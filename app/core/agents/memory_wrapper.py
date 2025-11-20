"""
Memory System Wrapper for Agents

This module wraps agents with automatic memory recording:
- Record task execution history
- Track tool usage statistics
- Monitor performance metrics
- Enable experience recall for similar tasks
"""

import time


def create_memory_enabled_agent(agent, agent_name):
    """Wrap an agent to automatically record task performance.

    Args:
        agent: The agent to wrap
        agent_name: Name of the agent for logging

    Returns:
        Wrapped agent with memory recording enabled
    """
    from ..auto_memory import auto_memory

    original_run = agent.run

    def run_with_memory(*args, **kwargs):
        """Enhanced run method that automatically records task performance and suggests improvements."""
        start_time = time.time()
        success = False
        result = ""

        # Extract task from args or kwargs
        task = args[0] if args else kwargs.get('task', 'Unknown task')

        try:
            # Check for similar past tasks first
            similar = auto_memory.get_similar_tasks(str(task), 2)
            if similar:
                print(f"💡 {agent_name}: Found {len(similar)} similar successful tasks")

            # Execute the task with all original arguments
            result = original_run(*args, **kwargs)
            success = True

            # Record tool usage (simplified) - avoid errors
            try:
                tools_used = getattr(agent, 'tools', [])
                if tools_used and isinstance(tools_used, list):
                    # Only record the last few tools to avoid excessive logging
                    recent_tools = tools_used[-3:] if len(tools_used) >= 3 else tools_used
                    for tool in recent_tools:
                        tool_name = getattr(tool, '__name__', getattr(tool, 'name', str(tool)))
                        auto_memory.record_tool_use(tool_name, success)
            except Exception:
                # Silent fail - don't break the main task for tool recording
                pass

            return result

        except Exception as e:
            result = str(e)
            raise

        finally:
            # Always record the task attempt
            duration = time.time() - start_time
            auto_memory.record_task(agent_name, str(task), str(result)[:100], success, duration)

    # Replace the run method
    agent.run = run_with_memory
    return agent
