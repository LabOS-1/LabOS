"""
LABOS Sandbox Service

Provides secure, isolated file storage for each user's projects.

Quick Start for Agent Tools:
    from app.services.sandbox import (
        sandbox_save_file,
        sandbox_read_file,
        sandbox_list_files,
        get_sandbox_working_dir
    )

    # Save a file
    result = sandbox_save_file("output.csv", csv_content)

    # Read a file
    content = sandbox_read_file("data.csv")

    # Get working directory
    work_dir = get_sandbox_working_dir()
"""

from app.services.sandbox.manager import (
    SandboxManager,
    SandboxSecurityError,
    get_sandbox_manager,
)
from app.services.sandbox.sync import (
    SandboxSyncManager,
    get_sync_manager,
)
from app.services.sandbox.agent_adapter import (
    sandbox_save_file,
    sandbox_read_file,
    sandbox_read_file_by_id,
    sandbox_list_files,
    sandbox_delete_file,
    sandbox_file_exists,
    get_sandbox_working_dir,
    get_sandbox_project_dir,
    get_sandbox_stats,
    set_sandbox_context,
    clear_sandbox_context,
    cleanup_workspace,
)

__all__ = [
    # Core classes
    "SandboxManager",
    "SandboxSyncManager",
    "SandboxSecurityError",
    # Singleton getters
    "get_sandbox_manager",
    "get_sync_manager",
    # Agent adapter functions (main API)
    "sandbox_save_file",
    "sandbox_read_file",
    "sandbox_read_file_by_id",
    "sandbox_list_files",
    "sandbox_delete_file",
    "sandbox_file_exists",
    "get_sandbox_working_dir",
    "get_sandbox_project_dir",
    "get_sandbox_stats",
    "set_sandbox_context",
    "clear_sandbox_context",
    "cleanup_workspace",
]
