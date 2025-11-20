"""
LabOS Service - Simplified service for integrating with LabOS AI
Handles communication with the LabOS core system and provides API endpoints.

FILE STRUCTURE (985 lines):
==========================
1. Initialization               (Lines 1-100)
2. Message Processing           (Lines 105-292)
3. Core Workflow Execution      (Lines 293-593) ← LARGEST & MOST COMPLEX
4. Database Operations          (Lines 594-708)
5. System Status & Tools        (Lines 709-774)
6. Workflow Management          (Lines 775-820)
7. File & Project Management    (Lines 822-958)
8. Cleanup                      (Lines 959-985)

For detailed navigation, see: labos_service_docs.md
"""

import os
import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

# Import unified configuration
from app.config import PERFORMANCE_CONFIG, LabOS_CONFIG

# Import LabOS engine directly (no bridge needed)
try:
    from app.core import labos_engine
    print("✅ LabOS engine module imported successfully")
    LabOS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Failed to import LabOS engine: {e}")
    stella_engine = None
    LabOS_AVAILABLE = False

# Import workflow modules
from app.services.workflows.workflow_executor import WorkflowExecutor
from app.services.workflows.workflow_database import WorkflowDatabase
from app.services.workflows.workflow_file_manager import WorkflowFileManager

class LabOSService:
    """Simplified service class for managing LabOS AI integration"""

    def __init__(self):
        self.manager_agent = None
        self.initialized = False
        self.executor = ThreadPoolExecutor(max_workers=LabOS_CONFIG["max_parallel_workers"])
        # REMOVED: self.chat_history - This was causing memory leak and privacy issues
        # Chat history is now loaded per-request from database
        # REMOVED: self.current_executions - Never used, always empty
        # FIXED: Changed from single list to per-workflow dictionary for multi-user isolation
        self.workflow_steps_by_id: Dict[str, List] = {}  # Store workflow steps per workflow_id
        self.active_workflows: Dict[str, asyncio.Task] = {}  # Track active workflow tasks
        self.workflow_to_project: Dict[str, str] = {}  # CRITICAL: Map workflow_id to project_id for user isolation
        self.cancelled_workflows: set = set()  # Track cancelled workflow IDs (cleaned up in finally block)
        self.logger = logging.getLogger('stella.service')  # Service logger
        self.workflow_logger = logging.getLogger('stella.workflow')  # Workflow logger
        self.system_stats = {
            "uptime_start": time.time(),
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
        }

    async def initialize(self):
        """Initialize LabOS AI system directly"""
        try:
            if not LabOS_AVAILABLE:
                print("❌ LabOS engine not available")
                return

            # Initialize LabOS directly
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self.executor,
                self._initialize_stella_direct
            )

            if success:
                self.manager_agent = stella_engine.manager_agent
                self.initialized = True
                print("✅ LabOS AI initialized successfully")
                print(f"   Debug: manager_agent type = {type(self.manager_agent)}")
                print(f"   Debug: manager_agent is None = {self.manager_agent is None}")
            else:
                print("❌ LabOS AI initialization failed")

        except Exception as e:
            print(f"❌ Failed to initialize LabOS AI: {e}")
            import traceback
            traceback.print_exc()
            
    def _initialize_stella_direct(self):
        """Initialize LabOS system directly in thread"""
        try:
            print("🔧 Attempting to initialize LabOS system...")
            
            if not LabOS_AVAILABLE or stella_engine is None:
                print("❌ LabOS engine not available")
                return False
            
            success = stella_engine.initialize_stella(use_template=True, use_mem0=True)
            
            if success:
                print("✅ LabOS system initialized successfully")
                return True
            else:
                print("❌ LabOS system initialization returned False")
                return False
                
        except Exception as e:
            print(f"❌ Error in LabOS initialization: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def is_initialized(self) -> bool:
        """Check if LabOS is initialized"""
        return self.initialized and self.manager_agent is not None
        
    async def process_message_async(self, message: str, workflow_id: str, project_id: str = None, user_id: str = None, mode: str = "deep") -> None:
        """Process message asynchronously with WebSocket updates and optional project saving

        Args:
            mode: Execution mode - "fast" or "deep" (default: "deep")
        """
        # Initialize workflow-specific steps list for multi-user isolation
        self.workflow_steps_by_id[workflow_id] = []

        # CRITICAL: Store workflow to project mapping for user isolation in WebSocket broadcasts
        if project_id:
            self.workflow_to_project[workflow_id] = project_id

        # Log workflow start
        self.workflow_logger.info(f"Starting workflow {workflow_id} for project {project_id}")
        self.logger.info(f"Processing message async: {workflow_id}")
        
        # Check if this workflow was cancelled before starting
        if workflow_id in self.cancelled_workflows:
            self.workflow_logger.warning(f"Workflow {workflow_id} was cancelled before starting")
            print(f"⚠️ Workflow {workflow_id} was cancelled before starting")
            self.cancelled_workflows.discard(workflow_id)
            return
        
        try:
            # Send initial status via WebSocket
            try:
                from app.services.websocket_broadcast import websocket_broadcaster
                await websocket_broadcaster.broadcast({
                    "type": "chat_started",
                    "workflow_id": workflow_id,
                    "project_id": project_id,  # CRITICAL: Include project_id for user isolation
                    "message": "Started processing your request...",
                    "timestamp": datetime.now().isoformat()
                })
                print(f"📤 Sent chat_started for workflow: {workflow_id} (project: {project_id})")
            except Exception as ws_error:
                print(f"⚠️ Failed to send chat_started message: {ws_error}")
            
            # Process the message with user_id and project_id context
            mode_display = "FAST ⚡" if mode == "fast" else "DEEP 🧠"
            self.workflow_logger.info(f"[{workflow_id}] Starting message processing ({mode_display} mode)")
            response = await self.process_message(message, workflow_id, user_id=user_id, project_id=project_id, mode=mode)

            # ✅ CRITICAL: Give event queue a moment to process Complete step before sending chat_completed
            # The Complete step is emitted via workflow_event_queue in execute_workflow
            # We need to ensure it's been broadcast to WebSocket before sending chat_completed
            await asyncio.sleep(0.1)  # 100ms delay to ensure event queue is processed

            # ✅ Send chat_completed IMMEDIATELY after processing, before database save
            # This ensures users see the completion status without waiting for slow database operations
            try:
                from app.services.websocket_broadcast import websocket_broadcaster
                await websocket_broadcaster.broadcast({
                    "type": "chat_completed",
                    "workflow_id": workflow_id,
                    "project_id": project_id,
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "action": "project_updated" if project_id else None
                })
                self.workflow_logger.info(f"[{workflow_id}] Sent chat_completed WebSocket message")
                print(f"📤 Sent chat_completed for workflow: {workflow_id} (before database save)")
            except Exception as ws_error:
                self.workflow_logger.error(f"[{workflow_id}] Failed to send chat_completed: {ws_error}")
                print(f"⚠️ Failed to send chat_completed message: {ws_error}")

            # Save to project database if project_id is provided
            # This happens AFTER sending chat_completed so users don't wait for database operations
            if project_id:
                # First save the response and create WorkflowExecution
                execution_id = await WorkflowDatabase.save_response_to_project(project_id, response, workflow_id)
                print(f"📝 Created WorkflowExecution: {execution_id}")

                # Then save workflow steps that were collected during processing
                workflow_steps = self.workflow_steps_by_id.get(workflow_id, [])
                if workflow_steps:
                    print(f"💾 Saving {len(workflow_steps)} workflow steps to database...")
                    await WorkflowDatabase.save_workflow_steps_batch(
                        project_id=project_id,
                        workflow_id=workflow_id,
                        steps=workflow_steps
                    )
                    print(f"✅ Database save completed for workflow: {workflow_id}")
                else:
                    print(f"⚠️  No workflow steps to save for workflow {workflow_id}")
                
        except asyncio.CancelledError:
            self.workflow_logger.info(f"[{workflow_id}] Workflow was cancelled")
            print(f"🛑 Workflow {workflow_id} was cancelled")
            # Send cancellation message via WebSocket (but NOT chat_completed)
            try:
                from app.services.websocket_broadcast import websocket_broadcaster
                await websocket_broadcaster.broadcast({
                    "type": "workflow_cancelled",
                    "workflow_id": workflow_id,
                    "project_id": project_id,  # CRITICAL: Include project_id for user isolation
                    "message": "Workflow was cancelled due to project switch",
                    "timestamp": datetime.now().isoformat()
                })
                self.workflow_logger.info(f"[{workflow_id}] Sent workflow_cancelled WebSocket message")
                print(f"📤 Sent workflow_cancelled (no chat_completed) for workflow: {workflow_id} (project: {project_id})")
            except Exception as ws_error:
                self.workflow_logger.error(f"[{workflow_id}] Failed to send cancellation message: {ws_error}")
                print(f"⚠️ Failed to send cancellation message: {ws_error}")
            # Don't send chat_completed for cancelled workflows
            return  # Early return, skip the chat_completed logic
                
        except Exception as e:
            print(f"❌ Error in async message processing: {e}")
            import traceback
            traceback.print_exc()
            
            # Send error via WebSocket
            try:
                from app.services.websocket_broadcast import websocket_broadcaster
                await websocket_broadcaster.broadcast({
                    "type": "chat_error",
                    "workflow_id": workflow_id,
                    "project_id": project_id,  # CRITICAL: Include project_id for user isolation
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as ws_error:
                print(f"❌ Failed to send error via WebSocket: {ws_error}")
        
        finally:
            # Clean up from active workflows tracking
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]

            # Clean up workflow steps to prevent memory leak
            if workflow_id in self.workflow_steps_by_id:
                del self.workflow_steps_by_id[workflow_id]
                print(f"🧹 Cleaned up workflow steps for {workflow_id}")

            # Clean up workflow to project mapping
            if workflow_id in self.workflow_to_project:
                del self.workflow_to_project[workflow_id]
                print(f"🧹 Cleaned up workflow-to-project mapping for {workflow_id}")

            # Clean up cancelled workflows set to prevent memory leak
            if workflow_id in self.cancelled_workflows:
                self.cancelled_workflows.discard(workflow_id)
                print(f"🧹 Cleaned up cancelled workflow {workflow_id} from tracking set")

    async def process_message(self, message: str, workflow_id: str = None, user_id: str = None, project_id: str = None, mode: str = "deep") -> Dict:
        """Process a chat message with LabOS

        Args:
            mode: Execution mode - "fast" or "deep" (default: "deep")
        """
        from app.services.workflows import workflow_service, WorkflowStep, WorkflowStepStatus
        from app.models.enums import WorkflowStepType, StepStatus

        self.system_stats["total_requests"] += 1
        start_time = time.time()

        # If no workflow_id is provided, generate one
        if not workflow_id:
            workflow_id = f"msg_{int(time.time() * 1000)}"

        try:
            # Create workflow
            workflow_service.create_workflow(workflow_id)

            # Note: Chat history is stored in database per project
            # No longer using self.chat_history to avoid memory leak

            if not self.initialized or self.manager_agent is None:
                # LabOS not initialized - return clear error message
                error_msg = "❌ LabOS AI is not initialized. Please check API keys and configuration."
                print(f"❌ LabOS not initialized for workflow_id: {workflow_id}")
                print(f"   Debug: initialized={self.initialized}, manager_agent={self.manager_agent is not None}")
                print(f"   LabOS_AVAILABLE={LabOS_AVAILABLE}")
                
                # Add error step to workflow
                await workflow_service.add_step(
                    workflow_id,
                    WorkflowStep(
                        id=f"{workflow_id}_error",
                        type=WorkflowStepType.SYNTHESIS,
                        title="LabOS Initialization Error",
                        description=error_msg,
                        status=StepStatus.FAILED
                    )
                )
                
                raise RuntimeError(error_msg)
            else:
                # Use LabOS processing with context
                mode_display = "FAST ⚡" if mode == "fast" else "DEEP 🧠"
                print(f"🚀 Using LabOS processing ({mode_display} mode) for workflow_id: {workflow_id}, user_id: {user_id}, project_id: {project_id}")
                response_content = await self._process_with_stella(workflow_id, message, user_id=user_id, project_id=project_id, mode=mode)

            execution_time = time.time() - start_time

            # Create response record
            assistant_message = {
                "id": f"msg_{int(time.time() * 1000) + 1}",
                "type": "assistant",
                "content": response_content,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "execution_time": execution_time,
                    "agent_id": "stella_manager",
                    "using_real_stella": self.initialized,
                    "workflow_id": workflow_id
                }
            }

            self.system_stats["successful_requests"] += 1

            return assistant_message

        except Exception as e:
            self.system_stats["failed_requests"] += 1
            print(f"❌ Error processing message: {e}")
            import traceback
            traceback.print_exc()

            error_message = {
                "id": f"msg_{int(time.time() * 1000)}",
                "type": "system",
                "content": f"Sorry, I encountered an error while processing your request: {str(e)}\n\nPlease check the server logs for more details.",
                "timestamp": datetime.now().isoformat(),
            }
            return error_message

    async def _process_with_stella(self, workflow_id: str, message: str, user_id: str = None, project_id: str = None, mode: str = "deep") -> str:
        """Process message with LabOS using WorkflowExecutor

        Args:
            mode: Execution mode - "fast" or "deep" (default: "deep")
        """
        # Get project output directory
        project_output_dir = WorkflowFileManager.get_project_output_dir(project_id)

        # Create workflow executor
        # No longer needs manager_agent - creates dedicated instance per workflow
        executor = WorkflowExecutor(
            cancelled_workflows=self.cancelled_workflows
        )

        # CRITICAL: Share the steps list with executor for this specific workflow
        # This allows tools (via emit_tool_call_event) to append to the same list
        # Using workflow_steps_by_id[workflow_id] ensures multi-user isolation
        self.workflow_steps_by_id[workflow_id] = executor.current_workflow_steps
        print(f"🔗 Linked workflow {workflow_id} steps to executor (id: {id(self.workflow_steps_by_id[workflow_id])})")

        # Register task for cancellation
        self.active_workflows[workflow_id] = None  # Will be updated by executor

        try:
            # Execute workflow
            response_content = await executor.execute_workflow(
                workflow_id=workflow_id,
                message=message,
                user_id=user_id,
                project_id=project_id,
                project_output_dir=project_output_dir,
                mode=mode
            )

            # Steps are already in self.workflow_steps_by_id[workflow_id] (shared reference)
            print(f"📊 Workflow {workflow_id} complete. Collected {len(self.workflow_steps_by_id[workflow_id])} steps total")

            # Auto-register any files created by agent
            await WorkflowFileManager.auto_register_workflow_files(
                workflow_id=workflow_id,
                workflow_tmp_dir=project_output_dir,
                user_id=user_id,
                project_id=project_id
            )

            return response_content

        finally:
            # Cleanup will be handled by executor
            pass
        


    def get_system_status(self) -> Dict:
        """Get system status information"""
        return {
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "initialized": self.initialized,
            "manager_agent_available": self.manager_agent is not None,
            "system": {
                "total_requests": self.system_stats["total_requests"],
                "successful_requests": self.system_stats["successful_requests"],
                "failed_requests": self.system_stats["failed_requests"],
                "uptime_seconds": int(time.time() - self.system_stats["uptime_start"]),
                "active_workflows": len(self.active_workflows),
                "cancelled_workflows_count": len(self.cancelled_workflows),
            }
        }

    # === API endpoint methods ===

    async def get_agents(self) -> Dict[str, Any]:
        """Get agents status (compatibility method)"""
        return {
            "stella_manager": {
                "id": "stella_manager",
                "name": "LabOS Manager",
                "type": "manager",
                "status": "ready" if self.initialized else "idle",
                "description": "Main coordinator agent",
                "capabilities": [
                    "Multi-agent coordination",
                    "Dynamic tool loading",
                    "Scientific research analysis"
                ],
                "last_activity": "2024-01-01T00:00:00Z"
            }
        }
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel an active workflow"""
        try:
            # Mark as cancelled
            self.cancelled_workflows.add(workflow_id)
            print(f"🛑 Marked workflow {workflow_id} as cancelled")
            
            # Mark in thread-local storage for tools to check
            from app.services.workflows import mark_workflow_cancelled
            mark_workflow_cancelled(workflow_id)
            print(f"🛑 Marked workflow {workflow_id} as cancelled in thread context")
            
            # If workflow task is running, cancel it
            cancelled = False
            
            if workflow_id in self.active_workflows:
                task = self.active_workflows[workflow_id]
                task.cancel()
                print(f"🛑 Cancelled active asyncio task for workflow {workflow_id}")
                cancelled = True

            if cancelled:
                # Get project_id from mapping for user isolation
                project_id = self.workflow_to_project.get(workflow_id)

                # Send cancellation message via WebSocket
                try:
                    from app.services.websocket_broadcast import websocket_broadcaster
                    await websocket_broadcaster.broadcast({
                        "type": "workflow_cancelled",
                        "workflow_id": workflow_id,
                        "project_id": project_id,  # CRITICAL: Include project_id for user isolation
                        "message": "Workflow cancelled by user",
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"📤 Sent workflow_cancelled for workflow: {workflow_id} (project: {project_id})")
                except Exception as e:
                    print(f"⚠️ Failed to send cancellation broadcast: {e}")
                
                return True
            else:
                print(f"⚠️ Workflow {workflow_id} not found in active workflows or processes")
                return False
                
        except Exception as e:
            print(f"❌ Error cancelling workflow {workflow_id}: {e}")
            return False
    
    def get_active_workflows(self) -> List[str]:
        """Get list of active workflow IDs"""
        return list(self.active_workflows.keys())
    
    async def cleanup(self):
        """Cleanup resources when shutting down"""
        try:
            # Cancel all active workflows
            for workflow_id in list(self.active_workflows.keys()):
                await self.cancel_workflow(workflow_id)
            
            if self.executor:
                self.executor.shutdown(wait=True)
                print("✅ Thread pool executor shut down")

            # Clear cancelled workflows set
            self.cancelled_workflows.clear()
            print("✅ Cleared cancelled workflows tracking")

            # Reset initialization state
            self.initialized = False
            self.manager_agent = None
            
            print("✅ LabOSService cleanup completed")

        except Exception as e:
            print(f"❌ Error during LabOSService cleanup: {e}")
