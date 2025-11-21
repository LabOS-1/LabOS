"""
File Tools - Tools for reading and accessing uploaded files
These tools allow agents to access files stored in the database
"""

from pathlib import Path
import base64
import mimetypes
from uuid import UUID
import asyncio
from functools import partial

from smolagents import tool
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from app.models import ProjectFile
import os

# Common text file extensions
TEXT_EXTS = {'.txt', '.csv', '.json', '.yaml', '.yml', '.md', '.py', '.xml', '.log', '.html', '.css', '.js', '.ts'}

# Create synchronous engine for tools (avoids event loop conflicts)
def get_sync_database_url() -> str:
    """Get synchronous database URL"""
    environment = os.getenv('ENVIRONMENT', 'development')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    cloud_sql_connection_name = os.getenv('CLOUD_SQL_CONNECTION_NAME')
    
    if not db_user or not db_password:
        raise ValueError("DB_USER and DB_PASSWORD must be set in environment variables")
    
    if environment == 'production':
        db_name = os.getenv('DB_NAME', 'stella_chat')
        return f"postgresql+psycopg2://{db_user}:{db_password}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"
    else:
        db_name = os.getenv('DEV_DB_NAME', 'stella_chat_dev')
        return f"postgresql+psycopg2://{db_user}:{db_password}@localhost:5432/{db_name}"

# Lazy initialization of sync engine
_sync_engine = None
_SyncSession = None

def get_sync_session():
    """Get or create sync database session"""
    global _sync_engine, _SyncSession
    if _sync_engine is None:
        try:
            _sync_engine = create_engine(
                get_sync_database_url(),
                pool_size=2,
                max_overflow=3,
                pool_pre_ping=True,
                echo=False  # Disable SQL logging
            )
            _SyncSession = sessionmaker(bind=_sync_engine, class_=Session)
        except Exception as e:
            print(f"Warning: Could not create sync database engine: {e}")
            raise
    return _SyncSession()


@tool
def save_agent_file(
    file_path: str,
    category: str = "agent_generated",
    description: str = ""
) -> str:
    """
    Save Agent-generated file to database for user download.
    
    Call this IMMEDIATELY after creating any output files (CSV, images, plots, reports).
    This makes the file available in the user's Files tab for download.
    
    Args:
        file_path: Full path to the file (e.g., "/tmp/analysis_results.csv")
        category: File category - "data_analysis", "visualization", "report", "model_output", etc.
        description: Brief description of what the file contains
    
    Returns:
        Success message with file_id, or error message
    
    Example:
        # After creating a file
        df.to_csv('/tmp/protein_results.csv', index=False)
        
        # Save to database immediately
        result = save_agent_file(
            file_path='/tmp/protein_results.csv',
            category='data_analysis',
            description='Protein sequence similarity scores for 1000 sequences'
        )
        print(result)  # "✅ File saved to database. File ID: abc-123-def. Users can download it from Files tab."
    """
    from pathlib import Path
    import os
    
    try:
        # Get workflow context
        from app.services.workflows import get_workflow_context
        context = get_workflow_context()
        
        # Get context data (even if context is None, we'll try to read from file)
        user_id = 'agent_default'
        project_id_str = None
        workflow_id = None
        workspace_dir = None
        
        if context:
            user_id = context.metadata.get('user_id', 'agent_default')
            project_id_str = context.metadata.get('project_id')
            workflow_id = context.workflow_id
            workspace_dir = context.metadata.get('workflow_tmp_dir')
        
        # If no context or missing project_id, try to infer workspace_dir and read from file
        # First, try to infer workspace_dir from file_path if not already set
        if not workspace_dir:
            # Try to determine workspace_dir from file_path
            file_path_obj = Path(file_path)
            if not file_path_obj.is_absolute():
                file_path_obj = file_path_obj.resolve()
            
            # Check if file is in a stella_projects directory
            file_path_str = str(file_path_obj)
            if '/stella_projects/project_' in file_path_str:
                # Extract project directory (e.g., /tmp/stella_projects/project_xxx)
                import re
                # Match everything up to and including project_<uuid>
                match = re.search(r'(.*/stella_projects/project_[a-f0-9\-]+)', file_path_str)
                if match:
                    workspace_dir = match.group(1)
                    print(f"🔍 Inferred workspace from file path: {workspace_dir}")
            
            # Final fallback
            if not workspace_dir:
                workspace_dir = os.environ.get('WORKFLOW_TMP_DIR', '/tmp')
        
        # Read from context file if project_id is still missing (even if workspace_dir exists)
        if not project_id_str and workspace_dir:
            import json
            context_file = os.path.join(workspace_dir, '.workflow_context.json')
            print(f"🔍 Looking for context file at: {context_file}")
            if os.path.exists(context_file):
                try:
                    with open(context_file, 'r') as f:
                        file_context = json.load(f)
                        project_id_str = file_context.get('project_id')
                        if not user_id or user_id == 'agent_default':
                            user_id = file_context.get('user_id', user_id)
                        if not workflow_id:
                            workflow_id = file_context.get('workflow_id')
                    print(f"📖 Read context from file: project_id={project_id_str}, user_id={user_id}, workspace={workspace_dir}")
                except Exception as e:
                    print(f"⚠️ Failed to read workflow context file: {e}")
            else:
                print(f"❌ Context file not found at: {context_file}")
        
        # Now validate file_path and read file data
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = file_path_obj.resolve()
        
        if not file_path_obj.exists():
            return f"❌ Error: File not found at {file_path}\n(Resolved to: {file_path_obj})"
        
        if not file_path_obj.is_file():
            return f"❌ Error: {file_path} is not a file"
        
        # Read file data
        file_size = file_path_obj.stat().st_size
        
        # Check size limit (10MB)
        if file_size > 10 * 1024 * 1024:
            return f"❌ Error: File too large ({file_size:,} bytes). Maximum size is 10MB."
        
        with open(file_path_obj, 'rb') as f:
            file_data = f.read()
        
        # Generate hash
        import hashlib
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        # Get file metadata
        import mimetypes
        content_type, _ = mimetypes.guess_type(str(file_path_obj))
        original_filename = file_path_obj.name
        
        # Generate safe filename
        import uuid as uuid_lib
        safe_filename = f"{uuid_lib.uuid4().hex}_{original_filename}"
        
        # Create database record
        session = None
        try:
            session = get_sync_session()
            
            from app.models import ProjectFile, FileType, FileStatus
            from uuid import UUID
            
            project_file = ProjectFile(
                user_id=user_id,
                project_id=UUID(project_id_str) if project_id_str else None,
                filename=safe_filename,
                original_filename=original_filename,
                file_size=file_size,
                content_type=content_type or 'application/octet-stream',
                file_hash=file_hash,
                file_data=file_data,
                storage_path=None,
                storage_provider="database",
                file_type=FileType.AGENT_GENERATED,
                category=category or "agent_generated",
                tags=["agent", "generated", category] if category else ["agent", "generated"],
                created_by_agent="dev_agent",  # Can be parameterized if needed
                workflow_id=workflow_id,
                status=FileStatus.ACTIVE,
                file_metadata={
                    "original_path": str(file_path),
                    "description": description,
                    "workflow_id": workflow_id
                }
            )
            
            session.add(project_file)
            session.commit()
            session.refresh(project_file)
            
            file_id = str(project_file.id)
            
            # Emit workflow event for file creation
            # For image files, include visualization metadata so they display in workflow
            from app.services.workflows import emit_observation_event

            # Check if this is an image file
            is_image = original_filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'))

            if is_image:
                # Emit with image reference format that frontend can detect
                emit_observation_event(
                    f"📊 Generated visualization: {original_filename} (file_id: {file_id})",
                    tool_name="save_agent_file"
                )
            else:
                # Regular file saved message
                emit_observation_event(
                    f"📁 Saved file: {original_filename} ({file_size:,} bytes)",
                    tool_name="save_agent_file"
                )

            # Return structured data with file_id for visualization tools
            # Format: "SUCCESS|file_id|filename|message"
            # This allows parsing while maintaining backward compatibility with string output
            return f"✅ File '{original_filename}' saved successfully (ID: {file_id})"
            
        finally:
            if session:
                session.close()
                
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error saving file to database:\n{str(e)}\n\nDetails:\n{error_details}"


def save_agent_file_sync(
    file_path: str,
    category: str = "agent_generated",
    description: str = "",
    user_id: str = None,
    project_id: str = None
) -> dict:
    """
    Synchronous version of save_agent_file for internal use (e.g., auto-registration).
    
    This function does NOT emit workflow events (used during cleanup).
    
    Args:
        file_path: Full path to the file
        category: File category
        description: File description
        user_id: User ID (optional, for auto-registration)
        project_id: Project ID (optional, for auto-registration)
    
    Returns:
        Dict with file_id if successful, None if error or already exists
    """
    from pathlib import Path
    import os
    
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = file_path_obj.resolve()
        
        if not file_path_obj.exists():
            return None
        
        if not file_path_obj.is_file():
            return None
        
        # Read file data
        file_size = file_path_obj.stat().st_size
        
        # Check size limit (10MB)
        if file_size > 10 * 1024 * 1024:
            print(f"⚠️ File too large: {file_size:,} bytes")
            return None
        
        with open(file_path_obj, 'rb') as f:
            file_data = f.read()
        
        # Generate hash
        import hashlib
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        # Get file metadata
        import mimetypes
        content_type, _ = mimetypes.guess_type(str(file_path_obj))
        original_filename = file_path_obj.name
        
        # Generate safe filename
        import uuid as uuid_lib
        safe_filename = f"{uuid_lib.uuid4().hex}_{original_filename}"
        
        # Create database record
        session = None
        try:
            session = get_sync_session()
            
            from app.models import ProjectFile, FileType, FileStatus
            from uuid import UUID
            
            # Check if file with same hash already exists
            existing_file = session.query(ProjectFile).filter_by(file_hash=file_hash).first()
            if existing_file:
                print(f"✅ File already registered: {original_filename} (hash: {file_hash[:8]}...)")
                return None  # Already exists, skip
            
            project_file = ProjectFile(
                user_id=user_id or 'agent_default',
                project_id=UUID(project_id) if project_id else None,
                filename=safe_filename,
                original_filename=original_filename,
                file_size=file_size,
                content_type=content_type or 'application/octet-stream',
                file_hash=file_hash,
                file_data=file_data,
                storage_path=None,
                storage_provider="database",
                file_type=FileType.AGENT_GENERATED,
                category=category or "agent_generated",
                tags=["agent", "generated", "auto_registered", category] if category else ["agent", "generated", "auto_registered"],
                created_by_agent="auto_registration",
                status=FileStatus.ACTIVE,
                file_metadata={
                    "original_path": str(file_path),
                    "description": description,
                    "auto_registered": True
                }
            )
            
            session.add(project_file)
            session.commit()
            session.refresh(project_file)
            
            file_id = str(project_file.id)
            
            return {
                'file_id': file_id,
                'filename': original_filename,
                'size': file_size,
                'hash': file_hash
            }
            
        finally:
            if session:
                session.close()
                
    except Exception as e:
        print(f"❌ Error in save_agent_file_sync: {e}")
        return None


@tool
def read_project_file(file_id: str) -> str:
    """Read file content from database by file ID.
    
    For text files: Returns decoded UTF-8 content (with error handling).
    For binary files: Returns metadata and base64 preview.
    
    Args:
        file_id: UUID string of the file in ProjectFile table
        
    Returns:
        File content as formatted string with metadata
        
    Example:
        content = read_project_file("cab61e7d-a627-48d4-9629-a57e00f05585")
    """
    # Clean tool implementation without event overhead
    
    session = None
    try:
        session = get_sync_session()
        # Validate and convert UUID
        try:
            file_uuid = UUID(file_id)
        except ValueError:
            return f"❌ Invalid file ID format: {file_id}\nExpected: UUID string (e.g., '123e4567-e89b-12d3-a456-426614174000')"
        
        # Query database synchronously
        result = session.execute(
            select(ProjectFile).where(ProjectFile.id == file_uuid)
        )
        pf = result.scalar_one_or_none()
        
        if not pf:
            return f"❌ File with ID {file_id} not found in database"
        
        filename = pf.original_filename or "unknown"
        ext = Path(filename).suffix.lower()
        mime, _ = mimetypes.guess_type(filename)
        
        # Text files: decode and return content
        if ext in TEXT_EXTS or (mime and mime.startswith("text/")):
            try:
                content = pf.file_data.decode("utf-8", errors="replace")
                content_preview = content[:1000] if len(content) > 1000 else content
                preview_note = f"\n\n⚠️  Content truncated. Showing first 1000 of {len(content)} characters." if len(content) > 1000 else ""
                
                return f"""📄 File: {filename}
Type: Text file ({ext})
Size: {len(content)} characters ({len(pf.file_data):,} bytes)
Content-Type: {pf.content_type or 'text/plain'}

Content:
{content_preview}{preview_note}"""
            except Exception as e:
                return f"❌ Failed to decode text file {filename}: {e}"
        
        # Binary files: provide metadata and base64 preview
        b64 = base64.b64encode(pf.file_data).decode("utf-8")
        preview_len = min(100, len(b64))
        preview = b64[:preview_len] + ("..." if len(b64) > preview_len else "")
        
        return f"""📦 File: {filename} (Binary)
Type: {pf.content_type or 'application/octet-stream'}
Size: {len(pf.file_data):,} bytes
Base64 length: {len(b64):,} characters

Base64 preview (first {preview_len} chars):
{preview}

💡 Note: This is a binary file. Consider:
   - If it's an image/PDF, use analyze_media_file() for AI-powered analysis
   - If it's structured data, ask user to convert to CSV/JSON/TXT
   - Use specialized tools for specific binary formats if available"""

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error reading file {file_id}:\n{str(e)}\n\nDetails:\n{error_details}"
    finally:
        if session:
            session.close()


# Media file extensions that Gemini can analyze
MEDIA_EXTS = {
    'image': {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'},
    'video': {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v', '.flv', '.wmv'},
    'pdf': {'.pdf'}
}


@tool
def analyze_media_file(file_id: str, prompt: str = "") -> str:
    """Analyze an image, video, or PDF file using Google Gemini AI.

    Use this tool when you need to understand the content of:
    - Images (PNG, JPG, GIF, WebP, etc.)
    - Videos (MP4, WebM, MOV, AVI, etc.)
    - PDF documents

    Args:
        file_id: UUID string of the file in database (from read_project_file output)
        prompt: Optional specific question about the file.
                If empty, provides a general analysis.
                Examples:
                - "What text is visible in this image?"
                - "Summarize the key points in this PDF"
                - "Describe what happens in this video"
                - "Extract data from this chart"

    Returns:
        Detailed AI analysis of the media file content

    Example:
        # Analyze an uploaded image
        analysis = analyze_media_file(
            file_id="cab61e7d-a627-48d4-9629-a57e00f05585",
            prompt="What data is shown in this chart?"
        )
        print(analysis)
    """
    session = None
    try:
        # Import Gemini agent
        from app.core.agents.gemini_agent import gemini_agent

        if not gemini_agent.model:
            return "❌ Error: Gemini API is not configured. Please set GOOGLE_API_KEY in environment."

        session = get_sync_session()

        # Validate and convert UUID
        try:
            file_uuid = UUID(file_id)
        except ValueError:
            return f"❌ Invalid file ID format: {file_id}\nExpected: UUID string"

        # Query database
        result = session.execute(
            select(ProjectFile).where(ProjectFile.id == file_uuid)
        )
        pf = result.scalar_one_or_none()

        if not pf:
            return f"❌ File with ID {file_id} not found in database"

        filename = pf.original_filename or "unknown"
        ext = Path(filename).suffix.lower()
        mime_type = pf.content_type or ""

        # Check if file type is supported
        is_image = ext in MEDIA_EXTS['image'] or mime_type.startswith('image/')
        is_video = ext in MEDIA_EXTS['video'] or mime_type.startswith('video/')
        is_pdf = ext in MEDIA_EXTS['pdf'] or mime_type == 'application/pdf'

        if not (is_image or is_video or is_pdf):
            return f"""❌ File type not supported for media analysis.
File: {filename}
Type: {mime_type or ext}

Supported types:
- Images: {', '.join(sorted(MEDIA_EXTS['image']))}
- Videos: {', '.join(sorted(MEDIA_EXTS['video']))}
- PDFs: .pdf

💡 For text files, use read_project_file() instead."""

        # Set default prompt based on file type
        if not prompt:
            if is_video:
                prompt = "Watch this video carefully and provide a detailed summary including: 1) Key events or scenes, 2) Main subjects/people, 3) Text or captions visible, 4) Audio/dialogue if present, 5) Important timestamps or transitions."
            elif is_image:
                prompt = "Analyze this image in detail including: 1) What you see, 2) Text content, 3) Colors and composition, 4) Any data, charts, or diagrams, 5) Relevant context."
            else:  # PDF
                prompt = "Analyze this PDF document. Summarize the key points, extract important data, tables, and describe its structure."

        # Get file data
        file_data = pf.file_data
        file_size = len(file_data)

        # Check size limits
        max_sizes = {
            'image': 20 * 1024 * 1024,   # 20MB
            'video': 100 * 1024 * 1024,  # 100MB
            'pdf': 50 * 1024 * 1024      # 50MB
        }

        file_type_key = 'video' if is_video else ('pdf' if is_pdf else 'image')
        max_size = max_sizes[file_type_key]

        if file_size > max_size:
            max_mb = max_size // (1024 * 1024)
            return f"❌ File too large for analysis. Size: {file_size / (1024*1024):.1f}MB, Max: {max_mb}MB"

        # Run Gemini analysis (sync wrapper for async function)
        print(f"🔍 Analyzing {file_type_key}: {filename} ({file_size:,} bytes) with Gemini...")

        # Create event loop if needed and run async function
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the async analyze_file method
        if loop.is_running():
            # We're in an async context, need to use run_in_executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    gemini_agent.analyze_file(file_data, mime_type or f"{file_type_key}/*", prompt)
                )
                analysis_result = future.result(timeout=300)  # 5 minute timeout
        else:
            # Not in async context, can run directly
            analysis_result = loop.run_until_complete(
                gemini_agent.analyze_file(file_data, mime_type or f"{file_type_key}/*", prompt)
            )

        # Format result
        type_emoji = "🎥" if is_video else ("📄" if is_pdf else "🖼️")

        return f"""{type_emoji} Media Analysis: {filename}
Type: {mime_type or ext}
Size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)
Model: Gemini

{'=' * 50}
ANALYSIS:
{'=' * 50}
{analysis_result}
{'=' * 50}"""

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error analyzing media file:\n{str(e)}\n\nDetails:\n{error_details}"
    finally:
        if session:
            session.close()


@tool
def analyze_gcs_media(gcs_uri: str, mime_type: str, prompt: str = "") -> str:
    """Analyze a large media file from Google Cloud Storage using Vertex AI Gemini.

    Use this tool for large video files (>30MB) that were uploaded directly to GCS.
    This bypasses the Cloud Run 32MB request limit and supports files up to 2GB.

    Args:
        gcs_uri: GCS URI in format 'gs://bucket-name/path/to/file'
        mime_type: MIME type of the file (e.g., 'video/mp4', 'image/png')
        prompt: Optional specific question about the file.
                If empty, provides a general analysis.

    Returns:
        Detailed AI analysis of the media file content

    Example:
        # Analyze a large video uploaded to GCS
        analysis = analyze_gcs_media(
            gcs_uri="gs://labos-uploads/uploads/user123/project456/video.mp4",
            mime_type="video/mp4",
            prompt="Summarize the key events in this video"
        )
        print(analysis)
    """
    try:
        from app.core.agents.gemini_agent import gemini_agent

        if not gemini_agent.vertex_client:
            return "❌ Error: Vertex AI client not initialized. Cannot analyze GCS files."

        if not gcs_uri.startswith("gs://"):
            return f"❌ Invalid GCS URI format. Expected 'gs://bucket/path', got: {gcs_uri}"

        # Determine file type for emoji
        is_video = mime_type.startswith('video/')
        is_pdf = mime_type == 'application/pdf'
        type_emoji = "🎥" if is_video else ("📄" if is_pdf else "🖼️")

        print(f"🔍 Analyzing GCS file via Vertex AI: {gcs_uri}")

        # Run async analysis
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    gemini_agent.analyze_gcs_file(gcs_uri, mime_type, prompt)
                )
                analysis_result = future.result(timeout=600)  # 10 minute timeout for large videos
        else:
            analysis_result = loop.run_until_complete(
                gemini_agent.analyze_gcs_file(gcs_uri, mime_type, prompt)
            )

        return f"""{type_emoji} GCS Media Analysis
URI: {gcs_uri}
Type: {mime_type}
Model: Vertex AI Gemini

{'=' * 50}
ANALYSIS:
{'=' * 50}
{analysis_result}
{'=' * 50}"""

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error analyzing GCS media:\n{str(e)}\n\nDetails:\n{error_details}"

