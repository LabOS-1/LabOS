"""
Chat Projects API - Project CRUD and Message/Workflow Reading
Note: Message sending is handled by V2 API (/api/v2/chat/projects)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.infrastructure.database import get_db_session
from app.core.infrastructure.cloud_logging import get_logger

# Initialize logger
logger = get_logger(__name__)
from app.models import (
    ChatProject, ChatMessage, WorkflowExecution,
    ChatProjectResponse, ChatMessageResponse
)
from pydantic import BaseModel

router = APIRouter()

# Request models
class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None

class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

async def get_current_user_id(request: Request) -> str:
    """Get current user ID from authentication context"""
    try:
        # Try Authorization header first (for cross-domain)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            try:
                # Try base64 decode first
                import base64
                import json
                decoded_data = base64.b64decode(token).decode()
                user_data = json.loads(decoded_data)
                user_id = user_data.get('sub') or user_data.get('id')
                if user_id:
                    return user_id
            except:
                try:
                    # Fallback to direct JSON
                    user_data = json.loads(token)
                    user_id = user_data.get('sub') or user_data.get('id')
                    if user_id:
                        return user_id
                except:
                    pass
        
        # Try token query parameter (for URL-based auth)
        token_param = request.query_params.get('token')
        if token_param:
            try:
                import base64
                import json
                decoded_data = base64.b64decode(token_param).decode()
                user_data = json.loads(decoded_data)
                user_id = user_data.get('sub') or user_data.get('id')
                if user_id:
                    return user_id
            except:
                pass
        
        # Fallback to cookie (for same-domain)
        auth_cookie = request.cookies.get('auth-user')
        if auth_cookie:
            try:
                import json
                user_data = json.loads(auth_cookie)
                user_id = user_data.get('sub') or user_data.get('id')
                if user_id:
                    return user_id
            except:
                pass
        
        # No valid authentication found
        raise HTTPException(status_code=401, detail="Authentication required")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication")

@router.get("/projects", response_model=List[ChatProjectResponse])
async def get_projects(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """Get user's chat projects with message counts"""
    # Get user ID from authentication
    user_id = await get_current_user_id(request)
    
    # Query projects with message counts
    query = (
        select(
            ChatProject,
            func.count(ChatMessage.id.distinct()).label('message_count')
        )
        .select_from(ChatProject)
        .outerjoin(ChatMessage, ChatProject.id == ChatMessage.project_id)
        .where(ChatProject.user_id == user_id)
        .where(ChatProject.is_active == True)
        .group_by(ChatProject.id)
        .order_by(desc(ChatProject.updated_at))
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(query)
    projects_with_counts = result.all()
    
    # Convert to response format
    projects = []
    for project, message_count in projects_with_counts:
        project_dict = {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "is_active": project.is_active,
            "message_count": message_count or 0
        }
        projects.append(ChatProjectResponse(**project_dict))
    
    return projects

@router.post("/projects", response_model=ChatProjectResponse)
async def create_project(
    http_request: Request,
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat project"""
    # Get user ID from authentication
    user_id = await get_current_user_id(http_request)
    
    project = ChatProject(
        user_id=user_id,
        name=request.name,
        description=request.description
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return ChatProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        is_active=project.is_active,
        message_count=0
    )

@router.put("/projects/{project_id}", response_model=ChatProjectResponse)
async def update_project(
    http_request: Request,
    project_id: str,
    request: UpdateProjectRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a project"""
    # Get user ID from authentication
    user_id = await get_current_user_id(http_request)
    
    query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user_id
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update fields
    if request.name is not None:
        project.name = request.name
    if request.description is not None:
        project.description = request.description
    
    project.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(project)
    
    # Get current message count
    count_query = select(func.count(ChatMessage.id)).where(ChatMessage.project_id == uuid.UUID(project_id))
    count_result = await db.execute(count_query)
    message_count = count_result.scalar() or 0
    
    return ChatProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        is_active=project.is_active,
        message_count=message_count
    )

@router.delete("/projects/{project_id}")
async def delete_project(
    http_request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a project and all its messages/workflows"""
    # Get user ID from authentication
    user_id = await get_current_user_id(http_request)

    query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user_id
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete sandbox files for this project
    try:
        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()
        sandbox.delete_project_sandbox(user_id, project_id)
        logger.info(f"Deleted sandbox for project: {project_id}")
    except Exception as e:
        logger.warning(f"Failed to delete sandbox for project {project_id}: {e}")

    # Delete project (cascade will handle messages and workflows)
    await db.delete(project)
    await db.commit()

    return {"success": True, "message": "Project deleted successfully"}

@router.get("/projects/{project_id}", response_model=ChatProjectResponse)
async def get_project(
    http_request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a single chat project by ID with message count"""
    # Get user ID from authentication
    user_id = await get_current_user_id(http_request)

    # Query project with message count
    query = (
        select(
            ChatProject,
            func.count(ChatMessage.id.distinct()).label('message_count')
        )
        .select_from(ChatProject)
        .outerjoin(ChatMessage, ChatProject.id == ChatMessage.project_id)
        .where(ChatProject.id == uuid.UUID(project_id))
        .where(ChatProject.user_id == user_id)
        .where(ChatProject.is_active == True)
        .group_by(ChatProject.id)
    )

    result = await db.execute(query)
    project_with_count = result.first()

    if not project_with_count:
        raise HTTPException(status_code=404, detail="Project not found")

    project, message_count = project_with_count

    # Convert to response format
    project_dict = {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "is_active": project.is_active,
        "message_count": message_count or 0
    }

    return ChatProjectResponse(**project_dict)

@router.get("/projects/{project_id}/messages", response_model=List[ChatMessageResponse])
async def get_project_messages(
    http_request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(100, le=10000),
    offset: int = Query(0, ge=0)
):
    """Get messages for a project"""
    # Get user ID from authentication
    user_id = await get_current_user_id(http_request)
    
    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user_id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get messages
    query = (
        select(ChatMessage)
        .where(ChatMessage.project_id == uuid.UUID(project_id))
        .order_by(ChatMessage.created_at)
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    return [
        ChatMessageResponse(
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            message_metadata=msg.message_metadata,
            created_at=msg.created_at
        )
        for msg in messages
    ]

@router.get("/projects/{project_id}/workflows")
async def get_project_workflows(
    http_request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """Get workflow executions for a project with their steps"""
    # Get user ID from authentication
    user_id = await get_current_user_id(http_request)
    
    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user_id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get workflow executions with their steps
    from sqlalchemy.orm import selectinload
    query = (
        select(WorkflowExecution)
        .options(selectinload(WorkflowExecution.steps))
        .where(WorkflowExecution.project_id == uuid.UUID(project_id))
        .order_by(desc(WorkflowExecution.started_at))
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    workflows = result.scalars().all()
    
    # Format response
    workflow_list = []
    for wf in workflows:
        # Format steps
        steps = []
        for step in sorted(wf.steps, key=lambda s: s.step_index):
            steps.append({
                "id": str(step.id),
                "step_index": step.step_index,
                "type": step.type,
                "title": step.title,
                "description": step.description,
                "status": step.status.value,
                "tool_name": step.tool_name,
                "tool_result": step.tool_result,
                "started_at": step.started_at,
                "completed_at": step.completed_at,
                "step_metadata": step.step_metadata  # ✅ Include visualization metadata
            })
        
        workflow_list.append({
            "id": str(wf.id),
            "workflow_id": wf.workflow_id,
            "message_id": str(wf.message_id) if wf.message_id else None,
            "status": wf.status.value,
            "started_at": wf.started_at,
            "completed_at": wf.completed_at,
            "result": wf.result,
            "steps": steps,
            "step_count": len(steps)
        })
    
    return {
        "success": True,
        "data": {
            "workflows": workflow_list,
            "total": len(workflow_list),
            "offset": offset,
            "limit": limit
        }
    }


@router.post("/projects/{project_id}/workflows/{workflow_id}/cancel")
async def cancel_project_workflow(
    http_request: Request,
    project_id: str,
    workflow_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Cancel an active workflow for a project"""
    try:
        # Get user ID from authentication
        user_id = await get_current_user_id(http_request)

        # Verify project ownership
        project_query = select(ChatProject).where(
            ChatProject.id == uuid.UUID(project_id),
            ChatProject.user_id == user_id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Mark workflow as cancelled using the workflow context system
        from app.services.workflows import mark_workflow_cancelled
        mark_workflow_cancelled(workflow_id)

        logger.info(f"Workflow cancelled", extra={
            "workflow_id": workflow_id,
            "project_id": project_id,
            "user_id": user_id
        })

        return {
            "success": True,
            "message": f"Workflow {workflow_id} cancellation requested"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

