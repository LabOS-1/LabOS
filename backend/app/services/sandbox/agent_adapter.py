"""
LABOS Sandbox Agent Adapter

Provides simple, secure file operations for Agent tools.
This is the interface that Agent tools should use instead of direct file I/O.

Usage in Agent tools:
    from app.services.sandbox.agent_adapter import (
        sandbox_save_file,
        sandbox_read_file,
        sandbox_list_files,
        get_sandbox_working_dir
    )

    # Save a file
    result = sandbox_save_file("output.csv", csv_content)

    # Read a file
    content = sandbox_read_file("data.csv")

    # Get working directory for subprocess
    work_dir = get_sandbox_working_dir()
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union
from datetime import datetime

from app.services.sandbox.manager import get_sandbox_manager, SandboxSecurityError
from app.services.sandbox.sync import get_sync_manager

logger = logging.getLogger(__name__)


def _get_context() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get user_id, project_id, and workflow_id from the current context.

    Returns:
        Tuple of (user_id, project_id, workflow_id)
    """
    user_id = None
    project_id = None
    workflow_id = None

    # Try to get from workflow context
    try:
        from app.services.workflows import get_workflow_context
        context = get_workflow_context()
        if context:
            user_id = context.metadata.get('user_id')
            project_id = context.metadata.get('project_id')
            workflow_id = context.workflow_id
    except Exception:
        pass

    # Fallback to environment variables (for testing)
    if not user_id:
        user_id = os.getenv("SANDBOX_USER_ID")
    if not project_id:
        project_id = os.getenv("SANDBOX_PROJECT_ID")

    return user_id, project_id, workflow_id


def _require_context() -> Tuple[str, str]:
    """
    Get required user_id and project_id, raising error if not available.

    Returns:
        Tuple of (user_id, project_id)

    Raises:
        SandboxSecurityError if context is not available
    """
    user_id, project_id, _ = _get_context()

    if not user_id:
        raise SandboxSecurityError(
            "User context not available. File operations require authenticated user."
        )
    if not project_id:
        raise SandboxSecurityError(
            "Project context not available. File operations require active project."
        )

    return user_id, project_id


# ==================== Main API for Agent Tools ====================

def sandbox_save_file(
    filename: str,
    content: Union[bytes, str],
    category: str = "generated",
    description: str = ""
) -> Dict[str, Any]:
    """
    Save a file to the current project's sandbox.

    This is the primary function for Agent tools to save files.
    It automatically:
    - Gets user/project context from the workflow
    - Validates and sanitizes the filename
    - Saves to the correct directory
    - Queues for GCS sync if enabled

    Args:
        filename: Name for the file (will be sanitized)
        content: File content (bytes or string)
        category: "generated" (default), "uploads", or "workspace"
        description: Optional description for metadata

    Returns:
        Dict with file_id, local_path, relative_path, etc.

    Example:
        result = sandbox_save_file("analysis.csv", csv_data)
        print(f"Saved: {result['relative_path']}")
    """
    user_id, project_id = _require_context()
    _, _, workflow_id = _get_context()

    # Convert string to bytes
    if isinstance(content, str):
        content = content.encode('utf-8')

    # Get sandbox manager
    sandbox = get_sandbox_manager()

    # Save file
    result = sandbox.save_file(
        user_id=user_id,
        project_id=project_id,
        filename=filename,
        content=content,
        category=category,
        metadata={
            "description": description,
            "workflow_id": workflow_id,
            "created_by": "agent"
        }
    )

    # Queue for GCS sync
    sync_manager = get_sync_manager()
    if sync_manager.sync_enabled:
        sync_manager.queue_upload(
            local_path=result["local_path"],
            user_id=user_id,
            project_id=project_id,
            relative_path=result["relative_path"]
        )

    logger.info(f"Agent saved file: {result['relative_path']} ({result['size']} bytes)")

    return result


def sandbox_read_file(
    filename: str,
    category: Optional[str] = None,
    as_text: bool = True
) -> Union[str, bytes]:
    """
    Read a file from the current project's sandbox.

    This is the primary function for Agent tools to read files.
    It automatically:
    - Gets user/project context from the workflow
    - Searches in uploads, generated, and workspace directories
    - Returns content as text or bytes

    Args:
        filename: Name of the file to read
        category: Optional hint for which directory to search
        as_text: If True, decode as UTF-8 text (default). If False, return bytes.

    Returns:
        File content as string or bytes

    Example:
        content = sandbox_read_file("data.csv")
        df = pd.read_csv(io.StringIO(content))
    """
    user_id, project_id = _require_context()

    sandbox = get_sandbox_manager()

    content, metadata = sandbox.read_file(
        user_id=user_id,
        project_id=project_id,
        filename=filename,
        category=category
    )

    logger.info(f"Agent read file: {metadata['filename']} ({len(content)} bytes)")

    if as_text:
        return content.decode('utf-8', errors='replace')
    return content


def sandbox_read_file_by_id(
    file_id: str,
    as_text: bool = True
) -> Union[str, bytes]:
    """
    Read a file by its file_id (from database).

    This provides backward compatibility with the old database-based storage.
    First checks local sandbox, then falls back to database lookup.

    Args:
        file_id: The file ID (from save_agent_file result)
        as_text: If True, decode as UTF-8 text

    Returns:
        File content as string or bytes
    """
    user_id, project_id = _require_context()

    # First, try to find in sandbox metadata
    sandbox = get_sandbox_manager()
    project_dir = sandbox.get_project_sandbox(user_id, project_id)
    metadata = sandbox._read_metadata(project_dir)

    for file_info in metadata.get("files", []):
        if file_info.get("file_id") == file_id:
            # Found in sandbox metadata, read from local
            relative_path = f"{file_info.get('category', 'generated')}/{file_info['filename']}"
            content, _ = sandbox.read_file_by_path(user_id, project_id, relative_path)

            if as_text:
                return content.decode('utf-8', errors='replace')
            return content

    # Fallback: try database lookup (for backward compatibility)
    try:
        from app.tools.core.files import read_project_file as db_read_file
        result = db_read_file(file_id)
        return result
    except Exception as e:
        raise FileNotFoundError(f"File not found: {file_id}") from e


def sandbox_list_files(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List files in the current project's sandbox.

    Args:
        category: Optional filter - "uploads", "generated", or "workspace"

    Returns:
        List of file info dicts with filename, category, size, etc.

    Example:
        files = sandbox_list_files()
        for f in files:
            print(f"{f['filename']} ({f['size']} bytes)")
    """
    user_id, project_id = _require_context()

    sandbox = get_sandbox_manager()
    return sandbox.list_files(user_id, project_id, category)


def sandbox_delete_file(filename: str, category: Optional[str] = None) -> bool:
    """
    Delete a file from the current project's sandbox.

    Args:
        filename: Name of the file to delete
        category: Optional category hint

    Returns:
        True if file was deleted
    """
    user_id, project_id = _require_context()

    sandbox = get_sandbox_manager()
    result = sandbox.delete_file(user_id, project_id, filename, category)

    # Also delete from GCS
    if result:
        sync_manager = get_sync_manager()
        if sync_manager.sync_enabled:
            import asyncio
            asyncio.create_task(
                sync_manager.delete_from_gcs(user_id, project_id, f"{category or 'generated'}/{filename}")
            )

    return result


def sandbox_file_exists(filename: str, category: Optional[str] = None) -> bool:
    """
    Check if a file exists in the current project's sandbox.

    Args:
        filename: Name of the file to check
        category: Optional category hint

    Returns:
        True if file exists
    """
    user_id, project_id = _require_context()

    sandbox = get_sandbox_manager()
    try:
        sandbox.read_file(user_id, project_id, filename, category)
        return True
    except FileNotFoundError:
        return False


# ==================== Working Directory ====================

def get_sandbox_working_dir() -> str:
    """
    Get the working directory path for the current project sandbox.

    This returns the 'workspace' subdirectory, which is suitable for:
    - Running Python scripts
    - Temporary file operations
    - Subprocess working directory

    Returns:
        Absolute path to the workspace directory

    Example:
        work_dir = get_sandbox_working_dir()
        subprocess.run(["python", "script.py"], cwd=work_dir)
    """
    user_id, project_id = _require_context()

    sandbox = get_sandbox_manager()
    project_dir = sandbox.ensure_project_sandbox(user_id, project_id)

    return str(project_dir / sandbox.WORKSPACE_DIR)


def get_sandbox_project_dir() -> str:
    """
    Get the root directory path for the current project sandbox.

    Returns:
        Absolute path to the project sandbox directory
    """
    user_id, project_id = _require_context()

    sandbox = get_sandbox_manager()
    project_dir = sandbox.ensure_project_sandbox(user_id, project_id)

    return str(project_dir)


# ==================== Context Helpers ====================

def set_sandbox_context(user_id: str, project_id: str):
    """
    Set sandbox context via environment variables.

    This is useful for testing or when workflow context is not available.

    Args:
        user_id: User ID to set
        project_id: Project ID to set
    """
    os.environ["SANDBOX_USER_ID"] = user_id
    os.environ["SANDBOX_PROJECT_ID"] = project_id
    logger.info(f"Set sandbox context: user={user_id}, project={project_id}")


def clear_sandbox_context():
    """Clear sandbox context environment variables."""
    os.environ.pop("SANDBOX_USER_ID", None)
    os.environ.pop("SANDBOX_PROJECT_ID", None)


# ==================== Utility Functions ====================

def get_sandbox_stats() -> Dict[str, Any]:
    """
    Get storage statistics for the current user.

    Returns:
        Dict with total_size, project_count, file_count
    """
    user_id, _ = _require_context()

    sandbox = get_sandbox_manager()
    return sandbox.get_sandbox_stats(user_id)


def cleanup_workspace():
    """Clean up temporary files in the current project's workspace."""
    user_id, project_id = _require_context()

    sandbox = get_sandbox_manager()
    sandbox.cleanup_workspace(user_id, project_id)
    logger.info(f"Cleaned workspace for project: {project_id}")


# ==================== Migration Helper ====================

async def migrate_file_from_database(
    file_id: str,
    user_id: str,
    project_id: str
) -> Optional[Dict[str, Any]]:
    """
    Migrate a file from database storage to sandbox.

    This is useful for migrating existing files from the old storage system.

    Args:
        file_id: Database file ID
        user_id: User ID
        project_id: Project ID

    Returns:
        Dict with new sandbox file info, or None if migration failed
    """
    try:
        # Import here to avoid circular imports
        from sqlalchemy import select
        from app.models.database.file import ProjectFile
        from app.tools.core.files import get_sync_session

        session = get_sync_session()
        from uuid import UUID

        result = session.execute(
            select(ProjectFile).where(ProjectFile.id == UUID(file_id))
        )
        db_file = result.scalar_one_or_none()

        if not db_file or not db_file.file_data:
            return None

        # Save to sandbox
        sandbox = get_sandbox_manager()
        result = sandbox.save_file(
            user_id=user_id,
            project_id=project_id,
            filename=db_file.original_filename or db_file.filename,
            content=db_file.file_data,
            category=db_file.category or "generated",
            metadata={
                "migrated_from_db": True,
                "original_file_id": file_id,
                "original_created_at": db_file.created_at.isoformat() if db_file.created_at else None
            }
        )

        logger.info(f"Migrated file from database: {file_id} -> {result['relative_path']}")
        return result

    except Exception as e:
        logger.error(f"Failed to migrate file {file_id}: {e}")
        return None
