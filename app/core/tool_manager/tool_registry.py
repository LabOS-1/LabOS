"""
Tool Registry - Manage Dynamic Tools

This module provides tool registration and management functionality:
- Global registry for dynamically created tools
- List all registered tools
- Get tool signatures and metadata
"""

from smolagents import tool
import inspect


# Global registry for dynamically created tools
dynamic_tools_registry = {}


@tool
def list_dynamic_tools() -> str:
    """List all dynamically created tools.

    Returns:
        List of created tools with their purposes
    """
    if not dynamic_tools_registry:
        return "No dynamic tools have been created yet."

    result = f"Dynamic Tools ({len(dynamic_tools_registry)}):\n"

    for tool_name, tool_info in dynamic_tools_registry.items():
        result += f"• {tool_name}: {tool_info['purpose'][:50]}...\n"

    return result


@tool
def get_tool_signature(tool_name: str) -> str:
    """Get the complete function signature of a loaded tool.

    Args:
        tool_name: Name of the tool to get signature for

    Returns:
        Complete function signature with parameter types and descriptions
    """
    # Import manager_agent from parent module
    from .. import labos_engine
    manager_agent = stella_engine.manager_agent

    try:
        if tool_name not in manager_agent.tools:
            return f"❌ Tool '{tool_name}' not found in loaded tools"

        tool_func = manager_agent.tools[tool_name]
        sig = inspect.signature(tool_func.forward)

        # Get complete signature with types
        params = []
        for param_name, param in sig.parameters.items():
            param_info = param_name
            if param.annotation != inspect.Parameter.empty:
                param_type = getattr(param.annotation, '__name__', str(param.annotation))
                param_info += f": {param_type}"
            if param.default != inspect.Parameter.empty:
                param_info += f" = {param.default}"
            params.append(param_info)

        signature = f"{tool_name}({', '.join(params)})"

        # Get docstring for parameter descriptions
        doc = inspect.getdoc(tool_func) or "No documentation available"

        result = f"🔧 Tool signature:\n{signature}\n\n📖 Documentation:\n{doc[:500]}..."

        return result

    except Exception as e:
        return f"❌ Error getting tool signature: {str(e)}"


def register_tool(tool_name: str, tool_info: dict) -> None:
    """Register a tool in the global registry.

    Args:
        tool_name: Name of the tool to register
        tool_info: Dictionary containing tool metadata (purpose, category, created_at, file_path)
    """
    dynamic_tools_registry[tool_name] = tool_info
    print(f"✅ Registered tool in registry: {tool_name}")
