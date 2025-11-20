"""
Workflow Database Operations
Handles all database persistence for workflows, including workflow steps,
executions, and chat messages.

This module extracts database operations from labos_service.py to provide
a clean interface for workflow persistence.
"""

from typing import Dict, Optional
from datetime import datetime
import uuid

from app.core.database import AsyncSessionLocal
from app.models import (
    WorkflowExecution,
    WorkflowStep as DBWorkflowStep,
    ChatMessage,
    MessageRole,
    StepStatus
)
from sqlalchemy import select


class WorkflowDatabase:
    """
    Handles database operations for workflows.

    Responsibilities:
    - Save workflow steps to database
    - Save workflow execution records
    - Save chat messages
    """

    @staticmethod
    async def save_workflow_step(
        project_id: str,
        workflow_id: str,
        step,
        step_index: int
    ) -> bool:
        """
        Save individual workflow step to database.

        Args:
            project_id: Project identifier
            workflow_id: Workflow identifier
            step: WorkflowStep object to save
            step_index: Sequential step number (1, 2, 3, ...)

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            async with AsyncSessionLocal() as db:
                # Find the workflow execution
                query = select(WorkflowExecution).where(
                    WorkflowExecution.project_id == uuid.UUID(project_id),
                    WorkflowExecution.workflow_id == workflow_id
                )
                result = await db.execute(query)
                workflow_execution = result.scalar_one_or_none()

                if not workflow_execution:
                    print(f"⚠️ No workflow execution found for {workflow_id}")
                    return False

                # Extract step information
                step_type = getattr(step, 'type', 'unknown')
                step_title = getattr(step, 'title', 'Untitled Step')
                step_description = getattr(step, 'description', '')
                step_status = getattr(step, 'status', 'completed')
                step_tool_name = getattr(step, 'tool_name', None)
                step_tool_result = getattr(step, 'tool_result', None)

                # Extract agent-aware fields
                step_agent_name = getattr(step, 'agent_name', None)
                step_agent_task = getattr(step, 'agent_task', None)
                step_metadata = getattr(step, 'step_metadata', None)

                # Convert enum values to strings
                if hasattr(step_type, 'value'):
                    step_type = step_type.value
                else:
                    step_type = str(step_type).split('.')[-1].lower() if '.' in str(step_type) else str(step_type)

                if hasattr(step_status, 'value'):
                    step_status = step_status.value
                else:
                    step_status = str(step_status).split('.')[-1].lower() if '.' in str(step_status) else str(step_status)

                if step_tool_result and not isinstance(step_tool_result, str):
                    step_tool_result = str(step_tool_result)

                # Create database workflow step
                workflow_step = DBWorkflowStep(
                    execution_id=workflow_execution.id,
                    step_index=step_index,
                    type=step_type,
                    title=step_title,
                    description=step_description,
                    status=StepStatus.COMPLETED if step_status == 'completed' else StepStatus.FAILED,
                    tool_name=step_tool_name,
                    tool_result=step_tool_result,
                    agent_name=step_agent_name,
                    agent_task=step_agent_task,
                    step_metadata=step_metadata,
                    started_at=datetime.now(),
                    completed_at=datetime.now()
                )
                db.add(workflow_step)
                await db.commit()

                print(f"✅ Saved workflow step {step_index} to database: {step_title}")
                return True

        except Exception as e:
            print(f"❌ Error saving workflow step to database: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    async def save_response_to_project(
        project_id: str,
        response: Dict,
        workflow_id: str
    ) -> Optional[str]:
        """
        Save AI response and workflow execution to project database.

        Args:
            project_id: Project identifier
            response: Response dictionary with content and metadata
            workflow_id: Workflow identifier

        Returns:
            Workflow execution ID if successful, None otherwise
        """
        try:
            async with AsyncSessionLocal() as db:
                # Create assistant message
                assistant_message = ChatMessage(
                    project_id=uuid.UUID(project_id),
                    role=MessageRole.ASSISTANT,
                    content=response.get("content", "No response content"),
                    message_metadata=response.get("metadata", {})
                )

                db.add(assistant_message)
                await db.commit()
                await db.refresh(assistant_message)

                # Create workflow execution record
                workflow_execution = WorkflowExecution(
                    project_id=uuid.UUID(project_id),
                    message_id=assistant_message.id,
                    workflow_id=workflow_id,
                    status="COMPLETED",
                    started_at=datetime.now(),
                    completed_at=datetime.now(),
                    result=response
                )

                db.add(workflow_execution)
                await db.commit()
                await db.refresh(workflow_execution)

                print(f"✅ Saved AI response and workflow to project {project_id}")
                return str(workflow_execution.id)

        except Exception as e:
            print(f"❌ Error saving response to project: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    async def save_workflow_steps_batch(
        project_id: str,
        workflow_id: str,
        steps: list
    ) -> int:
        """
        Save multiple workflow steps to database in batch.

        Args:
            project_id: Project identifier
            workflow_id: Workflow identifier
            steps: List of WorkflowStep objects

        Returns:
            Number of steps successfully saved
        """
        saved_count = 0
        for i, step in enumerate(steps):
            success = await WorkflowDatabase.save_workflow_step(
                project_id=project_id,
                workflow_id=workflow_id,
                step=step,
                step_index=i + 1  # Sequential numbering (1, 2, 3, ...)
            )
            if success:
                saved_count += 1

        if saved_count > 0:
            print(f"✅ Saved {saved_count}/{len(steps)} workflow steps to database")

        return saved_count
