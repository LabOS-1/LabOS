"""
Project Export API - Endpoints for exporting project data
"""

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Dict, Any
import json
import uuid
from datetime import datetime

from app.core.infrastructure.database import get_db_session
from app.models import ChatProject, ChatMessage, WorkflowExecution
from app.api.v1.chat_projects import get_current_user_id

router = APIRouter()

@router.get("/export/project/{project_id}")
async def export_project_data(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    format: str = "json"
):
    """Export complete project data including messages and workflows"""
    try:
        # Get user ID from authentication
        user_id = await get_current_user_id(request)
        
        # Verify project ownership
        project_query = select(ChatProject).where(
            ChatProject.id == uuid.UUID(project_id),
            ChatProject.user_id == user_id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all messages for the project
        messages_query = (
            select(ChatMessage)
            .where(ChatMessage.project_id == uuid.UUID(project_id))
            .order_by(ChatMessage.created_at)
        )
        messages_result = await db.execute(messages_query)
        messages = messages_result.scalars().all()
        
        # Get all workflows with steps for the project
        workflows_query = (
            select(WorkflowExecution)
            .options(selectinload(WorkflowExecution.steps))
            .where(WorkflowExecution.project_id == uuid.UUID(project_id))
            .order_by(WorkflowExecution.started_at)
        )
        workflows_result = await db.execute(workflows_query)
        workflows = workflows_result.scalars().all()
        
        # Format export data
        export_data = {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "is_active": project.is_active
            },
            "messages": [
                {
                    "id": str(msg.id),
                    "role": msg.role.value,
                    "content": msg.content,
                    "metadata": msg.message_metadata,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                }
                for msg in messages
            ],
            "workflows": [
                {
                    "id": str(wf.id),
                    "workflow_id": wf.workflow_id,
                    "status": wf.status.value,
                    "started_at": wf.started_at.isoformat() if wf.started_at else None,
                    "completed_at": wf.completed_at.isoformat() if wf.completed_at else None,
                    "result": wf.result,
                    "steps": [
                        {
                            "step_index": step.step_index,
                            "type": step.type,
                            "title": step.title,
                            "description": step.description,
                            "status": step.status.value,
                            "tool_name": step.tool_name,
                            "tool_result": step.tool_result,
                            "started_at": step.started_at.isoformat() if step.started_at else None,
                            "completed_at": step.completed_at.isoformat() if step.completed_at else None
                        }
                        for step in sorted(wf.steps, key=lambda s: s.step_index)
                    ]
                }
                for wf in workflows
            ],
            "export_metadata": {
                "exported_at": datetime.now().isoformat(),
                "total_messages": len(messages),
                "total_workflows": len(workflows),
                "format": format
            }
        }
        
        if format.lower() == "json":
            # Return as downloadable JSON file
            filename = f"labos_project_{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            response = Response(
                content=json.dumps(export_data, indent=2, ensure_ascii=False),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
            return response
        else:
            # Return as API response
            return {
                "success": True,
                "data": export_data
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/export/project/{project_id}/chat-history")
async def export_chat_history(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Export only chat history for a project"""
    try:
        # Get user ID from authentication
        user_id = await get_current_user_id(request)
        
        # Verify project ownership
        project_query = select(ChatProject).where(
            ChatProject.id == uuid.UUID(project_id),
            ChatProject.user_id == user_id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all messages for the project
        messages_query = (
            select(ChatMessage)
            .where(ChatMessage.project_id == uuid.UUID(project_id))
            .order_by(ChatMessage.created_at)
        )
        messages_result = await db.execute(messages_query)
        messages = messages_result.scalars().all()
        
        # Format chat history
        chat_data = {
            "project_name": project.name,
            "exported_at": datetime.now().isoformat(),
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat() if msg.created_at else None
                }
                for msg in messages
            ]
        }
        
        filename = f"labos_chat_{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        response = Response(
            content=json.dumps(chat_data, indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        return response
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/export/project/{project_id}/workflows")
async def export_workflows(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Export only workflow data for a project"""
    try:
        # Get user ID from authentication
        user_id = await get_current_user_id(request)
        
        # Verify project ownership
        project_query = select(ChatProject).where(
            ChatProject.id == uuid.UUID(project_id),
            ChatProject.user_id == user_id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all workflows with steps
        workflows_query = (
            select(WorkflowExecution)
            .options(selectinload(WorkflowExecution.steps))
            .where(WorkflowExecution.project_id == uuid.UUID(project_id))
            .order_by(WorkflowExecution.started_at)
        )
        workflows_result = await db.execute(workflows_query)
        workflows = workflows_result.scalars().all()
        
        # Format workflow data
        workflow_data = {
            "project_name": project.name,
            "exported_at": datetime.now().isoformat(),
            "workflows": [
                {
                    "workflow_id": wf.workflow_id,
                    "status": wf.status.value,
                    "started_at": wf.started_at.isoformat() if wf.started_at else None,
                    "completed_at": wf.completed_at.isoformat() if wf.completed_at else None,
                    "result": wf.result,
                    "steps": [
                        {
                            "step_index": step.step_index,
                            "type": step.type,
                            "title": step.title,
                            "description": step.description,
                            "status": step.status.value,
                            "tool_name": step.tool_name,
                            "tool_result": step.tool_result,
                            "duration": None  # Could calculate from start/end times
                        }
                        for step in sorted(wf.steps, key=lambda s: s.step_index)
                    ]
                }
                for wf in workflows
            ]
        }
        
        filename = f"labos_workflows_{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        response = Response(
            content=json.dumps(workflow_data, indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        return response
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
