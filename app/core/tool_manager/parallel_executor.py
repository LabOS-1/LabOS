"""
Parallel Tool Executor - Execute Tools Concurrently

This module provides parallel execution of multiple tools:
- Execute tool calls in parallel using ThreadPoolExecutor
- Timeout control for each tool call
- Detailed error handling and reporting
- Performance metrics and speedup calculation
"""

from smolagents import tool
import concurrent.futures
import time


@tool
def execute_tools_in_parallel(tool_calls: list, max_workers: int = 3, timeout: int = 30) -> str:
    """Execute multiple tool calls in parallel to improve efficiency.

    Args:
        tool_calls: List of tool call dictionaries with 'tool_name' and 'args' keys
        max_workers: Maximum number of parallel workers (default: 3)
        timeout: Timeout in seconds for each tool call (default: 30)

    Returns:
        Formatted results from all parallel tool executions

    Example:
        tool_calls = [
            {"tool_name": "query_pubmed", "args": {"query": "protein research", "max_results": 5}},
            {"tool_name": "query_uniprot", "args": {"genes": ["FAST"], "fields": "function"}},
            {"tool_name": "multi_source_search", "args": {"query": "cell fusion", "sources": "google"}}
        ]
        results = execute_tools_in_parallel(tool_calls)
    """
    try:
        # Import manager_agent from parent module
        from .. import labos_engine
        manager_agent = stella_engine.manager_agent

        if not tool_calls:
            return "❌ No tool calls provided for parallel execution"

        if not isinstance(tool_calls, list):
            return "❌ tool_calls must be a list of dictionaries"

        # Validate tool calls format
        for i, call in enumerate(tool_calls):
            if not isinstance(call, dict):
                return f"❌ Tool call {i+1} must be a dictionary"
            if 'tool_name' not in call:
                return f"❌ Tool call {i+1} missing 'tool_name'"
            if 'args' not in call:
                return f"❌ Tool call {i+1} missing 'args'"

            # Check if tool exists (flexible approach)
            tool_name = call['tool_name']
            tool_found = False

            try:
                # Try dictionary access first
                if hasattr(manager_agent.tools, 'get'):
                    tool_found = manager_agent.tools.get(tool_name) is not None
                elif hasattr(manager_agent.tools, '__contains__'):
                    tool_found = tool_name in manager_agent.tools
                else:
                    # List-like search
                    tool_found = any(getattr(t, 'name', getattr(t, '__name__', str(t))) == tool_name for t in manager_agent.tools)
            except:
                tool_found = False

            if not tool_found:
                return f"❌ Tool '{tool_name}' not found in loaded tools"

        def execute_single_tool(tool_call):
            """Execute a single tool call with timeout"""
            tool_name = tool_call['tool_name']
            args = tool_call['args']
            start_time = time.time()

            try:
                # Get tool function - flexible approach
                tool_func = None

                # Try different ways to access the tool
                if hasattr(manager_agent.tools, 'get'):
                    # Dictionary-like access
                    tool_func = manager_agent.tools.get(tool_name)
                elif hasattr(manager_agent.tools, '__getitem__'):
                    # Dictionary or list-like with indexing
                    try:
                        tool_func = manager_agent.tools[tool_name]
                    except (KeyError, TypeError):
                        # Maybe it's a list, search by name
                        for tool in manager_agent.tools:
                            if getattr(tool, 'name', getattr(tool, '__name__', str(tool))) == tool_name:
                                tool_func = tool
                                break
                else:
                    # List-like search
                    for tool in manager_agent.tools:
                        if getattr(tool, 'name', getattr(tool, '__name__', str(tool))) == tool_name:
                            tool_func = tool
                            break

                if tool_func is None:
                    raise ValueError(f"Tool '{tool_name}' not found")

                # Handle different tool calling conventions with debugging
                import inspect

                # Check if this is a dynamic tool that expects positional args
                if 'args' in args and isinstance(args['args'], str):
                    # This is likely a dynamic tool that expects a positional string argument
                    try:
                        # Extract additional parameters
                        sanitize = args.get('sanitize_inputs_outputs', False)
                        kwargs = {k: v for k, v in args.items() if k not in ['args', 'sanitize_inputs_outputs']}

                        # Call with positional argument first
                        if kwargs:
                            result = tool_func(args['args'], sanitize_inputs_outputs=sanitize, **kwargs)
                        else:
                            result = tool_func(args['args'], sanitize_inputs_outputs=sanitize)
                    except Exception as e:
                        # If that fails, try standard keyword arguments
                        try:
                            result = tool_func(**args)
                        except Exception as ex:
                            # Re-raise the original error
                            raise e
                else:
                    # Standard tool with keyword arguments
                    try:
                        result = tool_func(**args)
                    except TypeError as e:
                        error_str = str(e)

                        # Try to provide helpful hints based on the error
                        if "unexpected keyword argument" in error_str:
                            # Try extracting the positional arg if present
                            if 'prompt' in args:
                                try:
                                    result = tool_func(args['prompt'], **{k: v for k, v in args.items() if k != 'prompt'})
                                except:
                                    raise e
                            else:
                                raise
                        else:
                            raise
                duration = time.time() - start_time

                return {
                    'tool_name': tool_name,
                    'success': True,
                    'result': result,
                    'duration': duration,
                    'error': None
                }
            except Exception as e:
                duration = time.time() - start_time
                return {
                    'tool_name': tool_name,
                    'success': False,
                    'result': None,
                    'duration': duration,
                    'error': str(e)
                }

        # Execute tools in parallel
        results = []
        start_total = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tool calls
            future_to_call = {
                executor.submit(execute_single_tool, call): call
                for call in tool_calls
            }

            # Collect results with timeout
            for future in concurrent.futures.as_completed(future_to_call, timeout=timeout):
                try:
                    result = future.result(timeout=5)  # Individual result timeout
                    results.append(result)
                except concurrent.futures.TimeoutError:
                    call = future_to_call[future]
                    results.append({
                        'tool_name': call['tool_name'],
                        'success': False,
                        'result': None,
                        'duration': timeout,
                        'error': 'Timeout'
                    })
                except Exception as e:
                    call = future_to_call[future]
                    results.append({
                        'tool_name': call['tool_name'],
                        'success': False,
                        'result': None,
                        'duration': 0,
                        'error': str(e)
                    })

        total_duration = time.time() - start_total

        # Format results
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]

        output = f"🚀 Parallel Execution Complete ({len(tool_calls)} tools, {total_duration:.1f}s total)\n"
        output += f"✅ Successful: {len(successful)} | ❌ Failed: {len(failed)}\n\n"

        # Show successful results
        if successful:
            output += "📋 Successful Results:\n"
            for result in successful:
                tool_name = result['tool_name']
                duration = result['duration']
                result_preview = str(result['result'])[:100] + "..." if len(str(result['result'])) > 100 else str(result['result'])
                output += f"  ✅ {tool_name} ({duration:.1f}s): {result_preview}\n"

        # Show failed results
        if failed:
            output += f"\n❌ Failed Results:\n"
            for result in failed:
                tool_name = result['tool_name']
                error = result['error']
                output += f"  ❌ {tool_name}: {error}\n"

        # Performance summary
        if successful:
            avg_duration = sum(r['duration'] for r in successful) / len(successful)
            max_duration = max(r['duration'] for r in successful)
            output += f"\n📊 Performance: Avg {avg_duration:.1f}s, Max {max_duration:.1f}s"

            # Calculate efficiency gain
            sequential_time = sum(r['duration'] for r in successful)
            if sequential_time > total_duration:
                speedup = sequential_time / total_duration
                output += f", {speedup:.1f}x speedup vs sequential"

        return output

    except Exception as e:
        return f"❌ Parallel execution error: {str(e)}"
