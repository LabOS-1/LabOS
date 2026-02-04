"""
Tool Creator - Create New Specialized Tools

This module handles the creation of new tools using the tool_creation_agent:
- Generate tool code based on specifications
- Save tools to sandbox filesystem as .py files
- Auto-load tools into agents
"""

from smolagents import tool
from typing import Optional


@tool
def save_tool_to_sandbox(
    tool_name: str,
    tool_code: str,
    description: str,
    category: str = "custom"
) -> str:
    """Save a dynamically created tool to the project sandbox as a .py file.

    Use this function to persist tool code as a file in the sandbox.
    This makes tools available across sessions and projects.

    Args:
        tool_name: Name of the tool (e.g., "analyze_protein_structure"). Must be a valid Python identifier.
        tool_code: Complete Python code for the tool (must include @tool decorator)
        description: Description of what the tool does
        category: Tool category (data_processing, analysis, visualization, etc.)

    Returns:
        Success message with tool name and path, or error message
    """
    try:
        from app.services.workflows import get_workflow_context
        context = get_workflow_context()

        if not context:
            return "Error: No workflow context available. Cannot determine project_id."

        user_id = context.metadata.get('user_id')
        project_id = context.metadata.get('project_id')

        if not user_id or not project_id:
            return "Error: Missing user_id or project_id in workflow context"

        # Save to sandbox filesystem
        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()
        result = sandbox.save_tool_file(
            user_id=user_id,
            project_id=project_id,
            tool_name=tool_name,
            tool_code=tool_code,
            description=description,
            category=category,
            metadata={"created_via": "tool_creation_agent", "auto_generated": True}
        )

        # Emit observation event
        from app.services.workflows import emit_observation_event
        emit_observation_event(
            f"Saved tool '{tool_name}' to sandbox ({result['relative_path']})",
            tool_name="save_tool_to_sandbox"
        )

        # Auto-load the tool into current agents so it's immediately usable
        try:
            import importlib.util
            import sys
            import inspect

            tool_file_path = result['local_path']
            spec = importlib.util.spec_from_file_location(tool_name, tool_file_path)
            if spec is None or spec.loader is None:
                return f"Tool '{tool_name}' saved to sandbox.\n\nCould not auto-load module. Run load_project_tools() to retry."

            module = importlib.util.module_from_spec(spec)
            sys.modules[tool_name] = module
            spec.loader.exec_module(module)

            # Find @tool decorated functions (smolagents format)
            smolagent_tools = []
            for name, obj in inspect.getmembers(module):
                is_tool = (
                    (inspect.isfunction(obj) and hasattr(obj, '__smolagents_tool__')) or
                    (type(obj).__name__ == 'SimpleTool' and callable(obj))
                )
                if is_tool:
                    smolagent_tools.append(obj)

            # Get the active running system (not a fresh instance)
            from app.core.engines.langchain.multi_agent_system import get_active_multi_agent_system
            system = get_active_multi_agent_system()

            if smolagent_tools and system:
                # Convert smolagents tools to LangChain format for the running system
                from app.core.engines.smolagents.tool_adapter import batch_convert_tools
                langchain_tools = batch_convert_tools(smolagent_tools)

                for lc_tool in langchain_tools:
                    for agent_name in ['dev_agent', 'tool_creation_agent']:
                        agent = system.agents.get(agent_name)
                        if agent and hasattr(agent, 'add_tool'):
                            if lc_tool.name not in agent.tool_map:
                                agent.add_tool(lc_tool)

                emit_observation_event(
                    f"Tool '{tool_name}' loaded into agents",
                    tool_name="save_tool_to_sandbox"
                )

            return f"Tool '{tool_name}' created successfully!\n\nPath: {result['relative_path']}\n\nThe tool is immediately available for use in this workflow.\nSaved to sandbox - will auto-load in future workflows via load_project_tools()."

        except Exception as load_error:
            return f"Tool '{tool_name}' saved to sandbox ({result['relative_path']}).\n\nAuto-loading warning: {str(load_error)}\n\nRun load_project_tools() to load the tool manually."

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"Error saving tool to sandbox:\n{str(e)}\n\nDetails:\n{error_details}"


@tool
def create_new_tool(tool_name: str, tool_purpose: str, tool_category: str, technical_requirements: str) -> str:
    """Use the tool creation agent to create a new specialized tool.

    Args:
        tool_name: Name of the tool to create
        tool_purpose: Detailed description of what the tool should do
        tool_category: Category of the tool (analysis, visualization, data_processing, modeling, etc.)
        technical_requirements: Specific technical requirements and implementation details

    Returns:
        Result of tool creation process
    """
    try:
        # Import agents from parent module
        from .. import labos_engine
        tool_creation_agent = labos_engine.tool_creation_agent

        creation_task = f"""
Create a new Python tool with the following specifications:

TOOL NAME: {tool_name}
PURPOSE: {tool_purpose}
CATEGORY: {tool_category}
TECHNICAL REQUIREMENTS: {technical_requirements}

Requirements:
1. Write the complete Python tool code as a string variable
2. The tool MUST use @tool decorator from langchain_core.tools
3. Include proper docstrings with Args and Returns sections
4. Add error handling and input validation
5. Import all necessary dependencies at the top
6. Include type hints for all function parameters and returns
7. Call save_tool_to_sandbox() to save it

CRITICAL: EVERY parameter MUST be documented in the Args section.

IMPORTANT:
- DO NOT use open() or write files to disk
- Generate the tool code as a string and call save_tool_to_sandbox()

Example:
```python
tool_code = '''
from langchain_core.tools import tool

@tool
def {tool_name}(param1: str, param2: int = 10) -> str:
    \"\"\"Brief description of what the tool does.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value
    \"\"\"
    try:
        # Implementation here
        return "result"
    except Exception as e:
        return f"Error: {{e}}"
'''

result = save_tool_to_sandbox(
    tool_name="{tool_name}",
    tool_code=tool_code,
    description="{tool_purpose}",
    category="{tool_category}"
)
print(result)
```
"""

        result = tool_creation_agent.run(creation_task)

        return f"✅ Tool creation completed!\n\n{result}"

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error creating tool:\n{str(e)}\n\nDetails:\n{error_details}"
