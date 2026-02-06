"""
Chat Projects API - Project and Session CRUD, Message/Workflow Reading
Note: Message sending is handled by V2 API (/api/v2/chat/projects)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.infrastructure.database import get_db_session
from app.core.infrastructure.cloud_logging import get_logger
from app.api.utils.auth import get_current_user_id, get_or_create_user
from app.models.enums import UserStatus

logger = get_logger(__name__)
from app.models.database import ChatProject, ChatSession, ChatMessage, WorkflowExecution, User
from app.models.schemas import ChatProjectResponse, ChatSessionResponse, ChatSessionCreate, ChatMessageResponse


def require_approved(user: User) -> None:
    """Check if user is approved. Raises 403 if not."""
    if user.status != UserStatus.APPROVED:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Your account is not approved (status: {user.status.value})"
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


class UpdateSessionRequest(BaseModel):
    name: Optional[str] = None


# ============================================================================
# Project Endpoints
# ============================================================================

@router.get("/projects", response_model=List[ChatProjectResponse])
async def get_projects(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """Get user's chat projects with session counts"""
    auth0_id = await get_current_user_id(request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)
    require_approved(user)

    # Query projects with session counts
    query = (
        select(
            ChatProject,
            func.count(ChatSession.id.distinct()).label('session_count')
        )
        .select_from(ChatProject)
        .outerjoin(ChatSession, ChatProject.id == ChatSession.project_id)
        .where(ChatProject.user_id == user.id)
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
    for project, session_count in projects_with_counts:
        project_dict = {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "is_active": project.is_active,
            "session_count": session_count or 0,
            "sessions": []
        }
        projects.append(ChatProjectResponse(**project_dict))

    return projects


@router.post("/projects", response_model=ChatProjectResponse)
async def create_project(
    http_request: Request,
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat project (without auto-creating a session)"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    project = ChatProject(
        user_id=user.id,
        name=request.name,
        description=request.description
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Return project without auto-creating a session
    # User will create sessions manually via "New Chat" button
    return ChatProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        is_active=project.is_active,
        session_count=0,
        sessions=[]
    )


@router.put("/projects/{project_id}", response_model=ChatProjectResponse)
async def update_project(
    http_request: Request,
    project_id: str,
    request: UpdateProjectRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a project"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user.id
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

    # Get session count
    count_query = select(func.count(ChatSession.id)).where(ChatSession.project_id == uuid.UUID(project_id))
    count_result = await db.execute(count_query)
    session_count = count_result.scalar() or 0

    return ChatProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        is_active=project.is_active,
        session_count=session_count,
        sessions=[]
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    http_request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a project and all its sessions/messages/workflows"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user.id
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete sandbox files for this project
    # Use str(user.id) to match how sandboxes are created (database UUID, not auth0_id)
    try:
        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()
        user_id_str = str(user.id)
        sandbox.delete_project_sandbox(user_id_str, project_id)
        logger.info(f"Deleted sandbox for project: {project_id} (user: {user_id_str})")
    except Exception as e:
        logger.warning(f"Failed to delete sandbox for project {project_id}: {e}")

    # Delete project (cascade will handle sessions, messages and workflows)
    await db.delete(project)
    await db.commit()

    return {"success": True, "message": "Project deleted successfully"}


@router.get("/projects/{project_id}", response_model=ChatProjectResponse)
async def get_project(
    http_request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a single chat project by ID with its sessions"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    # Query project with sessions
    query = (
        select(ChatProject)
        .options(selectinload(ChatProject.sessions))
        .where(ChatProject.id == uuid.UUID(project_id))
        .where(ChatProject.user_id == user.id)
        .where(ChatProject.is_active == True)
    )

    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Build sessions with message counts
    sessions = []
    for session in project.sessions:
        # Get message count for each session
        count_query = select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session.id)
        count_result = await db.execute(count_query)
        message_count = count_result.scalar() or 0

        sessions.append(ChatSessionResponse(
            id=str(session.id),
            project_id=str(project.id),
            name=session.name,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=message_count
        ))

    return ChatProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        is_active=project.is_active,
        session_count=len(sessions),
        sessions=sessions
    )


# ============================================================================
# Session Endpoints
# ============================================================================

@router.get("/projects/{project_id}/sessions", response_model=List[ChatSessionResponse])
async def get_project_sessions(
    http_request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get all sessions for a project"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user.id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get sessions with message counts
    query = (
        select(
            ChatSession,
            func.count(ChatMessage.id.distinct()).label('message_count')
        )
        .select_from(ChatSession)
        .outerjoin(ChatMessage, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.project_id == uuid.UUID(project_id))
        .group_by(ChatSession.id)
        .order_by(desc(ChatSession.updated_at))
    )

    result = await db.execute(query)
    sessions_with_counts = result.all()

    return [
        ChatSessionResponse(
            id=str(session.id),
            project_id=str(session.project_id),
            name=session.name,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=message_count or 0
        )
        for session, message_count in sessions_with_counts
    ]


@router.post("/projects/{project_id}/sessions", response_model=ChatSessionResponse)
async def create_session(
    http_request: Request,
    project_id: str,
    request: ChatSessionCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat session in a project"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user.id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    session = ChatSession(
        project_id=project.id,
        name=request.name
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return ChatSessionResponse(
        id=str(session.id),
        project_id=str(project.id),
        name=session.name,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0
    )


@router.put("/projects/{project_id}/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    http_request: Request,
    project_id: str,
    session_id: str,
    request: UpdateSessionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a session name"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user.id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get session
    session_query = select(ChatSession).where(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.project_id == project.id
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if request.name is not None:
        session.name = request.name

    session.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    # Get message count
    count_query = select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session.id)
    count_result = await db.execute(count_query)
    message_count = count_result.scalar() or 0

    return ChatSessionResponse(
        id=str(session.id),
        project_id=str(project.id),
        name=session.name,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=message_count
    )


@router.delete("/projects/{project_id}/sessions/{session_id}")
async def delete_session(
    http_request: Request,
    project_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a session and all its messages/workflows"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user.id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get session
    session_query = select(ChatSession).where(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.project_id == project.id
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete session (cascade will handle messages and workflows)
    await db.delete(session)
    await db.commit()

    return {"success": True, "message": "Session deleted successfully"}


# ============================================================================
# Message Endpoints (now session-based)
# ============================================================================

@router.get("/projects/{project_id}/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(
    http_request: Request,
    project_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(100, le=10000),
    offset: int = Query(0, ge=0)
):
    """Get messages for a session"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user.id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify session belongs to project
    session_query = select(ChatSession).where(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.project_id == project.id
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == uuid.UUID(session_id))
        .order_by(ChatMessage.created_at)
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    messages = result.scalars().all()

    return [
        ChatMessageResponse(
            id=str(msg.id),
            session_id=str(msg.session_id),
            role=msg.role,
            content=msg.content,
            message_metadata=msg.message_metadata or {},
            created_at=msg.created_at
        )
        for msg in messages
    ]


# Legacy endpoint for backward compatibility
@router.get("/projects/{project_id}/messages", response_model=List[ChatMessageResponse])
async def get_project_messages_legacy(
    http_request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(100, le=10000),
    offset: int = Query(0, ge=0)
):
    """Get all messages for a project (across all sessions) - legacy endpoint"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user.id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all messages across all sessions in this project
    query = (
        select(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(ChatSession.project_id == uuid.UUID(project_id))
        .order_by(ChatMessage.created_at)
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    messages = result.scalars().all()

    return [
        ChatMessageResponse(
            id=str(msg.id),
            session_id=str(msg.session_id),
            role=msg.role,
            content=msg.content,
            message_metadata=msg.message_metadata or {},
            created_at=msg.created_at
        )
        for msg in messages
    ]


# ============================================================================
# Workflow Endpoints (now session-based)
# ============================================================================

@router.get("/projects/{project_id}/sessions/{session_id}/workflows")
async def get_session_workflows(
    http_request: Request,
    project_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """Get workflow executions for a session with their steps"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user.id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify session belongs to project
    session_query = select(ChatSession).where(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.project_id == project.id
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get workflow executions with their steps
    query = (
        select(WorkflowExecution)
        .options(selectinload(WorkflowExecution.steps))
        .where(WorkflowExecution.session_id == uuid.UUID(session_id))
        .order_by(desc(WorkflowExecution.started_at))
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    workflows = result.scalars().all()

    # Format response
    workflow_list = []
    for wf in workflows:
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
                "step_metadata": step.step_metadata
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


# Legacy endpoint for backward compatibility
@router.get("/projects/{project_id}/workflows")
async def get_project_workflows_legacy(
    http_request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """Get all workflow executions for a project (across all sessions) - legacy endpoint"""
    auth0_id = await get_current_user_id(http_request)
    user = await get_or_create_user(db, auth0_id)
    require_approved(user)

    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user.id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all workflow executions across all sessions
    query = (
        select(WorkflowExecution)
        .options(selectinload(WorkflowExecution.steps))
        .join(ChatSession, WorkflowExecution.session_id == ChatSession.id)
        .where(ChatSession.project_id == uuid.UUID(project_id))
        .order_by(desc(WorkflowExecution.started_at))
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    workflows = result.scalars().all()

    # Format response
    workflow_list = []
    for wf in workflows:
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
                "step_metadata": step.step_metadata
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
        auth0_id = await get_current_user_id(http_request)
        user = await get_or_create_user(db, auth0_id)
        require_approved(user)

        # Verify project ownership
        project_query = select(ChatProject).where(
            ChatProject.id == uuid.UUID(project_id),
            ChatProject.user_id == user.id
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
            "user_id": auth0_id
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
