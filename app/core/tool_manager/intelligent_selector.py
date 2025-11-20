"""
Intelligent Tool Selector - LLM-based Tool Selection

This module provides intelligent tool selection and loading:
- Analyze user queries using LLM
- Select most relevant tools from available tool files
- Fallback to keyword matching if LLM fails
- Caching mechanism to reduce repeated LLM calls
"""

from smolagents import tool
import hashlib
import time
import threading
import os
import sys
import inspect
import importlib.util

# Tool loading cache and lock
tool_loading_cache = {}
tool_loading_lock = threading.Lock()


@tool
def analyze_query_and_load_relevant_tools(user_query: str, max_tools: int = 10) -> str:
    """Analyze user query using LLM and intelligently load the most relevant tools.

    Optimized version with caching and reduced token usage.

    Args:
        user_query: The user's task description or query
        max_tools: Maximum number of relevant tools to load (default: 10)

    Returns:
        Status of the tool loading operation with analysis details
    """
    try:
        # Import agents from parent module
        from .. import labos_engine
        manager_agent = stella_engine.manager_agent
        tool_creation_agent = stella_engine.tool_creation_agent

        # Check cache first
        query_hash = hashlib.md5(user_query.encode()).hexdigest()
        cache_key = f"{query_hash}_{max_tools}"

        with tool_loading_lock:
            if cache_key in tool_loading_cache:
                cached_result, cached_time = tool_loading_cache[cache_key]
                # Use cache if less than 5 minutes old
                if time.time() - cached_time < 300:
                    return f"🔄 Using cached tool selection\n{cached_result}"

        # Import LLM functionality
        from ...tools.llm import json_llm_call

        # Define tool files to analyze
        script_dir = os.getcwd()
        tool_files = {
            'literature_tools': os.path.join(script_dir, 'app', 'tools', 'literature.py'),
            'database_tools': os.path.join(script_dir, 'app', 'tools', 'database.py'),
            'virtual_screening_tools': os.path.join(script_dir, 'app', 'tools', 'screening.py')
        }

        available_tools = {}

        # Extract tools and their descriptions from each file
        for module_name, file_path in tool_files.items():
            if not os.path.exists(file_path):
                continue

            try:
                # Load the module
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Find all tools (SimpleTool objects created by @tool decorator)
                for name, obj in inspect.getmembers(module):
                    if hasattr(obj, '__class__') and 'SimpleTool' in str(type(obj)):
                        # Extract description from tool object or docstring
                        if hasattr(obj, 'description') and obj.description:
                            description = obj.description
                        else:
                            doc = inspect.getdoc(obj) or ""
                            description = doc.split('\n\n')[0].replace('\n', ' ').strip()

                        available_tools[name] = {
                            'function': obj,
                            'description': description,
                            'module': module_name,
                            'file_path': file_path
                        }

            except Exception as e:
                continue

        if not available_tools:
            return f"❌ No tools found in literature_tools.py, database_tools.py, or virtual_screening_tools.py"

        # Create tool list for LLM analysis - OPTIMIZED
        tool_list = []
        for tool_name, tool_info in available_tools.items():
            tool_list.append({
                "name": tool_name,
                "description": tool_info['description'][:100],  # Truncate descriptions
                "module": tool_info['module']
            })

        # Create OPTIMIZED LLM prompt for intelligent tool selection
        llm_prompt = f"""Select relevant tools for this query: "{user_query}"

Available tools ({len(tool_list)}):
{chr(10).join([f"{i+1}. {tool['name']} [{tool['module']}]: {tool['description']}" for i, tool in enumerate(tool_list[:20])])}

Return JSON with top {max_tools} most relevant tools:
{{
    "selected_tools": [
        {{"name": "tool_name", "relevance_score": 0.95}}
    ]
}}"""

        # Use LLM to select tools intelligently
        try:
            llm_response = json_llm_call(llm_prompt, "gemini-2.5-flash")

            if "error" in llm_response:
                # Fallback to simple keyword matching if LLM fails
                return _fallback_tool_selection(user_query, available_tools, max_tools, manager_agent, tool_creation_agent)

            selected_tool_data = llm_response.get("selected_tools", [])

            if not selected_tool_data:
                return f"🔍 LLM analysis found no relevant tools for query: '{user_query}'"

        except Exception as e:
            # Fallback to simple selection if LLM fails completely
            return _fallback_tool_selection(user_query, available_tools, max_tools, manager_agent, tool_creation_agent)

        # Load selected tools into agents
        loaded_tools = []
        loaded_count = 0

        for tool_selection in selected_tool_data:
            tool_name = tool_selection.get("name")

            if tool_name not in available_tools:
                continue

            try:
                tool_info = available_tools[tool_name]
                tool_func = tool_info['function']

                # Add to manager_agent tools if not already present
                if tool_name not in manager_agent.tools:
                    manager_agent.tools[tool_name] = tool_func

                    # Important: also update CodeAgent's Python executor
                    if hasattr(manager_agent, 'python_executor') and hasattr(manager_agent.python_executor, 'custom_tools'):
                        manager_agent.python_executor.custom_tools[tool_name] = tool_func

                    loaded_count += 1

                # Add to tool_creation_agent tools if not already present
                if tool_name not in tool_creation_agent.tools:
                    tool_creation_agent.tools[tool_name] = tool_func

                    # Important: also update CodeAgent's Python executor
                    if hasattr(tool_creation_agent, 'python_executor') and hasattr(tool_creation_agent.python_executor, 'custom_tools'):
                        tool_creation_agent.python_executor.custom_tools[tool_name] = tool_func

                loaded_tools.append({
                    'name': tool_name,
                    'relevance': tool_selection.get("relevance_score", 0.0),
                    'module': tool_info['module']
                })

            except Exception as e:
                continue

        # Generate concise result summary
        result = f"🎯 Loaded {loaded_count} tools for: '{user_query[:50]}...'\n"
        result += f"Tools: {', '.join([t['name'] for t in loaded_tools[:5]])}"
        if len(loaded_tools) > 5:
            result += f" (+{len(loaded_tools)-5} more)"

        # Cache the result
        with tool_loading_lock:
            tool_loading_cache[cache_key] = (result, time.time())

        return result

    except Exception as e:
        return f"❌ Error analyzing query and loading tools: {str(e)}"


def _fallback_tool_selection(user_query: str, available_tools: dict, max_tools: int,
                              manager_agent, tool_creation_agent) -> str:
    """Fallback tool selection using simple keyword matching when LLM fails.

    Args:
        user_query: The user's query
        available_tools: Dictionary of available tools
        max_tools: Maximum number of tools to load
        manager_agent: Manager agent instance
        tool_creation_agent: Tool creation agent instance

    Returns:
        Summary of loaded tools
    """
    query_lower = user_query.lower()
    tool_scores = []

    # Simple keyword matching
    for tool_name, tool_info in available_tools.items():
        tool_text = f"{tool_name.replace('_', ' ')} {tool_info['description']}".lower()

        # Score based on keyword matches
        score = 0
        query_words = query_lower.split()
        for word in query_words:
            if len(word) > 2 and word in tool_text:
                score += 1

        tool_scores.append((tool_name, score))

    # Sort by score and take top tools
    tool_scores.sort(key=lambda x: x[1], reverse=True)
    selected_tools = tool_scores[:max_tools]

    if not selected_tools or all(score == 0 for _, score in selected_tools):
        return f"🔍 No relevant tools found for query: '{user_query}' (fallback method used)"

    # Load tools and return summary
    loaded_count = 0
    for tool_name, score in selected_tools:
        if score > 0:
            tool_func = available_tools[tool_name]['function']

            # Add to manager_agent
            if tool_name not in manager_agent.tools:
                manager_agent.tools[tool_name] = tool_func

                # Important: also update CodeAgent's Python executor
                if hasattr(manager_agent, 'python_executor') and hasattr(manager_agent.python_executor, 'custom_tools'):
                    manager_agent.python_executor.custom_tools[tool_name] = tool_func

                loaded_count += 1

            # Add to tool_creation_agent
            if tool_name not in tool_creation_agent.tools:
                tool_creation_agent.tools[tool_name] = tool_func

                # Important: also update CodeAgent's Python executor
                if hasattr(tool_creation_agent, 'python_executor') and hasattr(tool_creation_agent.python_executor, 'custom_tools'):
                    tool_creation_agent.python_executor.custom_tools[tool_name] = tool_func

    return f"🎯 Fallback Analysis: '{user_query}'\n✅ Loaded {loaded_count} tools using keyword matching."
