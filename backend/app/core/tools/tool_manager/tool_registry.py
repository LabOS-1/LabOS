"""
Tool Registry Module
Provides automatic tool discovery and per-user tool management for LABOS V2

Architecture:
- Predefined tools: Shared across all users (discovered from code)
- Custom tools: Per-user isolation (stored in database)
- Each user sees: predefined tools + their own custom tools only

Thread Safety:
- Uses threading.RLock for cache access protection
- Safe for concurrent requests from multiple users
- Predefined tools cached with thread-safe read/write
"""

import importlib
import logging
import threading
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Centralized tool registry with per-user tool isolation

    Features:
    - Auto-discover predefined tools (shared across users)
    - Load user-specific custom tools from database
    - Per-user isolation (users only see their own custom tools)
    - Category-based tool organization
    - Caching for performance
    - Thread-safe concurrent access

    Usage:
        # Get all tools for a specific user (predefined + user's custom tools)
        tools = await tool_registry.get_tools_for_user(user_id="user_123")

        # Get only predefined tools
        predefined = tool_registry.get_predefined_tools()

        # Add user custom tool to database
        await tool_registry.register_custom_tool(user_id, tool_code, tool_name)
    """

    _instance = None
    _instance_lock = threading.RLock()  # Class-level lock for singleton creation
    _predefined_tools_cache: Optional[List[Any]] = None
    _cache_lock = threading.RLock()  # Instance-level lock for cache access

    def __new__(cls):
        """Thread-safe singleton pattern"""
        if cls._instance is None:
            with cls._instance_lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize tool registry with thread-safe setup"""
        if not hasattr(self, '_initialized'):
            with self._cache_lock:
                # Double-check to prevent race condition
                if not hasattr(self, '_initialized'):
                    self._initialized = True
                    logger.info("🔧 ToolRegistry initialized (per-user isolation + thread-safe mode)")

    def discover_predefined_tools(self, force_refresh: bool = False) -> List[Any]:
        """
        Auto-discover predefined tools from code (shared across all users)
        Thread-safe with double-check locking pattern

        Args:
            force_refresh: If True, bypass cache and rediscover

        Returns:
            List of predefined tools (thread-safe cached copy)
        """
        # Fast path: Return cached if available (no lock needed for read)
        if not force_refresh and self._predefined_tools_cache is not None:
            with self._cache_lock:
                # Lock for safe read, return copy to prevent external modification
                if self._predefined_tools_cache is not None:
                    logger.debug(f"📦 Returning {len(self._predefined_tools_cache)} cached predefined tools")
                    return self._predefined_tools_cache.copy()  # Return copy for safety

        # Slow path: Need to discover tools
        with self._cache_lock:
            # Double-check: Another thread might have populated cache while we waited
            if not force_refresh and self._predefined_tools_cache is not None:
                logger.debug(f"📦 Cache populated by another thread, returning cached tools")
                return self._predefined_tools_cache.copy()

            logger.info("🔍 Discovering predefined tools (thread-safe)...")

            all_tools = []

            # Define tool modules to discover from
            tool_modules = [
                # Core tools
                ('app.tools.core.files', ['read_project_file', 'save_agent_file', 'analyze_media_file', 'analyze_gcs_media']),
                ('app.tools.core.memory', ['auto_recall_experience']),
                ('app.tools.core.evaluation', ['evaluate_with_critic']),
                ('app.tools.core.collaboration', ['check_agent_performance', 'quick_tool_stats']),

                # Predefined tools
                ('app.tools.predefined', [
                    # Search tools
                    'enhanced_google_search', 'search_google_basic', 'multi_source_search',
                    'smart_search_router', 'search_with_serpapi', 'enhanced_knowledge_search', 'search_google',
                    # Web tools
                    'visit_webpage', 'extract_url_content', 'extract_pdf_content',
                    # GitHub tools
                    'search_github_repositories', 'search_github_code', 'get_github_repository_info',
                    # Academic research tools
                    'fetch_supplementary_info_from_doi', 'query_arxiv', 'query_scholar', 'query_pubmed',
                    # Development tools
                    'run_shell_command', 'create_conda_environment', 'install_packages_conda',
                    'install_packages_pip', 'check_gpu_status', 'create_script', 'create_and_run_script',
                    'run_script', 'create_requirements_file', 'monitor_training_logs'
                ]),

                # Visualization tools
                ('app.tools.visualization', [
                    'create_line_plot', 'create_bar_chart', 'create_scatter_plot',
                    'create_heatmap', 'create_distribution_plot'
                ]),

                # Python interpreter (critical tool)
                ('app.tools.python_interpreter', ['python_interpreter']),
            ]

            # Discover tools from each module
            for module_name, tool_names in tool_modules:
                try:
                    module = importlib.import_module(module_name)

                    for tool_name in tool_names:
                        if hasattr(module, tool_name):
                            tool = getattr(module, tool_name)
                            all_tools.append(tool)
                            logger.debug(f"  ✅ Discovered: {tool_name} from {module_name}")
                        else:
                            logger.warning(f"  ⚠️  Tool {tool_name} not found in {module_name}")

                except Exception as e:
                    logger.error(f"  ❌ Failed to import {module_name}: {e}")

            # Cache the discovered tools (inside lock)
            self._predefined_tools_cache = all_tools

            logger.info(f"✅ Discovered {len(all_tools)} predefined tools (cached for future use)")
            return all_tools.copy()  # Return copy for safety

    async def get_custom_tools_for_user(self, user_id: str) -> List[Any]:
        """
        Load user-specific custom tools from database

        Args:
            user_id: User ID

        Returns:
            List of custom tools created by this user

        Note:
            This method loads tools from the database. Custom tools are
            isolated per user - each user only sees their own tools.
        """
        from app.core.infrastructure.database import get_db_session

        try:
            async with get_db_session() as session:
                # Import here to avoid circular dependency
                from app.models.database.tool import Tool as ToolModel

                # Query user's custom tools from database
                from sqlalchemy import select
                stmt = select(ToolModel).where(ToolModel.user_id == user_id)
                result = await session.execute(stmt)
                tool_records = result.scalars().all()

                if not tool_records:
                    logger.debug(f"No custom tools found for user: {user_id}")
                    return []

                # Convert database records to executable tool objects
                custom_tools = []
                for tool_record in tool_records:
                    try:
                        # Execute the tool code to create the function
                        # The tool code should define a function decorated with @tool
                        exec_globals = {}
                        exec(tool_record.code, exec_globals)

                        # Find the tool function in the executed code
                        for name, obj in exec_globals.items():
                            if callable(obj) and hasattr(obj, 'name'):
                                custom_tools.append(obj)
                                logger.debug(f"  ✅ Loaded custom tool: {tool_record.name} for user {user_id}")
                                break

                    except Exception as e:
                        logger.error(f"  ❌ Failed to load custom tool {tool_record.name}: {e}")

                logger.info(f"✅ Loaded {len(custom_tools)} custom tools for user: {user_id}")
                return custom_tools

        except Exception as e:
            logger.error(f"❌ Failed to load custom tools for user {user_id}: {e}")
            return []

    async def get_tools_for_user(
        self,
        user_id: Optional[str] = None,
        include_custom: bool = True
    ) -> List[Any]:
        """
        Get all available tools for a specific user

        Args:
            user_id: User ID (optional, if None only returns predefined tools)
            include_custom: Whether to include user's custom tools

        Returns:
            List of tools (predefined + user's custom tools)

        Example:
            # Get all tools for user (predefined + custom)
            tools = await tool_registry.get_tools_for_user("user_123")

            # Get only predefined tools
            tools = await tool_registry.get_tools_for_user()
        """
        # Get predefined tools (shared across all users)
        predefined_tools = self.discover_predefined_tools()

        # If no user_id or not including custom, return only predefined
        if not user_id or not include_custom:
            return predefined_tools

        # Load user's custom tools from database
        custom_tools = await self.get_custom_tools_for_user(user_id)

        # Combine predefined + custom tools
        all_tools = predefined_tools + custom_tools

        logger.info(f"📦 Total tools for user {user_id}: {len(all_tools)} "
                   f"(predefined: {len(predefined_tools)}, custom: {len(custom_tools)})")

        return all_tools

    def get_predefined_tools(self) -> List[Any]:
        """
        Get only predefined tools (shared across all users)

        Returns:
            List of predefined tools
        """
        return self.discover_predefined_tools()

    def get_tools_by_category(
        self,
        category: str,
        predefined_only: bool = True
    ) -> List[Any]:
        """
        Get tools filtered by category

        Args:
            category: Category name (search, visualization, files, etc.)
            predefined_only: If True, only return predefined tools

        Returns:
            List of tools in that category
        """
        # Category mapping
        category_mapping = {
            'search': [
                'enhanced_google_search', 'search_google_basic', 'multi_source_search',
                'smart_search_router', 'search_with_serpapi', 'enhanced_knowledge_search',
                'search_google', 'search_github_repositories', 'search_github_code'
            ],
            'visualization': [
                'create_line_plot', 'create_bar_chart', 'create_scatter_plot',
                'create_heatmap', 'create_distribution_plot'
            ],
            'files': [
                'read_project_file', 'save_agent_file', 'analyze_media_file', 'analyze_gcs_media'
            ],
            'code': [
                'python_interpreter', 'run_shell_command', 'create_script',
                'create_and_run_script', 'run_script'
            ],
            'research': [
                'fetch_supplementary_info_from_doi', 'query_arxiv', 'query_scholar',
                'query_pubmed', 'visit_webpage', 'extract_url_content', 'extract_pdf_content'
            ],
            'development': [
                'check_gpu_status', 'create_conda_environment', 'install_packages_conda',
                'install_packages_pip', 'create_requirements_file', 'monitor_training_logs'
            ],
            'memory': [
                'auto_recall_experience'
            ],
            'evaluation': [
                'evaluate_with_critic', 'check_agent_performance', 'quick_tool_stats'
            ]
        }

        tool_names_in_category = category_mapping.get(category.lower(), [])

        # Get predefined tools
        all_tools = self.get_predefined_tools()

        # Filter tools by name
        filtered_tools = []
        for tool in all_tools:
            tool_name = getattr(tool, 'name', getattr(tool, '__name__', None))
            if tool_name in tool_names_in_category:
                filtered_tools.append(tool)

        logger.info(f"📦 Retrieved {len(filtered_tools)} tools for category '{category}'")
        return filtered_tools

    def clear_cache(self):
        """Clear the predefined tools cache (force re-discovery next time) - Thread-safe"""
        with self._cache_lock:
            self._predefined_tools_cache = None
            logger.info("🗑️  Predefined tools cache cleared (thread-safe)")


# Global singleton instance
tool_registry = ToolRegistry()


# Convenience functions
def get_predefined_tools(force_refresh: bool = False) -> List[Any]:
    """
    Get all predefined tools (shared across users)

    Args:
        force_refresh: Force re-discovery even if cached

    Returns:
        List of predefined tools
    """
    return tool_registry.discover_predefined_tools(force_refresh=force_refresh)


async def get_tools_for_user(
    user_id: Optional[str] = None,
    include_custom: bool = True
) -> List[Any]:
    """
    Get all tools for a specific user (predefined + custom)

    Args:
        user_id: User ID (if None, returns only predefined)
        include_custom: Whether to include user's custom tools

    Returns:
        List of tools
    """
    return await tool_registry.get_tools_for_user(user_id, include_custom)
