"""
Files API - Endpoints for file management
"""

import os
import time
import hashlib
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request, Form
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import io

from app.services.labos_service import LabOSService
from app.core.database import get_db_session
from app.models import ProjectFile, FileType, FileStatus, ProjectFileResponse
from app.api.chat_projects import get_current_user_id

router = APIRouter()


async def get_labos_service() -> LabOSService:
    if not hasattr(get_labos_service, "_instance"):
        get_labos_service._instance = LabOSService()
        await get_labos_service._instance.initialize()
    return get_labos_service._instance

@router.get("/user")
async def get_user_files(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    project_id: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):

    try:
        user_id = await get_current_user_id(request)
        
        query = select(ProjectFile).where(
            ProjectFile.user_id == user_id,
            ProjectFile.status != FileStatus.DELETED
        )
        
        if project_id:
            query = query.where(ProjectFile.project_id == uuid.UUID(project_id))
        
        query = query.order_by(desc(ProjectFile.updated_at)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        files = result.scalars().all()
        
        return {
            "success": True,
            "data": [
                {
                    "id": str(f.id),
                    "filename": f.filename,
                    "original_filename": f.original_filename,
                    "file_size": f.file_size,
                    "content_type": f.content_type,
                    "file_type": f.file_type.value,
                    "category": f.category,
                    "tags": f.tags,
                    "created_by_agent": f.created_by_agent,
                    "status": f.status.value,
                    "created_at": f.created_at.isoformat(),
                    "updated_at": f.updated_at.isoformat(),
                    "project_id": str(f.project_id) if f.project_id else None
                }
                for f in files
            ]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("")
async def get_files(
    labos_service: LabOSService = Depends(get_labos_service)
):
    """Get all files (legacy endpoint)"""
    try:
        files = await labos_service.get_files()
        
        return {
            "success": True,
            "data": files
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/content")
async def get_file_content(
    path: str = Query(..., description="File path"),
    labos_service: LabOSService = Depends(get_labos_service)
):
    """Get file content"""
    try:
        file_path = Path(path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
            
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
            
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try binary mode for non-text files
            with open(file_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='replace')
                
        return {
            "success": True,
            "data": {"content": content}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/download")
async def download_file(
    path: str = Query(..., description="File path")
):
    """Download a file"""
    try:
        file_path = Path(path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
            
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
            
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("")
async def delete_file(
    path: str = Query(..., description="File path")
):
    """Delete a file"""
    try:
        file_path = Path(path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
            
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
            
        # Delete the file
        file_path.unlink()
        
        return {
            "success": True,
            "message": f"File {file_path.name} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/{file_id}/download")
async def download_file_by_id(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Download a file from database by file_id"""
    try:
        # Verify user authentication (no fallback for production)
        user_id = await get_current_user_id(request)
        
        # Query file from database
        query = select(ProjectFile).where(
            ProjectFile.id == uuid.UUID(file_id),
            ProjectFile.user_id == user_id,
            ProjectFile.status != FileStatus.DELETED
        )
        
        result = await db.execute(query)
        project_file = result.scalar_one_or_none()
        
        if not project_file:
            raise HTTPException(status_code=404, detail="File not found or access denied")
        
        # Update last accessed time
        project_file.last_accessed = datetime.utcnow()
        await db.commit()
        
        # Return file as streaming response
        file_stream = io.BytesIO(project_file.file_data)
        
        return StreamingResponse(
            file_stream,
            media_type=project_file.content_type or 'application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{project_file.original_filename}"',
                'Content-Length': str(project_file.file_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.get("/{file_id}/content")
async def get_file_content_by_id(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Get file content (text files only) by file_id"""
    try:
        # Verify user authentication (no fallback for production)
        user_id = await get_current_user_id(request)
        
        # Query file from database
        query = select(ProjectFile).where(
            ProjectFile.id == uuid.UUID(file_id),
            ProjectFile.user_id == user_id,
            ProjectFile.status != FileStatus.DELETED
        )
        
        result = await db.execute(query)
        project_file = result.scalar_one_or_none()
        
        if not project_file:
            raise HTTPException(status_code=404, detail="File not found or access denied")
        
        # Update last accessed time
        project_file.last_accessed = datetime.utcnow()
        await db.commit()
        
        # Try to decode as text
        try:
            content = project_file.file_data.decode('utf-8')
            
            return {
                "success": True,
                "data": {
                    "filename": project_file.original_filename,
                    "content": content,
                    "content_type": project_file.content_type,
                    "file_size": project_file.file_size
                }
            }
        except UnicodeDecodeError:
            return {
                "success": False,
                "error": "File is not a text file or uses unsupported encoding"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.delete("/{file_id}")
async def delete_file_by_id(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a file by file_id"""
    try:
        # Verify user authentication (no fallback for production)
        user_id = await get_current_user_id(request)
        
        # Query file from database
        query = select(ProjectFile).where(
            ProjectFile.id == uuid.UUID(file_id),
            ProjectFile.user_id == user_id,
            ProjectFile.status != FileStatus.DELETED
        )
        
        result = await db.execute(query)
        project_file = result.scalar_one_or_none()
        
        if not project_file:
            raise HTTPException(status_code=404, detail="File not found or access denied")
        
        # Soft delete (mark as DELETED)
        project_file.status = FileStatus.DELETED
        project_file.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"File '{project_file.original_filename}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ❌ Removed: /upload endpoint (unused, use chat interface instead)

@router.post("/execute")
async def execute_file(
    path: str,
    labos_service: LabOSService = Depends(get_labos_service)
):
    """Execute a file (Python scripts only)"""
    try:
        file_path = Path(path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
            
        if file_path.suffix != ".py":
            raise HTTPException(status_code=400, detail="Only Python files can be executed")
            
        # TODO: Implement file execution through LabOS
        execution = {
            "id": f"exec_{int(time.time())}",
            "task": f"Execute {file_path.name}",
            "status": "pending",
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "files_created": [],
            "tools_used": [],
            "performance_metrics": {
                "execution_time": 0,
                "memory_usage": 0,
                "cpu_usage": 0,
                "success_rate": 0,
                "error_count": 0
            }
        }
        
        return {
            "success": True,
            "data": execution
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
