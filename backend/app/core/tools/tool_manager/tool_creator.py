"""
Tool Creator - Create New Specialized Tools

This module handles the creation of new tools using the tool_creation_agent:
- Generate tool code based on specifications
- Save tools to database (not filesystem)
- Auto-load tools into agents
"""

from smolagents import tool
import time
from typing import Optional
from .tool_registry import register_tool


@tool
def save_tool_to_database(
    tool_name: str,
    tool_code: str,
    description: str,
    category: str = "custom"
) -> str:
    """Save a dynamically created tool to the database.

    Use this function to persist tool code to the database instead of writing files.
    This makes tools available across sessions and projects.

    Args:
        tool_name: Name of the tool (e.g., "analyze_protein_structure")
        tool_code: Complete Python code for the tool (must include @tool decorator)
        description: Description of what the tool does
        category: Tool category (data_processing, analysis, visualization, etc.)

    Returns:
        Success message with tool ID, or error message

    Example:
        # Create tool code as a string
        tool_code = \"\"\"
        from smolagents import tool

        @tool
        def analyze_data(data: str) -> str:
            '''Analyze the provided data.'''
            return f"Analysis: {data}"
        \"\"\"

        # Save to database
        result = save_tool_to_database(
            tool_name="analyze_data",
            tool_code=tool_code,
            description="Analyzes data and returns insights",
            category="data_processing"
        )
    """
    try:
        # Get workflow context
        from app.services.workflows import get_workflow_context
        context = get_workflow_context()

        if not context:
            return "❌ Error: No workflow context available. Cannot determine project_id."

        user_id = context.metadata.get('user_id')
        project_id = context.metadata.get('project_id')
        workflow_id = context.workflow_id

        if not user_id or not project_id:
            return "❌ Error: Missing user_id or project_id in workflow context"

        # Import tool storage service
        from app.services.tool_storage_service import tool_storage_service
        from app.models.schemas.tool import ToolCreate
        from uuid import UUID

        # Create tool data with minimal required fields
        tool_data = ToolCreate(
            name=tool_name,
            description=description,
            category=category,
            tool_code=tool_code,
            project_id=UUID(project_id),
            workflow_id=workflow_id,
            tool_metadata={
                "created_via": "tool_creation_agent",
                "auto_generated": True
            }
        )

        # Save to database using SYNCHRONOUS method to avoid event loop conflicts
        # This directly uses psycopg2 and works with uvloop without issues
        tool = tool_storage_service.create_tool_sync(
            tool_data=tool_data,
            user_id=user_id,
            created_by_agent="tool_creation_agent"
        )

        # Emit observation event
        from app.services.workflows import emit_observation_event
        emit_observation_event(
            f"💾 Saved tool '{tool_name}' to database (ID: {tool.id})",
            tool_name="save_tool_to_database"
        )

        # Auto-load the tool into agents so it's immediately usable
        # Use workflow-scoped temporary directory - will be cleaned up when workflow ends
        try:
            import os

            # Get workflow temp directory from context
            # This directory is automatically cleaned up when workflow completes
            workflow_tmp_dir = context.metadata.get('workflow_tmp_dir')
            if not workflow_tmp_dir:
                workflow_tmp_dir = f'/tmp/labos_workflow_{workflow_id}'
                os.makedirs(workflow_tmp_dir, exist_ok=True)

            # Create tools subdirectory in workflow temp
            tools_dir = os.path.join(workflow_tmp_dir, 'tools')
            os.makedirs(tools_dir, exist_ok=True)

            # Create __init__.py to make it a package
            init_file = os.path.join(tools_dir, '__init__.py')
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    f.write('# Temporary workflow tools\n')

            # Write tool code to workflow-specific temporary directory
            tool_file_path = os.path.join(tools_dir, f'{tool_name}.py')
            with open(tool_file_path, 'w') as f:
                f.write(tool_code)

            # Load the tool dynamically
            import importlib.util
            import sys
            import inspect

            # Load the module
            spec = importlib.util.spec_from_file_location(tool_name, tool_file_path)
            if spec is None or spec.loader is None:
                return f"✅ Tool '{tool_name}' saved to database (ID: {tool.id})\n\n⚠️ Could not load module. Run load_project_tools() to retry."

            module = importlib.util.module_from_spec(spec)
            sys.modules[tool_name] = module
            spec.loader.exec_module(module)

            # Find tool functions and add to agents
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

            if not tool_functions:
                return f"✅ Tool '{tool_name}' saved to database (ID: {tool.id})\n\n⚠️ No @tool decorated functions found. Run load_project_tools() to retry."

            # Add to agents
            for func_name, tool_func in tool_functions:
                if func_name not in manager_agent.tools:
                    manager_agent.tools[func_name] = tool_func
                if func_name not in dev_agent.tools:
                    dev_agent.tools[func_name] = tool_func

            emit_observation_event(
                f"🔧 Tool '{tool_name}' loaded into agents (workflow-scoped)",
                tool_name="save_tool_to_database"
            )

            return f"✅ Tool '{tool_name}' created successfully!\n\nTool ID: {tool.id}\nProject ID: {project_id}\n\n🎯 The tool is immediately available for use in this workflow.\n💾 Saved to database - will auto-load in future workflows via load_project_tools().\n🗑️  Temporary files will be cleaned up when workflow ends."

        except Exception as load_error:
            import traceback
            error_details = traceback.format_exc()
            return f"✅ Tool '{tool_name}' saved to database (ID: {tool.id})\n\n⚠️ Auto-loading error:\n{str(load_error)}\n\nRun load_project_tools() to load the tool manually."

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error saving tool to database:\n{str(e)}\n\nDetails:\n{error_details}"


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
2. The tool MUST be implemented as a function decorated with @tool from smolagents
3. Include proper docstrings with Args and Returns sections
4. Add error handling and input validation
5. Import all necessary dependencies at the top
6. Include type hints for all function parameters and returns
7. After writing the code, call save_tool_to_database() to save it

🚨 CRITICAL DOCSTRING REQUIREMENTS 🚨
- EVERY parameter MUST be documented in the Args section (including optional params with defaults)
- Missing parameter descriptions will cause auto-load to FAIL
- Use Google-style docstrings with complete Args, Returns sections

IMPORTANT:
- DO NOT use open() or write files to disk
- DO NOT try to create files in app/tools/ directory
- Instead, generate the tool code as a string and call save_tool_to_database()

Example structure with COMPLETE docstring:
```python
tool_code = '''
from smolagents import tool
import pandas as pd

@tool
def {tool_name}(param1: str, param2: int = 10, mode: str = "default") -> str:
    \"\"\"Brief one-line description of what the tool does.

    Longer description with more details about the tool's purpose,
    behavior, and use cases.

    Args:
        param1: Description of param1 (REQUIRED - be specific!)
        param2: Description of param2 (REQUIRED even for optional params!)
        mode: Operation mode - 'default' or 'verbose' (REQUIRED - document ALL params!)

    Returns:
        Description of what the function returns

    Raises:
        ValueError: When invalid input is provided
    \"\"\"
    try:
        # Implementation here
        if mode == "verbose":
            print(f"Processing {{param1}} with param2={{param2}}")
        return "result"
    except Exception as e:
        return f"Error: {{e}}"
'''

# Save to database
result = save_tool_to_database(
    tool_name="{tool_name}",
    tool_code=tool_code,
    description="{tool_purpose}",
    category="{tool_category}"
)
print(result)
```

The tool should be production-ready and will be saved to the database for immediate use.
"""

        result = tool_creation_agent.run(creation_task)

        return f"✅ Tool creation completed!\n\n{result}"

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error creating tool:\n{str(e)}\n\nDetails:\n{error_details}"
