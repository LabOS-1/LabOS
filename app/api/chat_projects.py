"""
Simplified Chat Projects API - No Sessions, Direct Project to Messages
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import uuid
import hashlib
import asyncio
import logging

from app.core.database import get_db_session
from app.core.cloud_logging import set_log_context, clear_log_context, get_logger

# Initialize logger
logger = get_logger(__name__)
from app.models import (
    ChatProject, ChatMessage, WorkflowExecution,
    ChatProjectResponse, ChatMessageResponse,
    MessageRole, ProjectFile, FileType, FileStatus
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

class SendMessageRequest(BaseModel):
    content: str
    role: MessageRole = MessageRole.USER
    mode: str = "deep"  # "fast" or "deep"

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

@router.post("/projects/{project_id}/messages")
async def send_message_to_project(
    http_request: Request,
    project_id: str,
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Send a message to a project and trigger AI processing"""
    # Get user ID from authentication
    user_id = await get_current_user_id(http_request)

    # Set logging context for ALL subsequent logs (including smolagents)
    set_log_context(user_id=user_id, project_id=project_id)

    logger.info(f"User sending message to project", extra={
        "message_length": len(request.content),
        "role": request.role.value
    })

    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user_id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create message
    message = ChatMessage(
        project_id=uuid.UUID(project_id),
        role=request.role,
        content=request.content
    )
    
    db.add(message)
    
    # Update project timestamp
    project.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(message)
    
    # If this is a user message, trigger AI processing with project context
    if request.role == MessageRole.USER:
        try:
            # Import LabOS service
            from app.services.labos_service import LabOSService
            from app.main import labos_service  # Get the global instance
            
            # Generate workflow ID for this project conversation
            import time
            workflow_id = f"project_{project_id}_{int(time.time() * 1000)}"

            # Update logging context with workflow_id
            set_log_context(user_id=user_id, project_id=project_id, workflow_id=workflow_id)

            logger.info(f"Starting AI workflow", extra={
                "workflow_id": workflow_id,
                "message_preview": request.content[:100]
            })

            # DEBUG: Log the mode value received from frontend
            print(f"🔍 DEBUG: Received mode from frontend: '{request.mode}' (type: {type(request.mode).__name__})")
            mode_to_use = request.mode if request.mode else "deep"
            print(f"🔍 DEBUG: Using mode: '{mode_to_use}'")

            # Start async AI processing with project_id and user_id
            import asyncio
            task = asyncio.create_task(
                labos_service.process_message_async(
                    message=request.content,
                    workflow_id=workflow_id,
                    project_id=project_id,  # Pass project_id for saving
                    user_id=user_id,  # Pass user_id for file context
                    mode=mode_to_use  # Pass mode (fast/deep)
                )
            )
            
            # Register task in active_workflows for cancellation support
            labos_service.active_workflows[workflow_id] = task
            
            # Return processing status (like /api/chat/send)
            return {
                "success": True,
                "data": {
                    "message": "Processing started",
                    "workflow_id": workflow_id,
                    "status": "processing",
                    "project_id": project_id,
                    "note": "AI response and workflow will be saved to project automatically"
                }
            }
            
        except Exception as e:
            print(f"Error starting AI processing: {e}")
            # Still return success for message storage
            return {
                "success": True,
                "data": {
                    "message": "Message saved, AI processing failed",
                    "error": str(e)
                }
            }
    
    # For non-user messages, just return success
    return {
        "success": True,
        "data": {
            "message": "Message saved successfully",
            "message_id": str(message.id)
        }
    }

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

@router.post("/workflows/cancel-all")
async def cancel_all_workflows(
    http_request: Request
):
    """Cancel ALL active workflows for the current user"""
    try:
        # Get user ID from authentication
        user_id = await get_current_user_id(http_request)
        
        # Get all active workflows and cancel them
        from app.main import labos_service
        active_workflows = labos_service.get_active_workflows()
        
        cancelled_count = 0
        for workflow_id in active_workflows:
            success = await labos_service.cancel_workflow(workflow_id)
            if success:
                cancelled_count += 1
        
        return {
            "success": True,
            "data": {
                "message": f"Cancelled {cancelled_count} active workflows",
                "cancelled_workflows": cancelled_count,
                "total_active": len(active_workflows)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error cancelling all workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        
        # Cancel the workflow
        from app.main import labos_service
        success = await labos_service.cancel_workflow(workflow_id)
        
        if success:
            return {
                "success": True,
                "data": {
                    "message": "Workflow cancelled successfully",
                    "workflow_id": workflow_id,
                    "project_id": project_id
                }
            }
        else:
            return {
                "success": False,
                "error": "Workflow not found or already completed",
                "workflow_id": workflow_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error cancelling workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/projects/{project_id}/messages/with-file")
async def send_message_with_file(
    http_request: Request,
    project_id: str,
    file: UploadFile = File(...),
    message: str = Form(...),
    db: AsyncSession = Depends(get_db_session)
):
    """Send a message with an attached file to a project"""
    try:
        # Get user ID from authentication (with test fallback)
        try:
            user_id = await get_current_user_id(http_request)
        except HTTPException:
            # Test mode: use default user ID
            user_id = "test_user_123"
            print("⚠️  Using test user ID for file upload")
        
        # Verify project ownership
        project_query = select(ChatProject).where(
            ChatProject.id == uuid.UUID(project_id),
            ChatProject.user_id == user_id
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        file_data = await file.read()
        file_size = len(file_data)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File too large (>10MB)")
        
        file_hash = hashlib.sha256(file_data).hexdigest()
        safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
        
        project_file = ProjectFile(
            user_id=user_id,
            project_id=uuid.UUID(project_id),
            filename=safe_filename,
            original_filename=file.filename or "unknown",
            file_size=file_size,
            content_type=file.content_type,
            file_hash=file_hash,
            file_data=file_data,
            storage_path=None,
            storage_provider="database",
            file_type=FileType.USER_UPLOAD,
            category="chat_attachment",
            tags=["chat", "attachment"],
            created_by_agent="user",
            status=FileStatus.ACTIVE
        )
        
        db.add(project_file)
        await db.flush()
        chat_message = ChatMessage(
            project_id=uuid.UUID(project_id),
            role=MessageRole.USER,
            content=message,
            message_metadata={
                "attached_files": [{
                    "file_id": str(project_file.id),
                    "filename": project_file.original_filename,
                    "size": project_file.file_size,
                    "content_type": project_file.content_type,
                    "hash": project_file.file_hash[:8] + "..."
                }]
            }
        )
        
        db.add(chat_message)
        
        project_file.message_id = chat_message.id
        
        project.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(chat_message)
        await db.refresh(project_file)
        
        # Smart message formatting based on file size and type
        file_ext = Path(project_file.original_filename).suffix.lower()
        is_small_text = (
            project_file.file_size < 50_000 and 
            file_ext in ['.txt', '.csv', '.json', '.md', '.log', '.yaml', '.yml']
        )
        
        if is_small_text:
            # Small text file: include content directly
            try:
                file_content = project_file.file_data.decode('utf-8', errors='replace')
                enhanced_message = f"""User message: {message}

Attached file: {project_file.original_filename}
File size: {project_file.file_size} bytes
File type: {project_file.content_type}

File content:
```
{file_content}
```

Please analyze the file content above and respond to the user's message."""
            except Exception as e:
                # Fallback to tool-based access
                enhanced_message = f"""User message: {message}

Attached file: {project_file.original_filename}
- File ID: {project_file.id}
- File size: {project_file.file_size} bytes
- File type: {project_file.content_type}

To access the file content, use the tool:
read_project_file("{project_file.id}")

Then analyze the content and respond to the user's message."""
        else:
            # Large file or binary: use tool
            enhanced_message = f"""User message: {message}

Attached file: {project_file.original_filename}
- File ID: {project_file.id}
- File size: {project_file.file_size:,} bytes
- File type: {project_file.content_type}

To access the file content, use the tool:
read_project_file("{project_file.id}")

This will return the file content for analysis. Then respond to the user's message based on the content."""
        
        try:
            from app.services.labos_service import LabOSService
            from app.main import labos_service
            
            workflow_id = f"project_{project_id}_file_{int(datetime.now().timestamp() * 1000)}"
            
            # 异步处理，传递 user_id 和 project_id
            task = asyncio.create_task(
                labos_service.process_message_async(
                    message=enhanced_message,
                    workflow_id=workflow_id,
                    project_id=project_id,
                    user_id=user_id  # Pass user_id for file context
                )
            )
            
            # Register task in active_workflows for cancellation support
            labos_service.active_workflows[workflow_id] = task
            
            return {
                "success": True,
                "data": {
                    "message": "Message with file sent successfully",
                    "message_id": str(chat_message.id),
                    "file_id": str(project_file.id),
                    "workflow_id": workflow_id,
                    "status": "processing",
                    "project_id": project_id,
                    "file_info": {
                        "filename": project_file.original_filename,
                        "size": project_file.file_size,
                        "content_type": project_file.content_type
                    }
                }
            }
            
        except Exception as e:
            print(f"Error starting AI processing: {e}")
            return {
                "success": True,
                "data": {
                    "message": "Message and file saved, but AI processing failed",
                    "message_id": str(chat_message.id),
                    "file_id": str(project_file.id),
                    "error": str(e)
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in send_message_with_file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

