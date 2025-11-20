"""
Workflow Context Management
Provides thread-local storage for workflow context, allowing tools to know
which workflow they're executing in and emit events.

This module uses threading.local() to safely store workflow context per thread,
avoiding conflicts when multiple workflows execute concurrently.
"""

import threading
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from .workflow_events import workflow_event_queue, WorkflowEvent

# Pre-compiled regex patterns for performance
_FILE_ID_PATTERN = re.compile(r'\(file_id:\s*[a-f0-9-]+\)')
_GENERATED_VIZ_PATTERN = re.compile(r'Generated visualization:')
_IMAGE_EXTENSION_PATTERN = re.compile(r'\.(?:png|jpg|jpeg|gif|svg)', re.IGNORECASE)
_NEW_FORMAT_VIZ_PATTERN = re.compile(r'Generated visualization:\s*([^\s]+\.(?:png|jpg|jpeg|gif|svg|webp))\s*\(file_id:\s*([a-f0-9-]+)\)')
_OLD_FORMAT_VIZ_PATTERN = re.compile(r'Saved file:\s*([^\s]+\.(?:png|jpg))\s*\(([^)]+)\)\s*-\s*ID:\s*([a-f0-9-]+)')

def _is_visualization_tool(tool_name: str) -> bool:
    """Check if tool is a visualization tool (simple set membership)"""
    VISUALIZATION_TOOLS = {
        'create_line_plot',
        'create_bar_chart',
        'create_scatter_plot',
        'create_heatmap',
        'create_distribution_plot',
        'create_box_plot',
        'create_violin_plot',
        'create_correlation_matrix'
    }
    return tool_name in VISUALIZATION_TOOLS


# Thread-local storage for workflow context
_context = threading.local()


class WorkflowCancelledException(Exception):
    """Exception raised when workflow is cancelled"""
    pass


class WorkflowContext:
    """
    Workflow context for the current execution thread.
    
    Stores:
    - workflow_id: Which workflow this thread is executing
    - step_counter: Shared counter for auto-incrementing step numbers
    - metadata: Additional context data
    - is_cancelled: Flag indicating if workflow has been cancelled
    """
    
    def __init__(self, workflow_id: str, step_counter: Dict[str, int]):
        self.workflow_id = workflow_id
        self.step_counter = step_counter  # Shared dict: {'count': N}
        self.metadata: Dict[str, Any] = {}
        self.is_cancelled: bool = False  # Cancellation flag
    
    def __repr__(self):
        return f"WorkflowContext(workflow_id={self.workflow_id}, step={self.step_counter['count']}, cancelled={self.is_cancelled})"


def set_workflow_context(workflow_id: str, step_counter: Dict[str, int], metadata: Optional[Dict[str, Any]] = None):
    """
    Set workflow context for the current thread.
    
    This should be called at the start of Agent execution in the worker thread.
    
    Args:
        workflow_id: Unique workflow identifier
        step_counter: Shared dict for step counting (e.g., {'count': 1})
        metadata: Optional additional context data
    
    Example:
        # In labos_service.py, before running Agent
        def run_agent_with_context():
            set_workflow_context(workflow_id, step_counter)
            return manager_agent.run(message)
        
        response = await loop.run_in_executor(None, run_agent_with_context)
    """
    context = WorkflowContext(workflow_id, step_counter)
    if metadata:
        context.metadata.update(metadata)
    
    _context.workflow_context = context
    print(f"📝 Workflow context set: {context}")


def get_workflow_context() -> Optional[WorkflowContext]:
    """
    Get workflow context for the current thread.
    
    Returns:
        WorkflowContext if set, None if not in a workflow thread
    
    Example:
        context = get_workflow_context()
        if context:
            print(f"I'm in workflow {context.workflow_id}")
    """
    return getattr(_context, 'workflow_context', None)


def clear_workflow_context():
    """
    Clear workflow context for the current thread.
    
    This is automatically called when Agent completes, but can be called
    manually if needed.
    """
    # Remove from global cancelled set if present
    context = get_workflow_context()
    if context and context.workflow_id in _cancelled_workflows:
        _cancelled_workflows.discard(context.workflow_id)
        print(f"🧹 Removed workflow {context.workflow_id} from global cancelled set")
    
    if hasattr(_context, 'workflow_context'):
        delattr(_context, 'workflow_context')
        print(f"🧹 Workflow context cleared")


def has_workflow_context() -> bool:
    """
    Check if current thread has workflow context.
    
    Returns:
        True if context is set, False otherwise
    """
    return hasattr(_context, 'workflow_context')


# === Convenience Functions for Emitting Events ===

# emit_step_event removed - not used in current implementation


def emit_agent_execution_start(agent_name: str, agent_task: str) -> int:
    """
    Emit agent execution start event.

    This creates a new step for agent execution that will be updated
    when the agent completes with tools_used and execution_result.

    Args:
        agent_name: Name of the agent (e.g., "dev_agent")
        agent_task: Task description given to the agent

    Returns:
        step_number: The step number for this agent execution

    Example:
        step_num = emit_agent_execution_start("dev_agent", "Create a bar chart...")
    """
    context = get_workflow_context()
    if not context:
        return 0

    # Increment step counter
    context.step_counter['count'] += 1
    step_number = context.step_counter['count']

    # Create agent execution event
    # Don't truncate description - frontend can handle expansion
    event = WorkflowEvent(
        workflow_id=context.workflow_id,
        event_type="agent_call",
        timestamp=datetime.now(),
        step_number=step_number,
        title=f"🤖 {agent_name.replace('_agent', '').replace('_', ' ').title()} Agent",
        description=agent_task,  # Send full task - frontend will expand/collapse as needed
        tool_name=agent_name,
        step_metadata={
            "agent_name": agent_name,
            "agent_task": agent_task,
            "status": "running",
            "tools_used": []  # Will be populated during execution
        }
    )

    # Add to database queue
    try:
        from app.main import labos_service
        from app.services.workflows.workflow_service import WorkflowStep, WorkflowStepStatus
        from app.models.enums import WorkflowStepType

        db_step = WorkflowStep(
            id=f"{context.workflow_id}_agent_{step_number}",
            type=WorkflowStepType.AGENT_EXECUTION,
            title=event.title,
            description=agent_task,  # Use full agent_task instead of truncated event.description
            status=WorkflowStepStatus.RUNNING,
            agent_name=agent_name,
            agent_task=agent_task,
            step_metadata={"status": "running", "tools_used": []}
        )

        # CRITICAL: Append to the workflow-specific steps list for database persistence
        if hasattr(labos_service, 'workflow_steps_by_id') and context.workflow_id in labos_service.workflow_steps_by_id:
            labos_service.workflow_steps_by_id[context.workflow_id].append(db_step)
            print(f"💾 Added agent execution step to database queue: {agent_name} (step #{step_number}) - Workflow {context.workflow_id} now has {len(labos_service.workflow_steps_by_id[context.workflow_id])} steps")
    except Exception as e:
        print(f"⚠️ Failed to add agent step to database queue: {e}")

    # Emit event for WebSocket broadcast
    workflow_event_queue.put(event)
    print(f"📤 Emitted agent_execution_start: {agent_name} (step #{step_number})")

    # Store in context metadata for later reference
    if 'active_agent_steps' not in context.metadata:
        context.metadata['active_agent_steps'] = {}
    context.metadata['active_agent_steps'][agent_name] = {
        'step_number': step_number,
        'tools_used': [],
        'start_time': datetime.now()
    }

    return step_number


def update_agent_execution_result(agent_name: str, execution_result: str, visualizations: List[Dict] = None) -> bool:
    """
    Update agent execution event with final results.

    This updates the agent step created by emit_agent_execution_start()
    with the collected tools_used and execution_result.

    Args:
        agent_name: Name of the agent
        execution_result: Final result from agent execution
        visualizations: List of visualization metadata

    Returns:
        True if updated successfully

    Example:
        update_agent_execution_result("dev_agent", "Created chart successfully", [...])
    """
    context = get_workflow_context()
    if not context:
        return False

    # Get agent step info from context
    if 'active_agent_steps' not in context.metadata or agent_name not in context.metadata['active_agent_steps']:
        print(f"⚠️ No active agent step found for {agent_name}")
        return False

    agent_info = context.metadata['active_agent_steps'][agent_name]
    step_number = agent_info['step_number']
    tools_used = agent_info.get('tools_used', [])
    start_time = agent_info.get('start_time')

    # Calculate duration
    duration = (datetime.now() - start_time).total_seconds() * 1000 if start_time else None

    # Prepare step_metadata
    step_metadata = {
        "agent_name": agent_name,
        "status": "completed",
        "tools_used": tools_used,
        "execution_duration": duration
    }

    if visualizations:
        step_metadata["visualizations"] = visualizations

    # Create update event
    event = WorkflowEvent(
        workflow_id=context.workflow_id,
        event_type="observation",  # Use observation type for updates
        timestamp=datetime.now(),
        step_number=step_number,  # Same step number as start event
        title=f"✅ {agent_name.replace('_agent', '').replace('_', ' ').title()} Agent - Completed",
        description=f"Used {len(tools_used)} tool(s): {', '.join([t['name'] for t in tools_used])}",
        tool_name=agent_name,
        step_metadata=step_metadata
    )

    # Update database step
    try:
        from app.main import labos_service
        from app.services.workflows.workflow_service import WorkflowStepStatus

        # CRITICAL: Update the agent step in the workflow-specific steps list
        if hasattr(labos_service, 'workflow_steps_by_id') and context.workflow_id in labos_service.workflow_steps_by_id:
            # Find and update the agent step
            for step in labos_service.workflow_steps_by_id[context.workflow_id]:
                if (hasattr(step, 'agent_name') and step.agent_name == agent_name and
                    hasattr(step, 'step_metadata') and step.step_metadata.get('status') == 'running'):
                    step.status = WorkflowStepStatus.COMPLETED
                    step.execution_result = execution_result
                    step.execution_duration = duration
                    step.step_metadata = step_metadata
                    print(f"💾 Updated agent step in database queue: {agent_name}")
                    break
    except Exception as e:
        print(f"⚠️ Failed to update agent step in database: {e}")

    # Emit update event
    workflow_event_queue.put(event)
    print(f"📤 Updated agent_execution: {agent_name} with {len(tools_used)} tools")

    # Clean up context
    del context.metadata['active_agent_steps'][agent_name]

    return True


def add_tool_to_active_agent(tool_name: str, tool_args: Dict[str, Any], tool_result: str, duration: float = None) -> bool:
    """
    Add a tool execution to the currently active agent's tools_used list.

    This is called when a tool is executed within an agent's context.
    The tool info is collected and will be included in the agent's final result.

    Args:
        tool_name: Name of the tool
        tool_args: Tool arguments
        tool_result: Tool result
        duration: Execution duration in ms

    Returns:
        True if added successfully
    """
    context = get_workflow_context()
    if not context:
        return False

    # Find active agent
    if 'active_agent_steps' not in context.metadata or not context.metadata['active_agent_steps']:
        # No active agent, this might be a direct manager tool call
        return False

    # Get the most recent active agent (in case of nested agents)
    active_agents = context.metadata['active_agent_steps']
    if not active_agents:
        return False

    # Add to the most recent agent's tools_used
    most_recent_agent = list(active_agents.keys())[-1]
    tool_info = {
        "name": tool_name,
        "args": tool_args,
        "result": str(tool_result),  # Don't truncate - frontend can handle expansion
        "duration": duration,
        "status": "success" if "❌" not in str(tool_result) and "error" not in str(tool_result).lower() else "error",
        "timestamp": datetime.now().isoformat()
    }

    active_agents[most_recent_agent]['tools_used'].append(tool_info)
    print(f"🔧 Added tool to {most_recent_agent}: {tool_name}")

    return True


def emit_tool_call_event(tool_name: str, params: Optional[Dict[str, Any]] = None, is_agent: bool = False) -> bool:
    """
    Emit a tool call event and save to current workflow steps for database persistence.

    IMPORTANT: If a tool is called within an agent context, it will be added to
    the agent's tools_used list instead of creating a separate step event.

    Args:
        tool_name: Name of the tool being called
        params: Tool parameters (will be truncated if too large)
        is_agent: Whether this is an agent call (not a regular tool)

    Returns:
        True if event was emitted, False if no context

    Example:
        emit_tool_call_event("read_project_file", {"file_id": "abc-123"})
        emit_tool_call_event("dev_agent", {"task": "..."}, is_agent=True)
    """
    # Check if this is a visualization tool
    is_visualization = _is_visualization_tool(tool_name)
    context = get_workflow_context()
    if not context:
        return False

    # If this is an agent call, use the new agent tracking
    if is_agent:
        task = params.get('task', '') if params else ''
        emit_agent_execution_start(tool_name, task)
        return True

    # If tool is called within an agent context, add to agent's tools_used instead of creating new step
    # This will be collected and shown when agent completes
    if 'active_agent_steps' in context.metadata and context.metadata['active_agent_steps']:
        # Tool is being called by an agent - don't create a separate step
        print(f"🔧 Tool {tool_name} called within agent context - will be collected")
        # Note: actual tool result will be added by add_tool_to_active_agent() later
        return False  # Don't create separate step event
    
    # Increment the shared step counter
    context.step_counter['count'] += 1
    step_number = context.step_counter['count']
    
    # Create event for WebSocket broadcast
    # Use different event type and icon for agents vs tools
    event_type = "agent_call" if is_agent else "tool_call"
    icon = "🤖" if is_agent else "🛠️"
    
    event = WorkflowEvent(
        workflow_id=context.workflow_id,
        event_type=event_type,
        timestamp=datetime.now(),
        step_number=step_number,
        title=f"{icon} {tool_name}",
        description=f"Executing {tool_name}",
        tool_name=tool_name,
        tool_params=params
    )
    
    # Add to LabOSService's current_workflow_steps for database saving
    try:
        from app.main import labos_service
        from app.services.workflows.workflow_service import WorkflowStep, WorkflowStepStatus
        from app.models.enums import WorkflowStepType
        
        # Create a WorkflowStep object for database saving
        # Use AGENT_EXECUTION type if this is an agent call
        step_type = WorkflowStepType.AGENT_EXECUTION if is_agent else WorkflowStepType.TOOL_EXECUTION
        
        # Add visualization metadata if this is a visualization tool
        step_metadata = {}
        if is_visualization and params:
            step_metadata = {
                "is_visualization": True,
                "chart_params": params
            }
        
        db_step = WorkflowStep(
            id=f"{context.workflow_id}_tool_{step_number}",
            type=step_type,
            title=f"🤖 {tool_name}" if is_agent else f"🛠️ {tool_name}",
            description=f"Executing {tool_name}",
            status=WorkflowStepStatus.COMPLETED,
            tool_name=tool_name if not is_agent else None,
            agent_name=tool_name if is_agent else None,
            tool_result=None, 
            step_metadata=step_metadata if step_metadata else None
        )

        # CRITICAL: Append to the workflow-specific steps list for database persistence
        if hasattr(labos_service, 'workflow_steps_by_id') and context.workflow_id in labos_service.workflow_steps_by_id:
            labos_service.workflow_steps_by_id[context.workflow_id].append(db_step)
            print(f"💾 Added tool step to database queue: {tool_name} (step #{step_number}) - Workflow {context.workflow_id} now has {len(labos_service.workflow_steps_by_id[context.workflow_id])} steps")
    except Exception as e:
        print(f"⚠️ Failed to add tool step to database queue: {e}")
    
    # Emit event for WebSocket broadcast
    workflow_logger = logging.getLogger('stella.workflow')
    workflow_logger.info(f"[{context.workflow_id}] Tool call: {tool_name} (step #{step_number})")
    print(f"📤 Emitting tool_call event for {tool_name} (step #{step_number})")
    workflow_event_queue.put(event)
    return True


# emit_artifact_event removed - not used in current implementation


def emit_observation_event(observation: str, tool_name: Optional[str] = None) -> bool:
    """
    Emit an observation event (typically after a tool executes).

    IMPORTANT: Only emit observations for:
    1. Visualizations (contains file_id and image reference)
    2. Errors (contains error message)
    3. Agent thoughts (tool_name == "agent_thought") - shows Agent's reasoning

    Regular tool observations are NOT emitted to reduce frontend noise.

    Args:
        observation: What was observed/returned
        tool_name: Which tool produced this observation

    Returns:
        True if event was emitted, False if no context or observation filtered

    Example:
        emit_observation_event("File contains 1024 bytes of data", tool_name="read_project_file")
    """
    context = get_workflow_context()
    if not context:
        print(f"⚠️ Cannot emit observation event: No workflow context available (tool: {tool_name})")
        return False

    # Filter: Only emit observations for visualizations, errors, or agent thoughts
    has_visualization = bool(_FILE_ID_PATTERN.search(observation)) or \
                       bool(_GENERATED_VIZ_PATTERN.search(observation)) or \
                       bool(_IMAGE_EXTENSION_PATTERN.search(observation))
    has_error = '❌' in observation or 'error' in observation.lower() or 'failed' in observation.lower()
    is_agent_thought = tool_name == "agent_thought"

    # Skip non-critical observations
    if not has_visualization and not has_error and not is_agent_thought:
        # Silently skip - don't spam the frontend with every tool result
        return False

    # Don't increment counter for observations - they are sub-steps
    # context.step_counter['count'] += 1  # Removed to avoid number gaps

    # Special handling for agent thoughts
    if tool_name == "agent_thought":
        title = "💭 Agent Reasoning"
    else:
        title = f"👁️ Observation"
        if tool_name:
            title += f" from {tool_name}"
    
    # Extract visualization metadata directly from observation if it contains image file
    # Support both new format: "Generated visualization: file.png (file_id: xxx)"
    # and old format: "Saved file: file.png (...) - ID: xxx"
    event_metadata = None

    # Try new format first
    new_format_match = _NEW_FORMAT_VIZ_PATTERN.search(observation)
    if new_format_match:
        filename = new_format_match.group(1)
        file_id = new_format_match.group(2)
        event_metadata = {
            'visualizations': [{
                "type": "image",
                "chart_type": "generated",
                "title": filename.replace('.png', '').replace('_', ' ').title(),
                "file_id": file_id,
                "filename": filename
            }]
        }
        print(f"📊 Including visualization in WebSocket event: {filename} (file_id: {file_id})")

        # Clean up the observation text to hide file_id from user
        observation = _FILE_ID_PATTERN.sub('', observation)
    else:
        # Try old format for backward compatibility
        old_format_match = _OLD_FORMAT_VIZ_PATTERN.search(observation)
        if old_format_match:
            filename = old_format_match.group(1)
            file_id = old_format_match.group(3)
            event_metadata = {
                'visualizations': [{
                    "type": "image",
                    "chart_type": "generated",
                    "title": filename.replace('.png', '').replace('_', ' ').title(),
                    "file_id": file_id,
                    "filename": filename
                }]
            }
            print(f"📊 Including visualization in WebSocket event: {filename} (file_id: {file_id})")
    
    event = WorkflowEvent(
        workflow_id=context.workflow_id,
        event_type="observation",
        timestamp=datetime.now(),
        step_number=context.step_counter['count'],  # Use current count without incrementing
        title=title,
        description=observation,
        tool_name=tool_name,
        step_metadata=event_metadata  # Include visualization metadata
    )
    
    # Use the same metadata for database storage
    observation_metadata = event_metadata
    
    try:
        from app.main import labos_service
        from app.services.workflows.workflow_service import WorkflowStep, WorkflowStepStatus
        from app.models.enums import WorkflowStepType
        
        # Create a WorkflowStep object for database saving
        db_step = WorkflowStep(
            id=f"{context.workflow_id}_obs_{context.step_counter['count']}",
            type=WorkflowStepType.SYNTHESIS,  # Use synthesis for observations
            title=title,
            description=observation,
            status=WorkflowStepStatus.COMPLETED,
            tool_name=tool_name,
            tool_result=observation,
            step_metadata=observation_metadata  # Include visualization metadata if present
        )

        # CRITICAL: Append to the workflow-specific steps list for database persistence
        if hasattr(labos_service, 'workflow_steps_by_id') and context.workflow_id in labos_service.workflow_steps_by_id:
            labos_service.workflow_steps_by_id[context.workflow_id].append(db_step)
            if observation_metadata:
                print(f"💾 Added observation with visualization to database queue: {tool_name} - Workflow {context.workflow_id} now has {len(labos_service.workflow_steps_by_id[context.workflow_id])} steps")
            elif tool_name == "agent_thought":
                print(f"💾 Added agent thought to database queue - Workflow {context.workflow_id} now has {len(labos_service.workflow_steps_by_id[context.workflow_id])} steps")
            else:
                print(f"💾 Added observation to database queue: {tool_name} - Workflow {context.workflow_id} now has {len(labos_service.workflow_steps_by_id[context.workflow_id])} steps")
    except Exception as e:
        print(f"⚠️ Failed to add observation to database queue: {e}")
    
    # Log observation event
    workflow_logger = logging.getLogger('stella.workflow')
    workflow_logger.debug(f"[{context.workflow_id}] Observation: {tool_name} - {observation[:100]}...")

    workflow_event_queue.put(event)

    # Confirmation log for agent thoughts
    if tool_name == "agent_thought":
        print(f"📤 Emitted agent thought to frontend: {observation[:100]}...")

    return True


# Global cancelled workflows set (shared across threads)
_cancelled_workflows = set()

# === Workflow Cancellation Functions ===

def mark_workflow_cancelled(workflow_id: str):
    """
    Mark the current workflow as cancelled.
    
    Uses both thread-local context (if available) and global state
    to ensure cancellation is detected across threads.
    
    Args:
        workflow_id: The workflow to cancel
    """
    # Add to global cancelled set (accessible from any thread)
    _cancelled_workflows.add(workflow_id)
    print(f"🛑 Added workflow {workflow_id} to global cancelled set")
    
    # Also mark in thread-local context if available
    context = get_workflow_context()
    if context and context.workflow_id == workflow_id:
        context.is_cancelled = True
        print(f"🛑 Marked workflow {workflow_id} as cancelled in thread context")


def is_workflow_cancelled() -> bool:
    """
    Check if the current workflow has been cancelled.
    
    Checks both thread-local context and global state.
    
    Returns:
        True if cancelled, False otherwise
    """
    # First check global state (works across threads)
    context = get_workflow_context()
    if context and context.workflow_id in _cancelled_workflows:
        return True
    
    # Then check thread-local state
    return context.is_cancelled if context else False


def check_cancellation():
    """
    Check if workflow is cancelled and raise exception if so.
    
    This should be called at the start of tool functions to enable
    early termination.
    
    Raises:
        WorkflowCancelledException: If the workflow has been cancelled
    
    Example:
        @tool
        def my_tool(param: str) -> str:
            check_cancellation()  # Check at start
            # ... rest of tool logic
    """
    if is_workflow_cancelled():
        context = get_workflow_context()
        workflow_id = context.workflow_id if context else "unknown"
        print(f"🛑 Workflow {workflow_id} cancellation detected in tool execution")
        raise WorkflowCancelledException(f"Workflow {workflow_id} was cancelled")


def get_workflow_id() -> Optional[str]:
    """
    Get the workflow ID for the current thread.
    
    Returns:
        Workflow ID if in context, None otherwise
    """
    context = get_workflow_context()
    return context.workflow_id if context else None


# ============================================
# Thinking Process Management (Thread-safe)
# ============================================

# Thread-local storage for thinking steps
_thinking_steps_storage = threading.local()


def add_thinking_step(message: str) -> bool:
    """
    Add a thinking step message to the current workflow context.
    
    This allows agents to record their thought process without relying on STDOUT.
    Messages are stored in thread-local storage and retrieved by the callback.
    
    Args:
        message: The thinking step message (e.g., "🧠 Analyzing DNA sequence...")
        
    Returns:
        True if added successfully, False if no workflow context
        
    Example:
        add_thinking_step("🧠 Thinking: Starting DNA sequence analysis...")
        add_thinking_step("📊 Analysis: Found A=20, T=21, G=17, C=12")
        add_thinking_step("🎨 Visualization: Creating bar chart...")
    """
    context = get_workflow_context()
    if not context:
        return False
    
    # Initialize storage if not exists
    if not hasattr(_thinking_steps_storage, 'steps'):
        _thinking_steps_storage.steps = []
    
    # Add message with workflow_id to ensure it's for the current workflow
    _thinking_steps_storage.steps.append({
        'workflow_id': context.workflow_id,
        'message': message,
        'timestamp': datetime.now().isoformat()
    })
    
    return True


def get_and_clear_thinking_steps(workflow_id: Optional[str] = None) -> list:
    """
    Get all thinking steps for the current workflow and clear them.
    
    This is called by the workflow callback at the end of each step to
    retrieve and emit all accumulated thinking messages.
    
    Args:
        workflow_id: Optional workflow ID to filter steps
        
    Returns:
        List of thinking step messages
    """
    if not hasattr(_thinking_steps_storage, 'steps'):
        return []
    
    steps = _thinking_steps_storage.steps
    messages = []
    
    # If workflow_id is provided, filter by it
    if workflow_id:
        messages = [s['message'] for s in steps if s['workflow_id'] == workflow_id]
    else:
        messages = [s['message'] for s in steps]
    
    # Clear the storage
    _thinking_steps_storage.steps = []
    
    return messages

