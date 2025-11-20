"""
Workflow Executor
Handles core workflow execution logic including agent execution, event broadcasting,
and workflow lifecycle management.

This module extracts the complex workflow execution logic from labos_service.py
to improve maintainability and testability.
"""

import os
import asyncio
import json
from typing import Optional, Dict, Any
from datetime import datetime

from .workflow_service import workflow_service, WorkflowStep, WorkflowStepStatus
from .workflow_events import workflow_event_queue, WorkflowEvent
from .workflow_event_listener import start_workflow_listener, stop_workflow_listener
from .workflow_context import (
    set_workflow_context,
    clear_workflow_context,
    get_workflow_context,
    WorkflowCancelledException
)
from app.models.enums import WorkflowStepType, StepStatus


class WorkflowExecutor:
    """
    Handles workflow execution with LabOS agent.

    Responsibilities:
    - Per-workflow agent instance creation (for thread safety and user isolation)
    - Agent execution coordination
    - Event listener management
    - Workflow step tracking
    - Cancellation handling
    - Timeout management
    """

    def __init__(self, cancelled_workflows: set):
        """
        Initialize workflow executor.

        Args:
            cancelled_workflows: Set of cancelled workflow IDs (shared with service)
        """
        self.cancelled_workflows = cancelled_workflows
        self.current_workflow_steps = []  # Steps collected during execution

    def _create_workflow_agent(self, mode='deep'):
        """
        Create a new manager agent instance for this workflow.

        This ensures complete isolation between concurrent workflows:
        - Each workflow gets its own agent instance
        - No shared state between users
        - Thread-safe by design (no locks needed)

        Args:
            mode: Execution mode - 'deep' (full workflow) or 'fast' (quick responses). Default: 'deep'

        Returns:
            New manager agent instance with all tools and configuration
        """
        from app.core import labos_engine
        from app.core.agents import create_manager_agent, load_agent_prompts

        # Get global resources from stella_engine
        models = {
            'claude_model': stella_engine.claude_model,
            'gpt_model': stella_engine.gpt_model,
            'manager_model': stella_engine.manager_model
        }

        # Use the same tools and managed agents as the global instance
        manager_tools = stella_engine.manager_tool_management

        # Create managed agents (dev, critic, tool_creation)
        # These are also created fresh to ensure complete isolation
        from app.core.agents import create_dev_agent, create_critic_agent, create_tool_creation_agent
        from app.core.tool_manager import save_tool_to_database
        from app.tools.core import save_agent_file
        from smolagents import WebSearchTool
        from app.tools.predefined import run_shell_command, visit_webpage

        # Load agent prompts
        agent_prompts = load_agent_prompts()

        # Create tool creation agent
        tool_creation_tools = [
            save_tool_to_database,
            save_agent_file,
            WebSearchTool(),
            visit_webpage,
            stella_engine.base_tools[2],  # search_github_repositories
            stella_engine.base_tools[3],  # search_github_code
            stella_engine.base_tools[4],  # get_github_repository_info
            stella_engine.base_tools[5],  # check_gpu_status
            stella_engine.base_tools[6],  # create_requirements_file
            stella_engine.base_tools[7],  # monitor_training_logs
        ]

        tool_creation_agent = create_tool_creation_agent(
            model=models['gpt_model'],
            tools=tool_creation_tools,
            agent_prompts=agent_prompts
        )

        # Create dev agent
        all_dev_tools = stella_engine.base_tools + stella_engine.mcp_tools
        dev_agent = create_dev_agent(
            model=models['claude_model'],
            tools=all_dev_tools,
            agent_prompts=agent_prompts
        )

        # Create critic agent
        critic_tools = [
            WebSearchTool(),
            visit_webpage,
            run_shell_command,
        ]

        critic_agent = create_critic_agent(
            model=models['manager_model'],
            tools=critic_tools,
            agent_prompts=agent_prompts
        )

        # Create manager agent based on mode
        if mode == 'fast':
            # Fast Mode: No tools, no managed agents - just LLM knowledge
            manager_agent = create_manager_agent(
                model=models['manager_model'],
                tools=[],  # Empty tool list for Fast Mode
                managed_agents=[],  # No sub-agents in Fast Mode
                use_template=stella_engine.use_templates,
                agent_prompts=agent_prompts,
                mode=mode
            )
            print(f"⚡ Created FAST MODE manager agent with {len(manager_agent.tools)} tools (pure LLM)")
        else:
            # Deep Mode: Full tools and managed agents
            manager_agent = create_manager_agent(
                model=models['manager_model'],
                tools=manager_tools,
                managed_agents=[dev_agent, critic_agent, tool_creation_agent],
                use_template=stella_engine.use_templates,
                agent_prompts=agent_prompts,
                mode=mode
            )
            print(f"✅ Created DEEP MODE manager agent with {len(manager_agent.tools)} tools")

        return manager_agent

    async def execute_workflow(
        self,
        workflow_id: str,
        message: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        project_output_dir: Optional[str] = None,
        mode: str = "deep"
    ) -> str:
        """
        Execute a workflow with LabOS agent.

        Args:
            workflow_id: Unique workflow identifier
            message: User message to process
            user_id: Optional user ID for context
            project_id: Optional project ID for context
            project_output_dir: Optional project output directory
            mode: Execution mode - "fast" (quick LLM response) or "deep" (full workflow). Default: "deep"

        Returns:
            Response content from agent

        Raises:
            asyncio.CancelledError: If workflow is cancelled
            Exception: If execution fails
        """
        # Clear steps list (don't reassign to preserve reference!)
        # This is critical for labos_service to collect all steps
        self.current_workflow_steps.clear()
        print(f"🧹 Cleared workflow steps list (keeping reference, id: {id(self.current_workflow_steps)})")

        # Event listener task
        listener_task = None

        try:
            # Register workflow in event queue
            workflow_event_queue.register_workflow(workflow_id)

            # Start event listener (runs in background) with project_id for user isolation
            listener_task = await start_workflow_listener(workflow_id, project_id=project_id)
            print(f"📡 Event listener started for workflow: {workflow_id} (project: {project_id})")

            # Step counter for workflow (shared with Agent thread via context)
            step_counter = {'count': 0}  # Start at 0

            # Add initial step
            initial_step = WorkflowStep(
                id=f"{workflow_id}_start",
                type=WorkflowStepType.THINKING,
                title="🚀 Start LabOS Processing",
                description=f"Starting to process query: {message}",
                status=WorkflowStepStatus.RUNNING
            )
            # Increment counter and add initial step with explicit numbering
            step_counter['count'] += 1
            await workflow_service.add_step(workflow_id, initial_step, step_counter['count'])
            self.current_workflow_steps.append(initial_step)  # Store for database saving

            # Also emit via workflow_event_queue for real-time WebSocket broadcast
            workflow_event_queue.put(WorkflowEvent(
                workflow_id=workflow_id,
                event_type="step",
                timestamp=datetime.now(),
                step_number=step_counter['count'],
                title="🚀 Start LabOS Processing",
                description=f"Starting to process query: {message}"
            ))

            # Prepare metadata for workflow context
            metadata = {}
            if user_id:
                metadata['user_id'] = user_id
            if project_id:
                metadata['project_id'] = project_id
            if project_output_dir:
                metadata['workflow_tmp_dir'] = project_output_dir
                print(f"📁 Using project output dir: {project_output_dir}")

            # Create workflow context file for subprocesses to read
            if project_output_dir:
                context_file_path = os.path.join(project_output_dir, '.workflow_context.json')
                try:
                    with open(context_file_path, 'w') as f:
                        json.dump({
                            'project_id': str(project_id),
                            'user_id': str(user_id),
                            'workflow_id': workflow_id
                        }, f)
                    print(f"📝 Created workflow context file: {context_file_path}")
                except Exception as e:
                    print(f"⚠️ Failed to create workflow context file: {e}")

            # Check if workflow was cancelled before starting Agent
            if workflow_id in self.cancelled_workflows:
                print(f"🛑 Workflow {workflow_id} was cancelled before Agent execution")
                raise asyncio.CancelledError("Workflow was cancelled before execution")

            # Create dedicated agent instance for this workflow
            # CRITICAL: Each workflow gets its own agent instance to prevent state mixing
            mode_emoji = "⚡" if mode == "fast" else "🧠"
            print(f"🏗️  Creating {mode.upper()} MODE {mode_emoji} agent instance for workflow: {workflow_id}")
            workflow_agent = self._create_workflow_agent(mode=mode)
            print(f"✅ {mode.upper()} MODE agent created for workflow: {workflow_id}")

            # Load conversation history from database BEFORE running agent (in async context)
            # Pass current message to exclude it from history (it was just saved to DB)
            conversation_history = await self._load_conversation_history(project_id, current_message=message)

            # Build full message with history
            if conversation_history:
                history_context = "\n\n".join([
                    f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                    for msg in conversation_history
                ])
                full_message = f"Previous conversation:\n{history_context}\n\nCurrent message:\n{message}"
                print(f"💬 Including conversation context ({len(conversation_history)} messages)")
            else:
                full_message = message

            # Execute agent with context
            response_content = await self._execute_agent_with_context(
                workflow_id=workflow_id,
                workflow_agent=workflow_agent,
                full_message=full_message,
                step_counter=step_counter,
                metadata=metadata,
                project_output_dir=project_output_dir
            )

            # Handle edge cases where agent returns non-string (e.g., ellipsis object)
            if response_content is None or response_content is ... or not isinstance(response_content, str):
                response_content = "LabOS processing completed, but no specific content returned."
            elif len(response_content.strip()) == 0:
                response_content = "LabOS processing completed, but no specific content returned."

            # Add final step
            final_step = WorkflowStep(
                id=f"{workflow_id}_complete",
                type=WorkflowStepType.SYNTHESIS,
                title="✅ LabOS Processing Complete",
                description=f"Generated response of {len(response_content)} characters",
                status=WorkflowStepStatus.COMPLETED
            )
            # Get current step count from context (may have been incremented by tools)
            current_context = get_workflow_context()
            if current_context and current_context.workflow_id == workflow_id:
                # Use the context's counter + 1 for the final step
                final_step_number = current_context.step_counter['count'] + 1
                current_context.step_counter['count'] = final_step_number  # Update context too
            else:
                step_counter['count'] += 1
                final_step_number = step_counter['count']

            await workflow_service.add_step(workflow_id, final_step, final_step_number)
            self.current_workflow_steps.append(final_step)  # Store for database saving

            # Also emit via workflow_event_queue for real-time WebSocket broadcast
            workflow_event_queue.put(WorkflowEvent(
                workflow_id=workflow_id,
                event_type="step",
                timestamp=datetime.now(),
                step_number=final_step_number,
                title="✅ LabOS Processing Complete",
                description=f"Generated response of {len(response_content)} characters"
            ))

            await workflow_service.complete_workflow(workflow_id)
            return response_content

        except asyncio.CancelledError:
            print(f"🛑 Workflow {workflow_id} task was cancelled")
            # Add cancellation step
            cancel_step = WorkflowStep(
                id=f"{workflow_id}_cancelled",
                type=WorkflowStepType.SYNTHESIS,
                title="🛑 Workflow Cancelled",
                description="Workflow was cancelled by user request",
                status=StepStatus.FAILED
            )
            await workflow_service.add_step(workflow_id, cancel_step)
            # Don't return content, let it propagate as CancelledError
            raise

        except Exception as e:
            print(f"❌ Error in LabOS processing: {e}")
            import traceback
            traceback.print_exc()

            # Add error step
            error_step = WorkflowStep(
                id=f"{workflow_id}_error",
                type=WorkflowStepType.SYNTHESIS,
                title="❌ Processing Error",
                description=f"Error: {str(e)}",
                status=StepStatus.FAILED
            )
            await workflow_service.add_step(workflow_id, error_step)

            return f"❌ Error processing with LabOS: {str(e)}"

        finally:
            # Give time for any remaining events to be processed
            await asyncio.sleep(0.5)

            # Clean up environment variable
            if 'WORKFLOW_TMP_DIR' in os.environ:
                del os.environ['WORKFLOW_TMP_DIR']
                print(f"🧹 Cleared WORKFLOW_TMP_DIR environment variable")

            # Clean up context after all processing is done
            clear_workflow_context()

            # Clean up: Stop listener and unregister workflow
            if listener_task:
                print(f"🛑 Stopping event listener for workflow: {workflow_id}")
                await stop_workflow_listener(listener_task, grace_period=1.0)

            workflow_event_queue.unregister_workflow(workflow_id)
            print(f"✅ Workflow cleanup complete: {workflow_id}")

    async def _load_conversation_history(self, project_id: Optional[str], current_message: Optional[str] = None) -> list:
        """
        Load conversation history from database.

        Args:
            project_id: Project ID to load history for
            current_message: Current message being processed (to exclude from history)

        Returns:
            List of conversation messages
        """
        conversation_history = []
        if not project_id:
            return conversation_history

        try:
            from app.models.database.chat import ChatMessage
            from app.core.database import AsyncSessionLocal
            from sqlalchemy import select
            import uuid

            async with AsyncSessionLocal() as session:
                # Convert project_id to UUID if it's a string
                if isinstance(project_id, str):
                    project_uuid = uuid.UUID(project_id)
                    print(f"🔍 Loading history for project (string->UUID): {project_id}")
                else:
                    project_uuid = project_id
                    print(f"🔍 Loading history for project (UUID): {project_uuid}")

                # Get last 11 messages (in case we need to exclude current)
                query = select(ChatMessage).where(
                    ChatMessage.project_id == project_uuid
                ).order_by(ChatMessage.created_at.desc()).limit(11)
                result = await session.execute(query)
                messages = list(result.scalars().all())
                messages = list(reversed(messages))  # Chronological order

                # Format for agent, excluding current message if it matches
                for msg in messages:
                    # Skip if this is the current message being processed
                    if current_message and msg.content == current_message and msg.role.value == "user":
                        print(f"⏭️  Skipping current message from history: {msg.content[:50]}...")
                        continue

                    conversation_history.append({
                        "role": "user" if msg.role.value == "user" else "assistant",
                        "content": msg.content
                    })

                # Limit to 10 messages after filtering
                conversation_history = conversation_history[-10:]

            print(f"📚 Loaded {len(conversation_history)} messages from conversation history for project {project_id}")
            if conversation_history:
                # Print first and last message for debugging
                print(f"   First: [{conversation_history[0]['role']}] {conversation_history[0]['content'][:50]}...")
                print(f"   Last: [{conversation_history[-1]['role']}] {conversation_history[-1]['content'][:50]}...")
        except Exception as hist_error:
            print(f"⚠️ Failed to load conversation history: {hist_error}")
            import traceback
            traceback.print_exc()

        return conversation_history

    async def _execute_agent_with_context(
        self,
        workflow_id: str,
        workflow_agent,
        full_message: str,
        step_counter: Dict[str, int],
        metadata: Dict[str, Any],
        project_output_dir: Optional[str]
    ) -> str:
        """
        Execute agent with workflow context in thread executor.

        Args:
            workflow_id: Workflow identifier
            workflow_agent: Dedicated agent instance for this workflow
            full_message: Message with conversation history
            step_counter: Step counter dict
            metadata: Workflow metadata
            project_output_dir: Project output directory

        Returns:
            Agent response content

        Raises:
            asyncio.CancelledError: If cancelled
            asyncio.TimeoutError: If timeout
        """
        def run_agent_with_context():
            """Wrapper to set workflow context before Agent execution"""
            try:
                # Set environment variable for project output dir (for python_interpreter tool)
                if project_output_dir:
                    os.environ['WORKFLOW_TMP_DIR'] = project_output_dir
                    print(f"🔧 Set WORKFLOW_TMP_DIR={project_output_dir}")

                # Check cancellation at the start
                if workflow_id in self.cancelled_workflows:
                    print(f"🛑 Workflow {workflow_id} cancelled, skipping Agent execution")
                    raise asyncio.CancelledError("Workflow was cancelled during setup")

                # Set context for this thread with metadata
                set_workflow_context(workflow_id, step_counter, metadata)

                # Run agent with periodic cancellation checks
                print(f"🚀 Starting Agent execution for workflow: {workflow_id}")

                try:
                    # Start Agent execution with full message
                    # CRITICAL: Using dedicated agent instance - no lock needed!
                    # Each workflow has its own agent, ensuring complete isolation
                    # reset=True ensures agent doesn't carry over any state
                    print(f"🎯 Executing with dedicated agent instance for workflow: {workflow_id}")
                    result = workflow_agent.run(full_message, reset=True)
                    print(f"✅ Agent execution completed for workflow: {workflow_id}")

                    # Check if cancelled after Agent completes
                    if workflow_id in self.cancelled_workflows:
                        print(f"🛑 Workflow {workflow_id} was cancelled during execution")
                        raise asyncio.CancelledError("Workflow was cancelled during execution")

                    return result
                except WorkflowCancelledException as e:
                    print(f"🛑 Workflow {workflow_id} cancelled via exception: {e}")
                    raise asyncio.CancelledError(f"Workflow cancelled via callback: {e}")
                except Exception as e:
                    # Check if this is due to cancellation
                    if workflow_id in self.cancelled_workflows:
                        print(f"🛑 Workflow {workflow_id} cancelled during Agent execution (exception caught)")
                        raise asyncio.CancelledError("Workflow was cancelled during Agent execution")
                    # Otherwise, re-raise the exception
                    raise
            finally:
                # Context will be cleared in the main finally block
                pass

        loop = asyncio.get_event_loop()

        # Create a task so we can cancel it
        executor_task = loop.run_in_executor(None, run_agent_with_context)

        try:
            # Use asyncio.wait_for with timeout to allow cancellation
            # 10 minutes timeout for complex workflows
            response_content = await asyncio.wait_for(executor_task, timeout=600)
            return response_content
        except asyncio.CancelledError:
            print(f"🛑 Agent execution task was cancelled for workflow: {workflow_id}")
            raise
        except asyncio.TimeoutError:
            print(f"⏱️ Agent execution timed out after 10 minutes for workflow: {workflow_id}")
            executor_task.cancel()

            # Send timeout notification to frontend
            try:
                from app.services.websocket_broadcast import websocket_broadcaster
                await websocket_broadcaster.broadcast({
                    "type": "chat_error",
                    "workflow_id": workflow_id,
                    "error": "Workflow timed out after 10 minutes. The task was too complex.",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Failed to send timeout notification: {e}")

            raise asyncio.CancelledError("Workflow timed out")

    def get_collected_steps(self) -> list:
        """
        Get workflow steps collected during execution.

        Returns:
            List of WorkflowStep objects
        """
        return self.current_workflow_steps
