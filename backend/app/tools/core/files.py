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
    """Get synchronous database URL

    Supports both SQLite and PostgreSQL (must match async database config)
    """
    # Check if SQLite mode is enabled (must match async config)
    use_sqlite = os.getenv('USE_SQLITE', 'false').lower() == 'true'

    if use_sqlite:
        # SQLite mode - synchronous driver
        sqlite_path = os.getenv('SQLITE_PATH', './data/labos.db')
        return f"sqlite:///{sqlite_path}"

    # PostgreSQL mode
    environment = os.getenv('ENVIRONMENT', 'development')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    cloud_sql_connection_name = os.getenv('CLOUD_SQL_CONNECTION_NAME')

    if not db_user or not db_password:
        raise ValueError(
            "DB_USER and DB_PASSWORD must be set in environment variables, "
            "or set USE_SQLITE=true to use local SQLite database"
        )

    if environment == 'production':
        db_name = os.getenv('DB_NAME', 'labos_chat')
        db_host = os.getenv('DB_HOST')
        if db_host:
            db_port = os.getenv('DB_PORT', '5432')
            return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            return f"postgresql+psycopg2://{db_user}:{db_password}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"
    else:
        db_name = os.getenv('DEV_DB_NAME', 'labos_chat_dev')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

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
    category: str = "generated",
    description: str = ""
) -> str:
    """
    Save Agent-generated file to sandbox for user download.

    Call this IMMEDIATELY after creating any output files (CSV, images, plots, reports).
    This makes the file available in the user's Files tab for download.

    Args:
        file_path: Full path to the file (e.g., "/tmp/analysis_results.csv")
        category: File category - "generated" (default), "data_analysis", "visualization", etc.
        description: Brief description of what the file contains

    Returns:
        Success message with file_id, or error message

    Example:
        # After creating a file
        df.to_csv('/tmp/protein_results.csv', index=False)

        # Save to sandbox immediately
        result = save_agent_file(
            file_path='/tmp/protein_results.csv',
            category='data_analysis',
            description='Protein sequence similarity scores'
        )
        print(result)  # "✅ File saved. Users can download from Files tab."
    """
    from pathlib import Path
    from datetime import datetime
    import json
    import shutil

    try:
        # Get workflow context
        from app.services.workflows import get_workflow_context
        context = get_workflow_context()

        # Get context data
        user_id = None
        project_id_str = None
        workflow_id = None

        if context:
            user_id = context.metadata.get('user_id')
            project_id_str = context.metadata.get('project_id')
            workflow_id = context.workflow_id

        # Validate we have required context
        if not user_id or not project_id_str:
            return f"❌ Error: Missing workflow context (user_id={user_id}, project_id={project_id_str}). Cannot save file."

        # Validate source file
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = file_path_obj.resolve()

        if not file_path_obj.exists():
            return f"❌ Error: File not found at {file_path}"

        if not file_path_obj.is_file():
            return f"❌ Error: {file_path} is not a file"

        # Get file info
        file_size = file_path_obj.stat().st_size

        # Check size limit (50MB for sandbox)
        if file_size > 50 * 1024 * 1024:
            return f"❌ Error: File too large ({file_size:,} bytes). Maximum size is 50MB."

        import mimetypes
        content_type, _ = mimetypes.guess_type(str(file_path_obj))
        original_filename = file_path_obj.name

        # Generate safe filename with UUID prefix
        import uuid as uuid_lib
        safe_filename = f"{uuid_lib.uuid4().hex[:8]}_{original_filename}"

        # Get sandbox manager and ensure project sandbox exists
        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()
        sandbox_root = sandbox.ensure_project_sandbox(user_id, project_id_str)

        # Determine target category folder (default to "generated")
        target_category = "generated"  # Always use generated for agent files
        target_dir = sandbox_root / target_category
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy file to sandbox
        target_path = target_dir / safe_filename
        shutil.copy2(file_path_obj, target_path)

        # Create composite file_id for API access: project_id/category/filename
        file_id = f"{project_id_str}/{target_category}/{safe_filename}"

        print(f"📁 Saved to sandbox: {target_path}")
        print(f"📎 File ID: {file_id}")

        # Update metadata.json for file listing
        metadata_path = sandbox_root / ".metadata.json"
        metadata = {"files": []}
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text())
            except:
                pass

        metadata.setdefault("files", []).append({
            "file_id": file_id,
            "filename": safe_filename,
            "original_filename": original_filename,
            "category": target_category,
            "file_category": category,  # User-provided category for filtering
            "content_type": content_type or 'application/octet-stream',
            "file_size": file_size,
            "description": description,
            "workflow_id": workflow_id,
            "created_at": datetime.now().isoformat(),
        })
        metadata_path.write_text(json.dumps(metadata, indent=2))

        # Emit workflow event for file creation
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

        return f"✅ File '{original_filename}' saved successfully (ID: {file_id})"

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error saving file:\n{str(e)}\n\nDetails:\n{error_details}"


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
    """Read file content by file ID (sandbox filename or legacy UUID).

    Files are stored in project sandbox: /data/sandboxes/{user_id}/{project_id}/

    For text files: Returns decoded UTF-8 content (with error handling).
    For binary files: Returns metadata and base64 preview.

    Args:
        file_id: Sandbox filename (e.g., "abc123_data.csv") or legacy UUID

    Returns:
        File content as formatted string with metadata

    Example:
        content = read_project_file("abc123_data.csv")
    """
    try:
        # First try to read from sandbox (new approach)
        from app.services.sandbox import sandbox_read_file, sandbox_file_exists, get_sandbox_project_dir

        # Check if file exists in sandbox
        if sandbox_file_exists(file_id):
            # Read from sandbox
            result = sandbox_read_file(file_id)

            filename = file_id
            ext = Path(filename).suffix.lower()
            content = result["content"]
            file_size = result["size"]

            # Text files
            if ext in TEXT_EXTS:
                content_preview = content[:1000] if len(content) > 1000 else content
                preview_note = f"\n\n⚠️  Content truncated. Showing first 1000 of {len(content)} characters." if len(content) > 1000 else ""

                return f"""📄 File: {filename}
Type: Text file ({ext})
Size: {len(content)} characters ({file_size:,} bytes)

Content:
{content_preview}{preview_note}"""
            else:
                # Return raw content for other text files
                return content

        # Fallback: Try to read from database (legacy files with UUID)
        session = None
        try:
            # Validate and convert UUID
            try:
                file_uuid = UUID(file_id)
            except ValueError:
                return f"❌ File not found: {file_id}\nFile does not exist in sandbox and is not a valid UUID."

            session = get_sync_session()

            # Query database synchronously
            result = session.execute(
                select(ProjectFile).where(ProjectFile.id == file_uuid)
            )
            pf = result.scalar_one_or_none()

            if not pf:
                return f"❌ File with ID {file_id} not found"

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

        finally:
            if session:
                session.close()

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error reading file {file_id}:\n{str(e)}\n\nDetails:\n{error_details}"


# Media file extensions that Gemini can analyze
MEDIA_EXTS = {
    'image': {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'},
    'video': {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v', '.flv', '.wmv'},
    'pdf': {'.pdf'}
}


@tool
def get_file_bytes(file_id: str, output_path: str) -> str:
    """Get binary file content and save to specified path for Python processing.

    Use this tool when you need to process binary files (images, videos, etc.) with Python code.
    This tool writes the full file data to a specified path, which you can then read in Python.

    Args:
        file_id: UUID string of the file in ProjectFile table
        output_path: Path where to save the file (e.g., "/tmp/input_image.png")

    Returns:
        Success message with file path and metadata, or error message

    Example:
        # Step 1: Save file to disk
        result = get_file_bytes(
            file_id="9f5d8ec5-7daa-43b7-8ac6-fb1ff3752529",
            output_path="/tmp/input_image.png"
        )

        # Step 2: Process with Python
        code = '''
import cv2
import numpy as np

# Read the image
img = cv2.imread("/tmp/input_image.png")

# Your processing here...
normalized = normalize_image(img)

# Save result
cv2.imwrite("/tmp/output_normalized.png", normalized)
'''
        python_interpreter(code)

        # Step 3: Save output to database
        save_agent_file("/tmp/output_normalized.png", category="data_analysis")
    """
    session = None
    try:
        session = get_sync_session()

        # Validate UUID
        try:
            file_uuid = UUID(file_id)
        except ValueError:
            return f"❌ Invalid file ID format: {file_id}"

        # Query database
        result = session.execute(
            select(ProjectFile).where(ProjectFile.id == file_uuid)
        )
        pf = result.scalar_one_or_none()

        if not pf:
            return f"❌ File with ID {file_id} not found in database"

        # Write file data to specified path
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'wb') as f:
            f.write(pf.file_data)

        filename = pf.original_filename or "unknown"

        return f"""✅ File saved successfully
Original filename: {filename}
Output path: {output_path}
Size: {len(pf.file_data):,} bytes
Content-Type: {pf.content_type or 'unknown'}

You can now process this file with python_interpreter. Example:
```python
import cv2
img = cv2.imread("{output_path}")
# Your processing code here...
```"""

    except Exception as e:
        import traceback
        return f"❌ Error saving file: {str(e)}\n\n{traceback.format_exc()}"
    finally:
        if session:
            session.close()


@tool
def analyze_media_file(file_id: str, prompt: str = "") -> str:
    """Analyze an image, video, or PDF file using Google Gemini AI.

    Use this tool when you need to understand the content of:
    - Images (PNG, JPG, GIF, WebP, etc.)
    - Videos (MP4, WebM, MOV, AVI, etc.)
    - PDF documents

    Files can be in sandbox (filename) or legacy database (UUID).

    Args:
        file_id: Sandbox filename (e.g., "abc123_image.png") or legacy UUID
        prompt: Optional specific question about the file.
                If empty, provides a general analysis.

    Returns:
        Detailed AI analysis of the media file content

    Example:
        analysis = analyze_media_file("abc123_chart.png", "What data is shown?")
    """
    try:
        # Import Gemini agent
        from app.core.agents.gemini_agent import gemini_agent

        if not gemini_agent.model:
            return "❌ Error: Gemini API is not configured. Please set GOOGLE_API_KEY in environment."

        # First try to read from sandbox
        from app.services.sandbox import sandbox_file_exists, sandbox_read_file, get_sandbox_project_dir

        file_data = None
        filename = file_id
        mime_type = ""

        if sandbox_file_exists(file_id):
            # Read from sandbox (as bytes)
            file_data = sandbox_read_file(file_id, as_text=False)
            filename = file_id
            mime_type, _ = mimetypes.guess_type(filename)
            mime_type = mime_type or ""
        else:
            # Fallback: Try to read from database (legacy files with UUID)
            session = None
            try:
                try:
                    file_uuid = UUID(file_id)
                except ValueError:
                    return f"❌ File not found: {file_id}\nFile does not exist in sandbox and is not a valid UUID."

                session = get_sync_session()

                result = session.execute(
                    select(ProjectFile).where(ProjectFile.id == file_uuid)
                )
                pf = result.scalar_one_or_none()

                if not pf:
                    return f"❌ File with ID {file_id} not found"

                file_data = pf.file_data
                filename = pf.original_filename or "unknown"
                mime_type = pf.content_type or ""
            finally:
                if session:
                    session.close()

        ext = Path(filename).suffix.lower()

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

        # Run Gemini analysis
        print(f"🔍 Analyzing {file_type_key}: {filename} ({file_size:,} bytes) with Gemini...")

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
                    gemini_agent.analyze_file(file_data, mime_type or f"{file_type_key}/*", prompt)
                )
                analysis_result = future.result(timeout=300)
        else:
            analysis_result = loop.run_until_complete(
                gemini_agent.analyze_file(file_data, mime_type or f"{file_type_key}/*", prompt)
            )

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
