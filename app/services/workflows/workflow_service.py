"""
Workflow Service - Manage real-time status and events for AI workflows
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
# Import from unified enums instead of defining locally
from app.models.enums import WorkflowStepType, StepStatus

# Create aliases for backward compatibility
WorkflowStepStatus = StepStatus

@dataclass
class WorkflowStep:
    id: str
    type: WorkflowStepType
    title: str
    description: Optional[str] = None
    status: StepStatus = StepStatus.PENDING
    timestamp: str = ""
    duration: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    
    # Legacy fields
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None
    progress: Optional[int] = None
    
    # New Agent-aware fields  
    agent_name: Optional[str] = None
    agent_task: Optional[str] = None
    execution_result: Optional[str] = None
    execution_duration: Optional[float] = None
    step_metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

class WorkflowService:
    """Service for managing AI workflow status"""
    
    def __init__(self):
        self.active_workflows: Dict[str, List[WorkflowStep]] = {}
        self.workflow_progress: Dict[str, int] = {}
        self.step_start_times: Dict[str, float] = {}
    
    def create_workflow(self, workflow_id: str) -> None:
        """Create new workflow"""
        self.active_workflows[workflow_id] = []
        self.workflow_progress[workflow_id] = 0
        print(f"🔄 Created workflow: {workflow_id}")

    async def add_step(self, workflow_id: str, step: WorkflowStep, step_number: int = None) -> None:
        """Add workflow step with explicit or automatic numbering"""
        if workflow_id not in self.active_workflows:
            self.create_workflow(workflow_id)
        
        # Use provided step_number or auto-assign based on current workflow length
        if step_number is None:
            step_number = len(self.active_workflows[workflow_id]) + 1
        
        self.active_workflows[workflow_id].append(step)
        self.step_start_times[step.id] = time.time()

        # WebSocket broadcast is handled by workflow_event_queue + WorkflowEventListener
        # No need to duplicate broadcast here - emit_tool_call_event/emit_observation_event
        # already handles real-time WebSocket updates through the event queue

        print(f"➕ Added step #{step_number} to {workflow_id}: {step.title}")
    
    async def update_step(self, workflow_id: str, step_id: str, **updates) -> None:
        """Update workflow step"""
        if workflow_id not in self.active_workflows:
            return
        
        for step in self.active_workflows[workflow_id]:
            if step.id == step_id:
                # Update step properties
                for key, value in updates.items():
                    if hasattr(step, key):
                        setattr(step, key, value)
                
                # If step completed, calculate duration
                if step.status == WorkflowStepStatus.COMPLETED and step_id in self.step_start_times:
                    step.duration = (time.time() - self.step_start_times[step_id]) * 1000  # milliseconds
                    del self.step_start_times[step_id]

                print(f"🔄 Updated step {step_id}: {step.status.value}")
                break
    
    async def update_progress(self, workflow_id: str, progress: int) -> None:
        """Update overall workflow progress"""
        if workflow_id not in self.workflow_progress:
            return
        
        self.workflow_progress[workflow_id] = progress

        # Send WebSocket broadcast
        from app.services.websocket_broadcast import websocket_broadcaster
        current_step = len(self.active_workflows.get(workflow_id, []))
        await websocket_broadcaster.send_workflow_progress(
            workflow_id, 
            float(progress), 
            current_step, 
            max(current_step + 1, 3),  # Estimate total steps
            progress < 100
        )
        
        print(f"📊 Updated progress for {workflow_id}: {progress}%")
        print(f"📡 Broadcasted workflow progress via WebSocket")
    
    async def complete_workflow(self, workflow_id: str) -> None:
        """Complete workflow"""
        if workflow_id not in self.active_workflows:
            return

        self.workflow_progress[workflow_id] = 100

        print(f"✅ Completed workflow: {workflow_id}")

        # Auto-cleanup after 5 minutes to prevent memory leak
        # This gives frontend time to fetch final state from WebSocket/API
        async def delayed_cleanup():
            await asyncio.sleep(300)  # 5 minutes
            self.cleanup_workflow(workflow_id)
            print(f"🧹 Auto-cleaned up workflow: {workflow_id} (5min after completion)")

        # Schedule cleanup in background (don't await)
        asyncio.create_task(delayed_cleanup())

    def get_workflow_steps(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get workflow steps"""
        if workflow_id not in self.active_workflows:
            return []
        
        return [asdict(step) for step in self.active_workflows[workflow_id]]
    
    def get_workflow_progress(self, workflow_id: str) -> int:
        """Get workflow progress"""
        return self.workflow_progress.get(workflow_id, 0)
    
    def cleanup_workflow(self, workflow_id: str) -> None:
        """Clean up workflow data"""
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
        if workflow_id in self.workflow_progress:
            del self.workflow_progress[workflow_id]

        # Clean up step timers
        step_ids_to_remove = [step_id for step_id in self.step_start_times.keys() 
                             if step_id.startswith(workflow_id)]
        for step_id in step_ids_to_remove:
            del self.step_start_times[step_id]
        
        print(f"🧹 Cleaned up workflow: {workflow_id}")

# Global workflow service instance
workflow_service = WorkflowService()
