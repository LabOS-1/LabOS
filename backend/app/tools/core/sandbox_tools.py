"""
LABOS Sandbox Tools

Central module that exports all sandbox-safe tools for Agent use.
These tools are designed to work within the project sandbox with proper security.

Usage:
    from app.tools.core.sandbox_tools import get_sandbox_tools

    tools = get_sandbox_tools()
    # Returns list of safe tools for Agent initialization
"""

import logging
from typing import List, Any

logger = logging.getLogger(__name__)

# Import sandbox-safe tools
from app.tools.core.sandbox_files import (
    save_file,
    save_binary_file,
    read_file,
    read_binary_file,
    list_project_files,
    delete_file,
    file_exists,
    get_working_directory,
)

from app.tools.core.sandbox_python import (
    python_interpreter,
    run_python_file,
)

# Import visualization tools (already sandbox-aware)
from app.tools.visualization.plotting import (
    create_line_plot,
    create_bar_chart,
    create_scatter_plot,
    create_heatmap,
    create_distribution_plot,
)

# Import safe search tools
from app.tools.predefined import (
    search_google,
    visit_webpage,
)
from app.tools.pubmed import pubmed_search


def get_sandbox_tools() -> List[Any]:
    """
    Get list of all sandbox-safe tools for Agent initialization.

    Returns:
        List of @tool decorated functions that are safe to use in sandbox
    """
    tools = [
        # File operations (sandbox-restricted)
        save_file,
        save_binary_file,
        read_file,
        read_binary_file,
        list_project_files,
        delete_file,
        file_exists,
        get_working_directory,

        # Code execution (sandbox-restricted)
        python_interpreter,
        run_python_file,

        # Visualization (writes to sandbox)
        create_line_plot,
        create_bar_chart,
        create_scatter_plot,
        create_heatmap,
        create_distribution_plot,

        # Search tools (read-only, safe)
        pubmed_search,
        search_google,
        visit_webpage,
    ]

    logger.info(f"Loaded {len(tools)} sandbox-safe tools")
    return tools


def get_dangerous_tools_blacklist() -> List[str]:
    """
    Get list of tool names that should NOT be given to Agents.

    These tools are dangerous because they allow:
    - Arbitrary shell command execution
    - Package installation
    - System modification
    """
    return [
        'run_shell_command',
        'install_packages_pip',
        'install_packages_conda',
        'create_conda_environment',
        'check_gpu_status',  # Could leak system info
    ]


# Export all safe tools
__all__ = [
    'get_sandbox_tools',
    'get_dangerous_tools_blacklist',
    # File tools
    'save_file',
    'save_binary_file',
    'read_file',
    'read_binary_file',
    'list_project_files',
    'delete_file',
    'file_exists',
    'get_working_directory',
    # Code execution
    'python_interpreter',
    'run_python_file',
    # Visualization
    'create_line_plot',
    'create_bar_chart',
    'create_scatter_plot',
    'create_heatmap',
    'create_distribution_plot',
    # Search
    'pubmed_search',
    'search_google',
    'visit_webpage',
]
