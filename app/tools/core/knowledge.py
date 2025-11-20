"""
Knowledge Tools - Knowledge base management tools
For saving and retrieving problem-solving templates, accessing Mem0 enhanced memory
"""

from smolagents import tool
from functools import lru_cache


@tool
@lru_cache(maxsize=16)  # Cache template retrievals
def retrieve_similar_templates(task_description: str, top_k: int = 3, user_id: str = "default") -> str:
    """Retrieve similar problem-solving templates from the knowledge base.
    
    Optimized with caching and reduced output.
    
    Args:
        task_description: Description of the current task
        top_k: Number of similar templates to retrieve (default: 3)
        user_id: User ID for personalized memory retrieval (default: "default")
        
    Returns:
        List of similar templates with reasoning approaches
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    
    if not use_templates:
        return "📋 Template usage is disabled. Use --use_template to enable."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    try:
        # Use the new knowledge memory component
        result = global_memory_manager.knowledge.search_templates(task_description, top_k, user_id)
        if result["success"]:
            similar_templates = result["templates"]
        else:
            similar_templates = []
        
        if not similar_templates:
            return "📚 No similar templates found in knowledge base."
        
        # Optimized output - more concise
        result = f"📚 Found {len(similar_templates)} templates:\n"
        
        for i, template in enumerate(similar_templates, 1):
            similarity = template.get('similarity', 0.0)
            task = template.get('task', '')[:80]  # Reduced from 150
            result += f"{i}. {task}... (Sim: {similarity:.2f})\n"
        
        return result
        
    except Exception as e:
        return f"❌ Error retrieving templates: {str(e)}"


@tool
def save_successful_template(task_description: str, reasoning_process: str, solution_outcome: str, domain: str = "general", user_id: str = "default") -> str:
    """Save a successful problem-solving approach to the knowledge base.
    
    Args:
        task_description: Description of the solved task
        reasoning_process: The reasoning process that led to success
        solution_outcome: The successful outcome achieved
        domain: Domain category (default: "general")
        user_id: User ID for personalized memory storage (default: "default")
        
    Returns:
        Status of the save operation
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    
    if not use_templates:
        return "📋 Template usage is disabled. Use --use_template to enable."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    try:
        # Use the new knowledge memory component to save template
        result = global_memory_manager.knowledge.add_template(task_description, reasoning_process, solution_outcome, domain, user_id)
        
        if result.get("success", False):
            # Get statistics
            stats = global_memory_manager.knowledge.get_stats(user_id)
            total_templates = stats.get('total_templates', 0)
            return f"✅ Template saved! Total: {total_templates}"
        else:
            return f"❌ Failed to save template: {result.get('message', 'Unknown error')}"
        
    except Exception as e:
        return f"❌ Error saving template: {str(e)}"


@tool
def list_knowledge_base_status(user_id: str = "default") -> str:
    """Get status and statistics of the knowledge base.
    
    Optimized to return concise information.
    
    Args:
        user_id: User ID for personalized memory statistics (default: "default")
    
    Returns:
        Knowledge base status and statistics
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    
    if not use_templates:
        return "📋 Template usage is disabled."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    try:
        # Get knowledge memory component statistics
        stats = global_memory_manager.knowledge.get_stats(user_id)
        
        result = f"📚 Memory Status: {stats.get('backend', 'Unknown')} - {stats.get('total_templates', 0)} templates"
        
        return result
        
    except Exception as e:
        return f"❌ Error getting memory system status: {str(e)}"


@tool
def search_templates_by_keyword(keyword: str, user_id: str = "default", limit: int = 5) -> str:
    """Search templates in the knowledge base by keyword.
    
    Args:
        keyword: Keyword to search for in templates
        user_id: User ID for personalized search (default: "default")
        limit: Maximum number of results to return (default: 5)
        
    Returns:
        Matching templates containing the keyword
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    
    if not use_templates:
        return "📋 Template usage is disabled. Use --use_template to enable."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    try:
        # Use knowledge memory component for semantic search
        result = global_memory_manager.knowledge.search_templates(keyword, limit, user_id)
        if result["success"]:
            matching_results = result["templates"]
        else:
            matching_results = []
            
        if not matching_results:
            return f"🔍 No memories found containing keyword '{keyword}'."
            
        result = f"🔍 Found {len(matching_results)} memories:\n"
        
        for i, memory_result in enumerate(matching_results, 1):
            memory_text = memory_result.get('memory', str(memory_result))
            result += f"{i}. {memory_text[:100]}...\n"
            
        return result
        
    except Exception as e:
        return f"❌ Error searching templates: {str(e)}"


@tool
def get_user_memories(user_id: str = "default", limit: int = 10) -> str:
    """Get all memories for a specific user (Mem0 enhanced feature).
    
    Args:
        user_id: User ID to retrieve memories for (default: "default")
        limit: Maximum number of memories to display (default: 10)
        
    Returns:
        List of user memories
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    
    if not use_templates:
        return "📋 Template usage is disabled. Use --use_template to enable."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    if not hasattr(global_memory_manager, 'session') or global_memory_manager.session is None:
        return "❌ This feature requires Mem0 enhanced memory system. Use --use_mem0 to enable."
    
    try:
        memories = global_memory_manager.session.get_user_memories(user_id)
        
        if not memories:
            return f"📚 No memories found for user '{user_id}'."
        
        result = f"📚 Memories for user '{user_id}' ({min(len(memories), limit)} of {len(memories)}):\n"
        
        for i, memory in enumerate(memories[:limit], 1):
            memory_text = memory.get('memory', str(memory))[:150]  # Reduced from 300
            result += f"{i}. {memory_text}...\n"
        
        return result
        
    except Exception as e:
        return f"❌ Error retrieving user memories: {str(e)}"

