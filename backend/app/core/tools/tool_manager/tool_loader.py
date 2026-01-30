"""
Tool Loader - Dynamic Tool Loading and Management

This module handles loading tools from various sources:
- Load tools from files in app/tools directory
- Load tools from database for current project
- Refresh all available tools
- Add specific tools to agents
- Retry mechanism for failed loads
"""

from smolagents import tool
from functools import wraps
import time
import os
import glob
import sys
import inspect
import importlib.util
import asyncio
import tempfile


# Retry decorator
def retry_on_failure(max_retries=3, delay=1.0):
    """Decorator to retry failed operations with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapper function that implements retry logic with exponential backoff."""
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise last_exception
            return None
        return wrapper
    return decorator


@tool
def load_project_tools() -> str:
    """Load all tools created for the current project from database.

    This function retrieves all tools that were previously created for this project
    and loads them into the agents so they can be used.

    Returns:
        Summary of loaded tools
    """
    try:
        from app.services.tool_storage_service import tool_storage_service
        from app.services.workflows import get_workflow_context

        context = get_workflow_context()
        if not context or not context.metadata.get('project_id'):
            return "❌ No project context available. This function only works within a project."

        project_id = context.metadata['project_id']
        user_id = context.metadata.get('user_id', 'system')

        # Get tools from database using SYNC method
        from uuid import UUID
        from sqlalchemy import select
        from app.models.database.tool import ProjectTool, ToolStatus

        # Use sync session
        session = None
        try:
            session = tool_storage_service._get_sync_session()
            query = select(ProjectTool).where(
                ProjectTool.project_id == UUID(project_id),
                ProjectTool.user_id == user_id,
                ProjectTool.status == ToolStatus.ACTIVE
            ).order_by(ProjectTool.created_at.desc())

            result = session.execute(query)
            tools = list(result.scalars().all())
        finally:
            if session:
                session.close()

        if not tools:
            return f"📦 No tools found for this project (ID: {project_id})"

        # Get workflow temp directory - tools will be auto-cleaned when workflow ends
        workflow_tmp_dir = context.metadata.get('workflow_tmp_dir')
        if not workflow_tmp_dir:
            workflow_id = context.workflow_id
            workflow_tmp_dir = f'/tmp/labos_workflow_{workflow_id}'
            os.makedirs(workflow_tmp_dir, exist_ok=True)

        # Create tools subdirectory
        tools_dir = os.path.join(workflow_tmp_dir, 'tools')
        os.makedirs(tools_dir, exist_ok=True)

        # Create __init__.py
        init_file = os.path.join(tools_dir, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('# Temporary workflow tools\n')

        # Load each tool
        loaded_count = 0
        failed_tools = []

        for tool in tools:
            try:
                # Write tool to workflow temp directory
                tool_file_path = os.path.join(tools_dir, f'{tool.name}.py')
                with open(tool_file_path, 'w') as f:
                    f.write(tool.tool_code)

                # Load the module dynamically
                import importlib.util
                import sys
                import inspect

                spec = importlib.util.spec_from_file_location(tool.name, tool_file_path)
                if spec is None or spec.loader is None:
                    failed_tools.append(f"{tool.name}: Could not create module spec")
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[tool.name] = module
                spec.loader.exec_module(module)

                # Find and add tool functions to agents
                from .. import labos_engine
                manager_agent = labos_engine.manager_agent
                dev_agent = labos_engine.dev_agent

                tool_functions = []
                for name, obj in inspect.getmembers(module):
                    is_tool = (
                        (inspect.isfunction(obj) and hasattr(obj, '__smolagents_tool__')) or
                        (type(obj).__name__ == 'SimpleTool' and callable(obj))
                    )
                    if is_tool:
                        tool_functions.append((name, obj))

                if tool_functions:
                    for func_name, tool_func in tool_functions:
                        if func_name not in manager_agent.tools:
                            manager_agent.tools[func_name] = tool_func
                        if func_name not in dev_agent.tools:
                            dev_agent.tools[func_name] = tool_func
                    loaded_count += 1
                    print(f"✅ Loaded tool from database: {tool.name}")
                else:
                    failed_tools.append(f"{tool.name}: No @tool decorated functions found")

            except Exception as e:
                failed_tools.append(f"{tool.name}: {str(e)}")

        # Generate summary
        summary = f"🔧 Loaded {loaded_count}/{len(tools)} tools from database\n"

        if loaded_count > 0:
            summary += f"✅ Successfully loaded: {loaded_count} tools\n"

        if failed_tools:
            summary += f"\n❌ Failed to load ({len(failed_tools)}):\n"
            for failure in failed_tools[:5]:  # Show first 5 failures
                summary += f"  • {failure}\n"
            if len(failed_tools) > 5:
                summary += f"  ... and {len(failed_tools) - 5} more\n"

        return summary

    except Exception as e:
        return f"❌ Error loading project tools: {str(e)}"


@tool
@retry_on_failure(max_retries=2)
def load_dynamic_tool(tool_name: str, add_to_agents: bool = True) -> str:
    """Dynamically load a tool from the app/tools directory and optionally add it to agents.

    Args:
        tool_name: Name of the tool to load
        add_to_agents: Whether to add the loaded tool to dev_agent and tool_creation_agent

    Returns:
        Status of the loading operation
    """
    try:
        # Import agents from parent module
        from .. import labos_engine
        manager_agent = labos_engine.manager_agent
        dev_agent = labos_engine.dev_agent
        tool_creation_agent = labos_engine.tool_creation_agent

        # Ensure app/tools directory exists
        os.makedirs('app/tools', exist_ok=True)

        tool_file_path = f'app/tools/{tool_name}.py'

        if not os.path.exists(tool_file_path):
            return f"❌ Tool file '{tool_file_path}' not found."

        # Load the module
        spec = importlib.util.spec_from_file_location(tool_name, tool_file_path)
        if spec is None or spec.loader is None:
            return f"❌ Could not load module specification for '{tool_name}'."

        module = importlib.util.module_from_spec(spec)
        sys.modules[tool_name] = module
        spec.loader.exec_module(module)

        result = f"✅ Successfully loaded tool '{tool_name}' from {tool_file_path}"

        if add_to_agents:
            # Find all functions decorated with @tool in the loaded module
            # Note: @tool decorator wraps functions into SimpleTool objects
            tool_functions = []
            for name, obj in inspect.getmembers(module):
                # Check for SimpleTool objects (created by @tool decorator)
                is_tool = (
                    (inspect.isfunction(obj) and hasattr(obj, '__smolagents_tool__')) or
                    (type(obj).__name__ == 'SimpleTool' and callable(obj))
                )
                if is_tool:
                    tool_functions.append((name, obj))

            if tool_functions:
                # Add to all agents' tools (tools is a dict in smolagents)
                agents_updated = []
                for tool_name_func, tool_func in tool_functions:
                    # Add to manager_agent (most important - it's the one calling the tool!)
                    if manager_agent is not None:
                        if tool_name_func not in manager_agent.tools:
                            manager_agent.tools[tool_name_func] = tool_func
                            if 'manager_agent' not in agents_updated:
                                agents_updated.append('manager_agent')

                    # Add to dev_agent
                    if tool_name_func not in dev_agent.tools:
                        dev_agent.tools[tool_name_func] = tool_func
                        if 'dev_agent' not in agents_updated:
                            agents_updated.append('dev_agent')

                    # Add to tool_creation_agent
                    if tool_name_func not in tool_creation_agent.tools:
                        tool_creation_agent.tools[tool_name_func] = tool_func
                        if 'tool_creation_agent' not in agents_updated:
                            agents_updated.append('tool_creation_agent')

                result += f"\n🔧 Added {len(tool_functions)} tool function(s) to {', '.join(agents_updated)}"

                # Save to database
                try:
                    from app.services.tool_storage_service import tool_storage_service
                    from app.services.workflows import get_workflow_context
                    from app.models.schemas.tool import ToolCreate, ToolParameter
                    from uuid import UUID

                    # Get current workflow context for project_id and user_id
                    context = get_workflow_context()

                    # Read tool source code
                    with open(tool_file_path, 'r') as f:
                        tool_code = f.read()

                    # Save each tool function to database
                    for tool_name_func, tool_func in tool_functions:
                        # Extract tool metadata
                        tool_description = getattr(tool_func, 'description', f"Dynamically created tool: {tool_name_func}")

                        # Get parameters from function signature
                        sig = inspect.signature(tool_func)
                        parameters = []
                        for param_name, param in sig.parameters.items():
                            parameters.append({
                                "name": param_name,
                                "type": getattr(param.annotation, '__name__', 'Any') if param.annotation != inspect.Parameter.empty else 'Any',
                                "required": param.default == inspect.Parameter.empty,
                                "description": f"Parameter: {param_name}"
                            })

                        # Convert project_id to UUID if it's a string
                        project_id = None
                        if context and context.metadata.get('project_id'):
                            pid = context.metadata.get('project_id')
                            project_id = UUID(pid) if isinstance(pid, str) else pid

                        tool_data = ToolCreate(
                            name=tool_name_func,
                            description=tool_description,
                            category="dynamic",
                            tool_code=tool_code,
                            parameters=[ToolParameter(**p) for p in parameters],
                            project_id=project_id,
                            workflow_id=context.workflow_id if context else None
                        )

                        # Get user_id from context
                        user_id = context.metadata.get('user_id', 'system') if context else 'system'

                        # Save to database - use a helper coroutine with proper error handling
                        async def save_tool_async():
                            try:
                                saved_tool = await tool_storage_service.create_tool(
                                    tool_data=tool_data,
                                    user_id=user_id,
                                    created_by_agent="tool_creation_agent"
                                )
                                print(f"✅ Saved tool '{tool_name_func}' to database (ID: {saved_tool.id})")
                                return True
                            except Exception as save_error:
                                print(f"❌ Failed to save tool '{tool_name_func}': {save_error}")
                                import traceback
                                traceback.print_exc()
                                return False

                        # Execute the save operation asynchronously without blocking
                        # Note: We don't wait for completion to avoid event loop issues
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # Schedule task in background without waiting
                                asyncio.create_task(save_tool_async())
                                result += f"\n💾 Saving tool '{tool_name_func}' to database (async)"
                            else:
                                # No running loop, run synchronously
                                success = loop.run_until_complete(save_tool_async())
                                if success:
                                    result += f"\n💾 Saved tool '{tool_name_func}' to database"
                                else:
                                    result += f"\n⚠️ Failed to save tool '{tool_name_func}' to database"
                        except RuntimeError:
                            # No event loop available, skip database save
                            result += f"\n⚠️ No event loop available, skipping database save for '{tool_name_func}'"

                except Exception as e:
                    print(f"⚠️ Failed to save tool to database: {e}")
                    import traceback
                    traceback.print_exc()
                    result += f"\n⚠️ Tool loaded but not saved to database: {str(e)}"
            else:
                result += "\n⚠️ No @tool decorated functions or SimpleTool objects found in the module"
                result += "\n💡 Tip: Make sure your function is decorated with @tool from smolagents"

        return result

    except Exception as e:
        return f"❌ Error loading tool '{tool_name}': {str(e)}"


@tool
def refresh_agent_tools() -> str:
    """Refresh agent tools by loading all available tools from the app/tools directory.

    Returns:
        Status of the refresh operation
    """
    try:
        new_tools_dir = 'app/tools'
        if not os.path.exists(new_tools_dir):
            return "📁 app/tools directory does not exist yet."

        # Find all Python files in app/tools directory
        tool_files = glob.glob(os.path.join(new_tools_dir, '*.py'))

        if not tool_files:
            return "📁 No tool files found in app/tools directory."

        loaded_count = 0
        results = []

        for tool_file in tool_files:
            tool_name = os.path.splitext(os.path.basename(tool_file))[0]
            try:
                result = load_dynamic_tool(tool_name, add_to_agents=True)
                if "✅" in result:
                    loaded_count += 1
                results.append(f"  - {tool_name}: {'✅' if '✅' in result else '❌'}")
            except Exception as e:
                results.append(f"  - {tool_name}: ❌ {str(e)}")

        summary = f"🔄 Agent tools refresh completed!\n"
        summary += f"📊 Loaded {loaded_count}/{len(tool_files)} tools:\n"
        summary += "\n".join(results)

        return summary

    except Exception as e:
        return f"❌ Error refreshing agent tools: {str(e)}"


@tool
def add_tool_to_agents(tool_function_name: str, module_name: str) -> str:
    """Add a specific tool function to dev_agent and tool_creation_agent.

    Args:
        tool_function_name: Name of the tool function to add
        module_name: Name of the module containing the tool

    Returns:
        Status of the operation
    """
    try:
        # Import agents from parent module
        from .. import labos_engine
        dev_agent = labos_engine.dev_agent
        tool_creation_agent = labos_engine.tool_creation_agent

        if module_name not in sys.modules:
            return f"❌ Module '{module_name}' not loaded. Use load_dynamic_tool first."

        module = sys.modules[module_name]

        if not hasattr(module, tool_function_name):
            return f"❌ Function '{tool_function_name}' not found in module '{module_name}'."

        tool_func = getattr(module, tool_function_name)

        # Check if it's a tool function
        if not hasattr(tool_func, '__smolagents_tool__'):
            return f"❌ Function '{tool_function_name}' is not decorated with @tool."

        # Add to agents if not already present (tools is a dict)
        added_to = []
        if tool_function_name not in dev_agent.tools:
            dev_agent.tools[tool_function_name] = tool_func
            added_to.append("dev_agent")

        if tool_function_name not in tool_creation_agent.tools:
            tool_creation_agent.tools[tool_function_name] = tool_func
            added_to.append("tool_creation_agent")

        if added_to:
            return f"✅ Tool '{tool_function_name}' added to: {', '.join(added_to)}"
        else:
            return f"ℹ️ Tool '{tool_function_name}' was already available in all agents."

    except Exception as e:
        return f"❌ Error adding tool to agents: {str(e)}"
