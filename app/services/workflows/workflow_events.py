"""
Workflow Event System
Provides thread-safe event queue for real-time workflow updates with rich media support.

This module enables:
- Real-time step-by-step progress visibility
- Rich media artifacts (images, code, data, tables)
- Thread-safe communication between Agent threads and WebSocket broadcasts
"""

from dataclasses import dataclass, asdict
from typing import Literal, Optional, Dict, Any, List
from datetime import datetime
import queue
import threading


@dataclass
class WorkflowEvent:
    """
    Workflow event with rich content support.
    
    This class represents a single event in an Agent's execution workflow,
    which can include text updates, tool calls, or rich media artifacts.
    
    Examples:
        Text notification:
            WorkflowEvent(
                workflow_id="workflow_123",
                event_type="step",
                step_number=2,
                title="Analyzing query",
                description="Processing user request..."
            )
        
        Code artifact:
            WorkflowEvent(
                workflow_id="workflow_123",
                event_type="artifact",
                step_number=3,
                title="Generated Python code",
                artifact_type="code",
                artifact_data="def analyze():\\n    pass",
                artifact_format="python"
            )
        
        Image artifact:
            WorkflowEvent(
                workflow_id="workflow_123",
                event_type="artifact",
                step_number=4,
                title="Created visualization",
                artifact_type="image",
                artifact_data="base64_encoded_image_data",
                artifact_format="png"
            )
    """
    
    # === Event Metadata ===
    workflow_id: str
    """Unique identifier for the workflow this event belongs to"""
    
    event_type: Literal["step", "artifact", "tool_call", "agent_call", "observation"]
    """Type of event:
    - step: General progress step
    - artifact: Rich media content (code, image, data)
    - tool_call: Tool execution started
    - agent_call: Agent execution started
    - observation: Tool execution result
    """
    
    timestamp: datetime
    """When this event was created"""
    
    step_number: int
    """Sequential step number in the workflow (1, 2, 3, ...)"""
    
    # === Display Information ===
    title: str
    """Short title for display (e.g., "Analyzing query", "Generated code")"""
    
    description: Optional[str] = None
    """Longer description with details"""
    
    # === Rich Media Artifacts ===
    artifact_type: Optional[Literal["image", "code", "data", "file", "table"]] = None
    """Type of artifact:
    - image: PNG/JPG image (base64 encoded)
    - code: Source code snippet
    - data: JSON data
    - file: File content
    - table: Tabular data
    """
    
    artifact_data: Optional[str] = None
    """
    Artifact content:
    - For images: base64 encoded string
    - For code: raw source code string
    - For data: JSON string
    - For tables: JSON array of objects
    """
    
    artifact_format: Optional[str] = None
    """
    Format specification:
    - For images: "png", "jpg", "svg"
    - For code: "python", "javascript", "bash", etc.
    - For data: "json", "csv"
    """
    
    artifact_metadata: Optional[Dict[str, Any]] = None
    """
    Additional metadata about the artifact:
    - For images: {"width": 1000, "height": 600, "dpi": 100}
    - For code: {"lines": 25, "language": "python"}
    - For tables: {"rows": 100, "columns": 5}
    """
    
    # === Tool Execution Information ===
    tool_name: Optional[str] = None
    """Name of the tool being called/executed"""
    
    tool_params: Optional[Dict[str, Any]] = None
    """Parameters passed to the tool"""
    
    tool_result: Optional[str] = None
    """Result returned by the tool (truncated if too long)"""
    
    step_metadata: Optional[Dict[str, Any]] = None
    """Extended metadata for visualizations, code blocks, etc."""
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for WebSocket transmission.
        
        Returns:
            Dictionary with all event data, ready for JSON serialization
        """
        # Map event_type to step_type for frontend
        step_type_mapping = {
            "tool_call": "tool_execution",
            "agent_call": "agent_execution",
            "observation": "synthesis",
            "step": "thinking",
            "artifact": "synthesis"
        }
        
        base_dict = {
            "type": "workflow_step",  # WebSocket message type
            "step_type": step_type_mapping.get(self.event_type, "thinking"),  # Frontend step type
            "workflow_id": self.workflow_id,
            "step_number": self.step_number,
            "title": self.title,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
        }
        
        # Add artifact information if present
        if self.artifact_type:
            base_dict["artifact"] = {
                "type": self.artifact_type,
                "data": self.artifact_data,
                "format": self.artifact_format,
                "metadata": self.artifact_metadata or {}
            }
        
        # Add tool information if present
        if self.tool_name:
            base_dict["tool"] = {
                "name": self.tool_name,
                "params": self.tool_params,
                "result": self.tool_result
            }

        # Add step_metadata if present (for visualizations, etc.)
        if self.step_metadata:
            base_dict["step_metadata"] = self.step_metadata
            print(f"📡 WorkflowEvent.to_dict: Including step_metadata with {len(self.step_metadata.get('visualizations', []))} visualizations")

        return base_dict
    
    def __repr__(self) -> str:
        """Human-readable representation"""
        parts = [
            f"WorkflowEvent(#{self.step_number}",
            f"type={self.event_type}",
            f"title='{self.title}'"
        ]
        
        if self.artifact_type:
            parts.append(f"artifact={self.artifact_type}")
        
        if self.tool_name:
            parts.append(f"tool={self.tool_name}")
        
        return " ".join(parts) + ")"


class WorkflowEventQueue:
    """
    Thread-safe event queue for workflow updates.
    
    This class manages a global queue of workflow events, allowing:
    - Agent threads to put events (thread-safe)
    - Async event listener to get events (non-blocking)
    - Workflow lifecycle management (register/unregister)
    
    Usage:
        # In Agent thread (synchronous)
        event = WorkflowEvent(...)
        workflow_event_queue.put(event)
        
        # In async listener
        event = workflow_event_queue.get_nowait()
        if event:
            await broadcast_to_websocket(event)
    """
    
    def __init__(self, maxsize: int = 1000):
        """
        Initialize event queue.
        
        Args:
            maxsize: Maximum queue size (default 1000 events)
                    Prevents memory issues with long-running workflows
        """
        # Thread-safe queue (queue.Queue is thread-safe by design)
        self._queue = queue.Queue(maxsize=maxsize)
        
        # Track active workflows
        self._active_workflows: Dict[str, bool] = {}
        self._lock = threading.Lock()
        
        # Statistics
        self._stats = {
            "total_events": 0,
            "events_dropped": 0,
            "active_workflows_count": 0
        }
    
    def put(self, event: WorkflowEvent, block: bool = False, timeout: Optional[float] = None):
        """
        Put event in queue (thread-safe, called from Agent thread).
        
        Args:
            event: WorkflowEvent to add
            block: If True, block until space available (default: False)
            timeout: Timeout in seconds if blocking (default: None)
        
        Raises:
            queue.Full: If queue is full and block=False
        """
        try:
            self._queue.put(event, block=block, timeout=timeout)
            self._stats["total_events"] += 1
        except queue.Full:
            self._stats["events_dropped"] += 1
            print(f"⚠️ Event queue full! Dropped event: {event.title}")
            if not block:
                raise
    
    def get_nowait(self) -> Optional[WorkflowEvent]:
        """
        Get event without blocking (for async listener).
        
        Returns:
            WorkflowEvent if available, None if queue is empty
        """
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None
    
    def register_workflow(self, workflow_id: str):
        """
        Register a workflow as active.
        
        Args:
            workflow_id: Unique workflow identifier
        """
        with self._lock:
            self._active_workflows[workflow_id] = True
            self._stats["active_workflows_count"] = len(self._active_workflows)
            print(f"📝 Registered workflow: {workflow_id}")
    
    def unregister_workflow(self, workflow_id: str):
        """
        Unregister workflow (workflow completed or errored).
        
        Args:
            workflow_id: Unique workflow identifier
        """
        with self._lock:
            self._active_workflows.pop(workflow_id, None)
            self._stats["active_workflows_count"] = len(self._active_workflows)
            print(f"📝 Unregistered workflow: {workflow_id}")
    
    def is_active(self, workflow_id: str) -> bool:
        """
        Check if workflow is active.
        
        Args:
            workflow_id: Workflow to check
        
        Returns:
            True if workflow is active, False otherwise
        """
        with self._lock:
            return self._active_workflows.get(workflow_id, False)
    
    def get_active_workflows(self) -> List[str]:
        """
        Get list of active workflow IDs.
        
        Returns:
            List of workflow IDs currently active
        """
        with self._lock:
            return list(self._active_workflows.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with queue stats
        """
        with self._lock:
            return {
                **self._stats,
                "queue_size": self._queue.qsize(),
                "active_workflows": list(self._active_workflows.keys())
            }
    
    def clear_workflow_events(self, workflow_id: str):
        """
        Clear all events for a specific workflow (cleanup after completion).
        
        Note: This doesn't actually remove from queue (queue.Queue doesn't support),
        but marks the workflow as inactive so listener stops processing its events.
        
        Args:
            workflow_id: Workflow to clear
        """
        self.unregister_workflow(workflow_id)


# === Global Singleton Instance ===
workflow_event_queue = WorkflowEventQueue(maxsize=1000)
"""
Global event queue instance.

Import this in:
- Tools (to send events): from app.services.workflows.workflow_events import workflow_event_queue
- Service layer (to listen): from app.services.workflows.workflow_events import workflow_event_queue
"""

