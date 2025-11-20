"""
Workflow Event Listener
Listens to the event queue and broadcasts events to WebSocket clients.

This module provides a clean separation between:
- Event generation (in Agent threads)
- Event distribution (via WebSocket)
"""

import asyncio
from typing import Optional
from datetime import datetime

from .workflow_events import workflow_event_queue, WorkflowEvent
from app.services.websocket_broadcast import websocket_broadcaster


class WorkflowEventListener:
    """
    Async listener that monitors the event queue and broadcasts to WebSocket.
    
    Usage:
        listener = WorkflowEventListener(workflow_id)
        task = asyncio.create_task(listener.start())
        # ... Agent executes ...
        listener.stop()
        await task
    """
    
    def __init__(self, workflow_id: str, project_id: str = None, poll_interval: float = 0.1):
        """
        Initialize event listener for a specific workflow.

        Args:
            workflow_id: Workflow to listen for
            project_id: Project ID for user isolation (optional)
            poll_interval: How often to check queue (seconds, default 0.1)
        """
        self.workflow_id = workflow_id
        self.project_id = project_id  # CRITICAL: Store project_id for user isolation
        self.poll_interval = poll_interval
        self._is_running = False
        self._stop_event = asyncio.Event()

        # Statistics
        self.events_processed = 0
        self.events_broadcasted = 0
        self.events_failed = 0
    
    async def start(self):
        """
        Start listening to the event queue.
        
        This runs in a loop until stop() is called.
        Should be run as an asyncio task.
        """
        self._is_running = True
        self._stop_event.clear()
        
        print(f"📡 Event listener started for workflow: {self.workflow_id}")
        
        try:
            while not self._stop_event.is_set():
                # Check if workflow is still active
                if not workflow_event_queue.is_active(self.workflow_id):
                    print(f"📡 Workflow inactive, stopping listener: {self.workflow_id}")
                    break
                
                # Get event from queue (non-blocking)
                event = workflow_event_queue.get_nowait()
                
                if event and event.workflow_id == self.workflow_id:
                    await self._process_event(event)
                
                # Small delay to avoid busy waiting
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.poll_interval
                    )
                except asyncio.TimeoutError:
                    # Timeout is expected, continue loop
                    pass
        
        except asyncio.CancelledError:
            print(f"📡 Event listener cancelled for workflow: {self.workflow_id}")
        
        except Exception as e:
            print(f"❌ Error in event listener for {self.workflow_id}: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self._is_running = False
            print(f"📡 Event listener stopped for workflow: {self.workflow_id}")
            print(f"   Stats: {self.events_processed} processed, "
                  f"{self.events_broadcasted} broadcasted, "
                  f"{self.events_failed} failed")
    
    async def _process_event(self, event: WorkflowEvent):
        """
        Process a single event: convert and broadcast.
        
        Args:
            event: WorkflowEvent to process
        """
        self.events_processed += 1
        
        try:
            # Convert event to WebSocket message format
            message = event.to_dict()
            
            # Broadcast via WebSocket with project_id for user isolation
            await websocket_broadcaster.send_workflow_step(
                self.workflow_id,
                message,
                project_id=self.project_id
            )
            
            self.events_broadcasted += 1
            
            # Log for debugging (can be removed in production)
            print(f"📤 Broadcasted event #{event.step_number}: {event.title}")
            
            # If it's an artifact, log the type
            if event.artifact_type:
                artifact_size = len(event.artifact_data) if event.artifact_data else 0
                print(f"   └─ Artifact: {event.artifact_type} ({artifact_size} bytes)")
        
        except Exception as e:
            self.events_failed += 1
            print(f"❌ Failed to broadcast event: {e}")
            print(f"   Event: {event}")
    
    def stop(self):
        """
        Signal the listener to stop.
        
        Call this when the Agent completes or errors.
        The listener will finish processing remaining events and exit.
        """
        self._stop_event.set()
        print(f"🛑 Stop signal sent to listener: {self.workflow_id}")
    
    def is_running(self) -> bool:
        """Check if listener is currently running"""
        return self._is_running


async def start_workflow_listener(workflow_id: str, project_id: str = None) -> asyncio.Task:
    """
    Convenience function to start a workflow event listener.

    Args:
        workflow_id: Workflow to listen for
        project_id: Project ID for user isolation (optional)

    Returns:
        asyncio.Task that can be awaited or cancelled

    Example:
        listener_task = await start_workflow_listener(workflow_id, project_id)
        # ... Agent executes ...
        listener_task.cancel()
        await listener_task  # Wait for cleanup
    """
    listener = WorkflowEventListener(workflow_id, project_id=project_id)
    task = asyncio.create_task(listener.start())
    
    # Store listener reference on task for later access
    task.listener = listener
    
    return task


async def stop_workflow_listener(task: asyncio.Task, grace_period: float = 0.5):
    """
    Stop a workflow listener task gracefully.
    
    Args:
        task: The task returned by start_workflow_listener()
        grace_period: Time to wait for remaining events (seconds)
    
    Example:
        task = await start_workflow_listener(workflow_id)
        # ... Agent executes ...
        await stop_workflow_listener(task)
    """
    if not task or task.done():
        return
    
    # Signal stop
    if hasattr(task, 'listener'):
        task.listener.stop()
    
    # Give it time to process remaining events
    await asyncio.sleep(grace_period)
    
    # Cancel if still running
    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

