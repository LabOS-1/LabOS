"""
Workflow Management Module

This package contains all workflow-related functionality:
- workflow_service: Core workflow state management
- workflow_context: Thread-local workflow context
- workflow_events: Event queue for real-time updates
- workflow_event_listener: WebSocket event broadcasting
- workflow_callback: Agent execution callbacks
- workflow_executor: Core workflow execution logic
- workflow_database: Database operations for workflows
- workflow_file_manager: File management for workflows
"""

from .workflow_service import workflow_service, WorkflowService, WorkflowStep, WorkflowStepStatus
from .workflow_context import (
    WorkflowContext,
    set_workflow_context,
    get_workflow_context,
    clear_workflow_context,
    emit_tool_call_event,
    emit_observation_event,
    emit_visualization_event,
    mark_workflow_cancelled,
    is_workflow_cancelled,
    check_cancellation,
    WorkflowCancelledException,
)
from .workflow_events import workflow_event_queue, WorkflowEvent
from .workflow_callback import create_agent_with_simple_callbacks, agent_aware_callback
from .workflow_executor import WorkflowExecutor
from .workflow_database import WorkflowDatabase
from .workflow_file_manager import WorkflowFileManager

__all__ = [
    # Service
    'workflow_service',
    'WorkflowService',
    'WorkflowStep',
    'WorkflowStepStatus',

    # Context
    'WorkflowContext',
    'set_workflow_context',
    'get_workflow_context',
    'clear_workflow_context',
    'emit_tool_call_event',
    'emit_observation_event',
    'emit_visualization_event',
    'mark_workflow_cancelled',
    'is_workflow_cancelled',
    'check_cancellation',
    'WorkflowCancelledException',

    # Events
    'workflow_event_queue',
    'WorkflowEvent',

    # Callbacks
    'create_agent_with_simple_callbacks',
    'agent_aware_callback',

    # New modules
    'WorkflowExecutor',
    'WorkflowDatabase',
    'WorkflowFileManager',
]
