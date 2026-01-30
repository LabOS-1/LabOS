"""
LABOS Sandbox File Tools

Secure file operations for Agent tools using the Sandbox system.
These tools replace the old database-based file storage with local file system storage.

Benefits:
- Faster read/write (local SSD vs database query)
- Automatic user isolation
- Path traversal protection
- Async GCS backup

Usage:
    from smolagents import tool

    # Tools are automatically registered
    result = save_file("output.csv", csv_content)
    content = read_file("data.csv")
"""

import os
import base64
import mimetypes
import logging
from pathlib import Path
from typing import Optional, Union
from smolagents import tool

from app.services.sandbox import (
    sandbox_save_file,
    sandbox_read_file,
    sandbox_list_files,
    sandbox_delete_file,
    sandbox_file_exists,
    get_sandbox_working_dir,
    get_sandbox_project_dir,
    SandboxSecurityError,
)
from app.services.workflows.workflow_context import emit_observation_event

logger = logging.getLogger(__name__)


# ==================== File Save Tool ====================

@tool
def save_file(
    filename: str,
    content: str,
    category: str = "generated",
    description: str = ""
) -> str:
    """
    Save a file to the project sandbox.

    This tool saves text content to a file in the current project's isolated sandbox.
    Files are automatically organized by category and synced to cloud storage.

    Args:
        filename: Name for the file (e.g., "analysis.csv", "output.json")
        content: Text content to save
        category: Where to save - "generated" (default), "uploads", or "workspace"
        description: Optional description of the file contents

    Returns:
        Status message with file ID and path

    Examples:
        >>> save_file("results.csv", csv_data)
        "Saved file: results.csv (ID: abc123) - 1.2 KB"

        >>> save_file("temp_data.json", json_str, category="workspace")
        "Saved file: temp_data.json (ID: def456) - 500 bytes"
    """
    try:
        result = sandbox_save_file(
            filename=filename,
            content=content,
            category=category,
            description=description
        )

        # Format size
        size = result["size"]
        if size >= 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        elif size >= 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} bytes"

        message = f"✅ Saved file: {result['original_filename']} (ID: {result['file_id']}) - {size_str}"

        # Emit event for visualization files
        if _is_image_file(filename):
            emit_observation_event(
                f"Generated visualization: {filename} (file_id: {result['file_id']})",
                tool_name="save_file"
            )

        return message

    except SandboxSecurityError as e:
        return f"❌ Security error: {str(e)}"
    except Exception as e:
        logger.error(f"Error saving file: {e}", exc_info=True)
        return f"❌ Error saving file: {str(e)}"


@tool
def save_binary_file(
    filename: str,
    base64_content: str,
    category: str = "generated",
    description: str = ""
) -> str:
    """
    Save a binary file (image, PDF, etc.) to the project sandbox.

    Use this for non-text files like images, PDFs, or other binary data.
    The content should be base64 encoded.

    Args:
        filename: Name for the file (e.g., "chart.png", "report.pdf")
        base64_content: Base64 encoded binary content
        category: Where to save - "generated" (default), "uploads", or "workspace"
        description: Optional description of the file

    Returns:
        Status message with file ID and path

    Example:
        >>> import base64
        >>> with open("image.png", "rb") as f:
        ...     b64 = base64.b64encode(f.read()).decode()
        >>> save_binary_file("chart.png", b64, description="Sales chart")
        "Saved file: chart.png (ID: xyz789) - 45.2 KB"
    """
    try:
        # Decode base64
        try:
            content = base64.b64decode(base64_content)
        except Exception:
            return "❌ Error: Invalid base64 content"

        result = sandbox_save_file(
            filename=filename,
            content=content,
            category=category,
            description=description
        )

        # Format size
        size = result["size"]
        if size >= 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        elif size >= 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} bytes"

        message = f"✅ Saved file: {result['original_filename']} (ID: {result['file_id']}) - {size_str}"

        # Emit event for visualization files
        if _is_image_file(filename):
            emit_observation_event(
                f"Generated visualization: {filename} (file_id: {result['file_id']})",
                tool_name="save_binary_file"
            )

        return message

    except SandboxSecurityError as e:
        return f"❌ Security error: {str(e)}"
    except Exception as e:
        logger.error(f"Error saving binary file: {e}", exc_info=True)
        return f"❌ Error saving file: {str(e)}"


# ==================== File Read Tool ====================

@tool
def read_file(filename: str, category: Optional[str] = None) -> str:
    """
    Read a file from the project sandbox.

    This tool reads text file content from the current project's sandbox.
    It searches in uploads, generated, and workspace directories.

    Args:
        filename: Name of the file to read
        category: Optional hint - "uploads", "generated", or "workspace"

    Returns:
        File content as text, or error message

    Examples:
        >>> read_file("data.csv")
        "id,name,value\n1,Alice,100\n2,Bob,200"

        >>> read_file("config.json", category="uploads")
        '{"setting": "value"}'
    """
    try:
        content = sandbox_read_file(
            filename=filename,
            category=category,
            as_text=True
        )

        # Truncate very long content for display
        if len(content) > 10000:
            return f"📄 File: {filename}\nContent (first 10000 chars):\n{content[:10000]}\n...[truncated]"

        return f"📄 File: {filename}\nContent:\n{content}"

    except FileNotFoundError:
        return f"❌ File not found: {filename}"
    except SandboxSecurityError as e:
        return f"❌ Security error: {str(e)}"
    except Exception as e:
        logger.error(f"Error reading file: {e}", exc_info=True)
        return f"❌ Error reading file: {str(e)}"


@tool
def read_binary_file(filename: str, category: Optional[str] = None) -> str:
    """
    Read a binary file and return its base64 encoded content.

    Use this for non-text files like images, PDFs, or other binary data.

    Args:
        filename: Name of the file to read
        category: Optional hint - "uploads", "generated", or "workspace"

    Returns:
        Base64 encoded content with metadata, or error message

    Example:
        >>> result = read_binary_file("chart.png")
        >>> # result contains base64 that can be used for display or processing
    """
    try:
        content = sandbox_read_file(
            filename=filename,
            category=category,
            as_text=False
        )

        b64 = base64.b64encode(content).decode('utf-8')
        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        return f"📦 File: {filename}\nType: {mime_type}\nSize: {len(content)} bytes\nBase64: {b64[:200]}{'...[truncated]' if len(b64) > 200 else ''}"

    except FileNotFoundError:
        return f"❌ File not found: {filename}"
    except SandboxSecurityError as e:
        return f"❌ Security error: {str(e)}"
    except Exception as e:
        logger.error(f"Error reading binary file: {e}", exc_info=True)
        return f"❌ Error reading file: {str(e)}"


# ==================== File List Tool ====================

@tool
def list_project_files(category: Optional[str] = None) -> str:
    """
    List all files in the current project's sandbox.

    This tool shows all available files organized by category.
    Use this to see what files have been uploaded or generated.

    Args:
        category: Optional filter - "uploads", "generated", or "workspace"

    Returns:
        Formatted list of files with details

    Example:
        >>> list_project_files()
        "Project Files:
        📁 uploads/
          - data.csv (1.2 KB)
          - config.json (500 bytes)
        📁 generated/
          - analysis.py (2.1 KB)
          - chart.png (45 KB)"
    """
    try:
        files = sandbox_list_files(category=category)

        if not files:
            return "📂 No files in project sandbox"

        # Group by category
        by_category = {}
        for f in files:
            cat = f.get("category", "unknown")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f)

        # Format output
        lines = ["📂 Project Files:"]

        for cat in ["uploads", "generated", "workspace"]:
            if cat in by_category:
                lines.append(f"\n📁 {cat}/")
                for f in by_category[cat]:
                    size = f.get("size", 0)
                    if size >= 1024 * 1024:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                    elif size >= 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size} bytes"
                    lines.append(f"  - {f['filename']} ({size_str})")

        return "\n".join(lines)

    except SandboxSecurityError as e:
        return f"❌ Security error: {str(e)}"
    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        return f"❌ Error listing files: {str(e)}"


# ==================== File Delete Tool ====================

@tool
def delete_file(filename: str, category: Optional[str] = None) -> str:
    """
    Delete a file from the project sandbox.

    This permanently removes a file from the project.
    Use with caution - deleted files cannot be recovered.

    Args:
        filename: Name of the file to delete
        category: Optional hint - "uploads", "generated", or "workspace"

    Returns:
        Status message

    Example:
        >>> delete_file("temp_data.json")
        "Deleted file: temp_data.json"
    """
    try:
        success = sandbox_delete_file(filename=filename, category=category)

        if success:
            return f"✅ Deleted file: {filename}"
        else:
            return f"❌ File not found: {filename}"

    except SandboxSecurityError as e:
        return f"❌ Security error: {str(e)}"
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        return f"❌ Error deleting file: {str(e)}"


# ==================== File Check Tool ====================

@tool
def file_exists(filename: str, category: Optional[str] = None) -> str:
    """
    Check if a file exists in the project sandbox.

    Args:
        filename: Name of the file to check
        category: Optional hint - "uploads", "generated", or "workspace"

    Returns:
        "true" if file exists, "false" otherwise

    Example:
        >>> file_exists("data.csv")
        "true"

        >>> file_exists("nonexistent.txt")
        "false"
    """
    try:
        exists = sandbox_file_exists(filename=filename, category=category)
        return "true" if exists else "false"

    except SandboxSecurityError as e:
        return f"❌ Security error: {str(e)}"
    except Exception as e:
        logger.error(f"Error checking file: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"


# ==================== Working Directory Tool ====================

@tool
def get_working_directory() -> str:
    """
    Get the working directory path for the current project.

    Use this to get a safe directory path for running scripts or
    storing temporary files during processing.

    Returns:
        Absolute path to the project's workspace directory

    Example:
        >>> work_dir = get_working_directory()
        >>> # Use this path for subprocess.run(cwd=work_dir)
        "/data/sandboxes/user123/project456/workspace"
    """
    try:
        path = get_sandbox_working_dir()
        return f"📁 Working directory: {path}"

    except SandboxSecurityError as e:
        return f"❌ Security error: {str(e)}"
    except Exception as e:
        logger.error(f"Error getting working directory: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"


# ==================== Helper Functions ====================

def _is_image_file(filename: str) -> bool:
    """Check if a file is an image based on extension."""
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}
    return Path(filename).suffix.lower() in image_extensions


# ==================== Backward Compatibility ====================
# These functions provide backward compatibility with the old database-based tools

def save_agent_file(
    file_path: str,
    category: str = "agent_generated",
    description: str = ""
) -> str:
    """
    Backward compatible wrapper for save_file.

    This reads from a local file path and saves to sandbox.
    Maintains compatibility with existing agent code.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"❌ File not found: {file_path}"

        content = path.read_bytes()
        result = sandbox_save_file(
            filename=path.name,
            content=content,
            category="generated" if category == "agent_generated" else category,
            description=description
        )

        return f"✅ Saved file: {result['original_filename']} (ID: {result['file_id']}) - {result['size']} bytes"

    except Exception as e:
        logger.error(f"Error in save_agent_file: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"


def read_project_file(file_id: str) -> str:
    """
    Backward compatible wrapper for read_file.

    Tries to read by file_id from sandbox metadata, falls back to filename search.
    """
    from app.services.sandbox import sandbox_read_file_by_id

    try:
        content = sandbox_read_file_by_id(file_id, as_text=True)
        return content
    except Exception as e:
        logger.error(f"Error in read_project_file: {e}", exc_info=True)
        return f"❌ Error reading file: {str(e)}"
