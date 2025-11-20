"""
Collaboration Tools - Multi-agent collaboration tools
For creating shared workspaces, managing task breakdowns, and tracking progress
"""

from smolagents import tool


@tool
def create_shared_workspace(workspace_id: str, task_description: str, participating_agents: str = "dev_agent,manager_agent,critic_agent") -> str:
    """Create a shared workspace for agent team collaboration.
    
    Args:
        workspace_id: Unique identifier for the workspace
        task_description: Description of the collaborative task
        participating_agents: Comma-separated list of agent names
        
    Returns:
        Workspace creation status and details
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    
    if not use_templates:
        return "📋 Template usage is disabled. Use --use_template to enable collaboration features."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    if not hasattr(global_memory_manager, 'collaboration') or global_memory_manager.collaboration is None:
        return "❌ This feature requires enhanced memory system. Use --use_template to enable."
    
    try:
        agents_list = [agent.strip() for agent in participating_agents.split(',')]
        
        result = global_memory_manager.collaboration.create_shared_workspace(
            workspace_id=workspace_id,
            task_description=task_description,
            participating_agents=agents_list
        )
        
        if result["success"]:
            return f"✅ Workspace '{workspace_id}' created with {len(result['participating_agents'])} agents"
        else:
            return f"❌ Failed to create workspace: {result['message']}"
            
    except Exception as e:
        return f"❌ Error creating shared workspace: {str(e)}"


@tool
def add_workspace_memory(workspace_id: str, agent_name: str, content: str, memory_type: str = "observation") -> str:
    """Add memory/observation to a shared workspace.
    
    Args:
        workspace_id: ID of the target workspace
        agent_name: Name of the contributing agent  
        content: The observation, discovery, or result to share
        memory_type: Type of memory (observation, discovery, result, question)
        
    Returns:
        Status of memory addition
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    
    if not use_templates:
        return "📋 Template usage is disabled. Use --use_template to enable."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    if not hasattr(global_memory_manager, 'collaboration') or global_memory_manager.collaboration is None:
        return "❌ This feature requires enhanced memory system. Use --use_template to enable."
    
    try:
        result = global_memory_manager.collaboration.add_workspace_memory(
            workspace_id=workspace_id,
            agent_name=agent_name,
            content=content,
            memory_type=memory_type
        )
        
        if result["success"]:
            return f"✅ Memory added to workspace '{workspace_id}'"
        else:
            return f"❌ Failed to add workspace memory: {result['message']}"
            
    except Exception as e:
        return f"❌ Error adding workspace memory: {str(e)}"


@tool
def get_workspace_memories(workspace_id: str, memory_type: str = "all", limit: int = 10) -> str:
    """Retrieve memories from a shared workspace.
    
    Optimized to return concise information.
    
    Args:
        workspace_id: ID of the target workspace
        memory_type: Type filter (all, observation, discovery, result, question)
        limit: Maximum number of memories to retrieve
        
    Returns:
        Formatted list of workspace memories
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    
    if not use_templates:
        return "📋 Template usage is disabled. Use --use_template to enable."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    if not hasattr(global_memory_manager, 'collaboration') or global_memory_manager.collaboration is None:
        return "❌ This feature requires enhanced memory system. Use --use_template to enable."
    
    try:
        result = global_memory_manager.collaboration.get_workspace_memories(
            workspace_id=workspace_id,
            memory_type=memory_type,
            limit=limit
        )
        
        if result["success"]:
            if not result["memories"]:
                return f"📭 No memories found in workspace '{workspace_id}'"
            
            output = f"🏢 Workspace '{workspace_id}' ({result['total_found']} memories):\n"
            
            for i, memory in enumerate(result["memories"], 1):
                metadata = memory.get('metadata', {})
                agent = metadata.get('agent_name', 'Unknown')
                mem_type = metadata.get('memory_type', 'unknown')
                content = memory.get('memory', str(memory))[:100]  # Reduced from 200
                
                output += f"{i}. [{mem_type}] {agent}: {content}...\n"
            
            return output
        else:
            return f"❌ Failed to retrieve workspace memories: {result.get('message', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Error retrieving workspace memories: {str(e)}"


@tool
def create_task_breakdown(task_id: str, main_task: str, subtasks: str, agent_assignments: str = "") -> str:
    """Create a task breakdown with tracking for complex collaborative tasks.
    
    Args:
        task_id: Unique identifier for the task
        main_task: Description of the main task
        subtasks: JSON array string of subtask descriptions  
        agent_assignments: JSON object string mapping subtask indices to agent names
        
    Returns:
        Task breakdown creation status
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    import json
    
    if not use_templates:
        return "📋 Template usage is disabled. Use --use_template to enable."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    if not hasattr(global_memory_manager, 'collaboration') or global_memory_manager.collaboration is None:
        return "❌ This feature requires enhanced memory system. Use --use_template to enable."
    
    try:
        # Parse subtasks
        try:
            subtasks_list = json.loads(subtasks)
        except json.JSONDecodeError:
            # Fallback: split by line or comma
            subtasks_list = [task.strip() for task in subtasks.replace('\n', ',').split(',') if task.strip()]
        
        # Parse agent assignments
        assignments_dict = {}
        if agent_assignments:
            try:
                assignments_dict = json.loads(agent_assignments)
            except json.JSONDecodeError:
                # Ignore malformed assignments
                pass
        
        result = global_memory_manager.collaboration.create_task_breakdown(
            task_id=task_id,
            main_task=main_task,
            subtasks=subtasks_list,
            agent_assignments=assignments_dict
        )
        
        if result["success"]:
            return f"✅ Task '{task_id}' created with {result['subtasks_created']} subtasks"
        else:
            return f"❌ Failed to create task breakdown: {result['message']}"
            
    except Exception as e:
        return f"❌ Error creating task breakdown: {str(e)}"


@tool  
def update_subtask_status(task_id: str, subtask_index: int, new_status: str, agent_name: str, progress_notes: str = "") -> str:
    """Update the status of a specific subtask.
    
    Args:
        task_id: ID of the parent task
        subtask_index: Index of the subtask (0-based)
        new_status: New status (pending, in_progress, completed, blocked)
        agent_name: Name of the agent updating the status
        progress_notes: Optional notes about the progress
        
    Returns:
        Status update confirmation
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    
    if not use_templates:
        return "📋 Template usage is disabled. Use --use_template to enable."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    if not hasattr(global_memory_manager, 'collaboration') or global_memory_manager.collaboration is None:
        return "❌ This feature requires enhanced memory system. Use --use_template to enable."
    
    try:
        result = global_memory_manager.collaboration.update_subtask_status(
            task_id=task_id,
            subtask_index=subtask_index,
            new_status=new_status,
            agent_name=agent_name,
            progress_notes=progress_notes
        )
        
        if result["success"]:
            return f"✅ Subtask #{subtask_index} updated to {new_status}"
        else:
            return f"❌ Failed to update subtask status: {result['message']}"
            
    except Exception as e:
        return f"❌ Error updating subtask status: {str(e)}"


@tool
def get_task_progress(task_id: str) -> str:
    """Get comprehensive progress overview for a collaborative task.
    
    Optimized to return concise progress information.
    
    Args:
        task_id: ID of the task to check
        
    Returns:
        Detailed progress report with statistics and recent updates
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    
    if not use_templates:
        return "📋 Template usage is disabled. Use --use_template to enable."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    if not hasattr(global_memory_manager, 'collaboration') or global_memory_manager.collaboration is None:
        return "❌ This feature requires enhanced memory system. Use --use_template to enable."
    
    try:
        result = global_memory_manager.collaboration.get_task_progress(task_id)
        
        if result["success"]:
            progress = result["progress"]
            
            if not progress.get("main_task"):
                return f"❌ Task '{task_id}' not found"
            
            # Concise output
            output = f"📊 Task '{task_id}': {progress['progress_percentage']}% complete\n"
            output += f"✅ {progress['completed']} / {progress['total_subtasks']} done"
            
            return output
        else:
            return f"❌ Failed to get task progress: {result.get('message', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Error getting task progress: {str(e)}"


@tool
def get_agent_contributions(agent_name: str) -> str:
    """Get statistics about an agent's contributions to team collaboration.
    
    Args:
        agent_name: Name of the agent to analyze
        
    Returns:
        Summary of the agent's collaboration statistics
    """
    from app.core.stella_engine import global_memory_manager, use_templates
    
    if not use_templates:
        return "📋 Template usage is disabled. Use --use_template to enable."
    
    if global_memory_manager is None:
        return "❌ Memory manager not initialized."
    
    if not hasattr(global_memory_manager, 'collaboration') or global_memory_manager.collaboration is None:
        return "❌ This feature requires enhanced memory system. Use --use_template to enable."
    
    try:
        result = global_memory_manager.collaboration.get_agent_contributions(agent_name)
        
        if result["success"]:
            contrib = result["contributions"]
            
            output = f"📊 {agent_name} contributions: "
            output += f"{contrib['total_contributions']} total "
            output += f"({contrib['discoveries_shared']} discoveries, "
            output += f"{contrib['workspace_contributions']} workspace, "
            output += f"{contrib['task_updates']} updates)"
            
            return output
        else:
            return f"❌ Failed to get agent contributions: {result.get('message', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Error getting agent contributions: {str(e)}"

