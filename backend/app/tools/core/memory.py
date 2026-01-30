"""
Memory Tools - Memory and performance monitoring tools
These tools help agents recall past tasks and monitor performance
"""

from smolagents import tool

# Import auto_memory from dedicated module
from app.core.memory.auto_memory import auto_memory


@tool
def auto_recall_experience(task_description: str) -> str:
    """Automatically recall similar past tasks and their outcomes.
    
    Args:
        task_description: Description of the current task to find similar experiences for
        
    Returns:
        List of similar successful tasks with execution times and recommended agent
    """
    similar_tasks = auto_memory.get_similar_tasks(task_description, 3)
    
    if not similar_tasks:
        return "No similar past tasks found"
    
    result = f"Found {len(similar_tasks)} similar tasks:\n"
    for i, task in enumerate(similar_tasks, 1):
        duration = task['duration']
        result += f"{i}. {task['task']} - took {duration:.1f}s\n"
    
    # Suggest best agent
    best_agent = auto_memory.get_best_agent_for_task(task_description)
    if best_agent:
        result += f"\nRecommended agent: {best_agent}"
    
    return result


@tool 
def check_agent_performance() -> str:
    """Check which agents perform best on different types of tasks.
    
    Returns:
        Performance statistics for all agents including success rates and average execution times
    """
    if not auto_memory.agent_performance:
        return "No performance data available yet"
    
    result = "Agent Performance:\n"
    for agent, stats in auto_memory.agent_performance.items():
        success_rate = stats['success'] / stats['total'] if stats['total'] > 0 else 0
        result += f"- {agent}: {success_rate:.0%} success, avg {stats['avg_duration']:.1f}s ({stats['total']} tasks)\n"
    
    return result


@tool
def quick_tool_stats() -> str:
    """Quick overview of which tools work best.
    
    Returns:
        Tool effectiveness rankings showing success rates and usage counts
    """
    if not auto_memory.tool_usage:
        return "No tool usage data yet"
    
    # Sort by success rate
    tool_stats = []
    for tool, stats in auto_memory.tool_usage.items():
        if stats['uses'] > 0:
            success_rate = stats['success'] / stats['uses']
            tool_stats.append((success_rate, tool, stats['uses']))
    
    tool_stats.sort(reverse=True)
    
    result = "Top performing tools:\n"
    for rate, tool, uses in tool_stats[:5]:
        result += f"- {tool}: {rate:.0%} success ({uses} uses)\n"
    
    return result

