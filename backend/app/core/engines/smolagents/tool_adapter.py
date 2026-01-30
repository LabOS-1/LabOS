"""
Tool Adapter: Convert Smolagents tools to LangChain format
Wraps existing Smolagents @tool functions to work with LangChain
"""

from langchain_core.tools import tool as langchain_tool
from typing import Callable, Any
import inspect


def smolagent_to_langchain(smolagent_tool: Any) -> Callable:
    """
    Convert a Smolagents tool to LangChain format

    Args:
        smolagent_tool: A Smolagents SimpleTool instance

    Returns:
        A LangChain-compatible tool function
    """
    # Smolagents SimpleTool structure:
    # - tool.name: tool name
    # - tool.description: tool description
    # - tool.inputs: input schema
    # - tool.output_type: output type
    # - tool.fn: underlying function (or tool itself is callable)

    # Get tool metadata
    func_name = getattr(smolagent_tool, 'name', 'unknown_tool')
    func_description = getattr(smolagent_tool, 'description', "No description")

    # Get the underlying callable
    if hasattr(smolagent_tool, 'fn') and callable(smolagent_tool.fn):
        original_fn = smolagent_tool.fn
    elif callable(smolagent_tool):
        # The tool itself is callable
        original_fn = lambda *args, **kwargs: smolagent_tool(*args, **kwargs)
    else:
        raise ValueError(f"Cannot find callable function in tool: {smolagent_tool}")

    # Get input schema if available
    input_schema = getattr(smolagent_tool, 'inputs', {})

    # Build function signature and annotations from input schema
    params = []
    annotations = {}

    if input_schema:
        for param_name, param_info in input_schema.items():
            param_type = param_info.get('type', 'string')
            # Map Smolagents types to Python types
            type_mapping = {
                'string': str,
                'integer': int,
                'number': float,
                'boolean': bool,
                'text': str,
                'any': Any
            }
            python_type = type_mapping.get(param_type, str)
            annotations[param_name] = python_type

            # Create parameter with default if optional
            is_required = not param_info.get('nullable', False)
            if is_required:
                params.append(inspect.Parameter(
                    param_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=python_type
                ))
            else:
                params.append(inspect.Parameter(
                    param_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=None,
                    annotation=python_type
                ))

    # Create wrapper function
    def wrapper(**kwargs):
        """Wrapper that calls the original Smolagents tool"""
        try:
            # Call the original function
            result = original_fn(**kwargs)
            return result
        except Exception as e:
            return f"Error executing {func_name}: {str(e)}"

    # Set function metadata
    wrapper.__name__ = func_name
    wrapper.__doc__ = func_description
    wrapper.__annotations__ = annotations

    # Create signature
    if params:
        wrapper.__signature__ = inspect.Signature(parameters=params)

    # Convert to LangChain tool
    langchain_wrapped = langchain_tool(wrapper)

    return langchain_wrapped


def batch_convert_tools(smolagent_tools: list) -> list:
    """
    Batch convert a list of Smolagents tools to LangChain format

    Args:
        smolagent_tools: List of Smolagents tools

    Returns:
        List of LangChain-compatible tools
    """
    langchain_tools = []
    failed_tools = []

    for tool in smolagent_tools:
        try:
            converted_tool = smolagent_to_langchain(tool)
            langchain_tools.append(converted_tool)
        except Exception as e:
            tool_name = getattr(tool, 'name', str(tool))
            failed_tools.append((tool_name, str(e)))
            print(f"⚠️ Failed to convert tool '{tool_name}': {e}")

    if failed_tools:
        print(f"\n❌ Failed to convert {len(failed_tools)} tools:")
        for name, error in failed_tools:
            print(f"  - {name}: {error}")

    print(f"\n✅ Successfully converted {len(langchain_tools)}/{len(smolagent_tools)} tools")

    return langchain_tools
