"""
Files API - Endpoints for file management using Sandbox storage

All files are stored in project sandboxes:
  /data/sandboxes/{user_id}/{project_id}/
    ├── uploads/      # User uploaded files
    ├── generated/    # Agent generated files (charts, code output)
    └── workspace/    # Temporary working files

API Endpoints:
  - GET /user                                     - List all files for current user
  - GET /{file_id}/download                       - Download file by ID
  - DELETE /{file_id}                             - Delete file by ID
  - POST /project/{project_id}/upload             - Upload file to project
  - GET /project/{project_id}                     - List files in project
  - GET /project/{project_id}/download/{category}/{filename} - Download by path
  - GET /project/{project_id}/content/{category}/{filename}  - Get content
  - DELETE /project/{project_id}/{category}/{filename}       - Delete by path
"""

import os
import mimetypes
import base64
import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import FileResponse, Response
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends

from app.api.v1.auth import get_current_user_id
from app.core.infrastructure.database import get_db_session
from app.models.database import User
from app.models.enums import UserStatus

router = APIRouter()


async def get_user_uuid(request: Request, db: AsyncSession) -> str:
    """Get user UUID from auth0_id for sandbox operations. Requires approved user."""
    auth0_id = await get_current_user_id(request)
    query = select(User).where(User.auth0_id == auth0_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user is approved
    if user.status != UserStatus.APPROVED:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Your account is not approved (status: {user.status.value})"
        )

    return str(user.id)


# ==================== User Files API (Global) ====================

@router.get("/user")
async def list_user_files(request: Request, db: AsyncSession = Depends(get_db_session)):
    """
    List all files for the current user across all projects.

    Returns:
        List of files with metadata from all user's projects
    """
    try:
        user_id = await get_user_uuid(request, db)

        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()

        # Get user's sandbox directory
        user_dir = sandbox.get_user_sandbox(user_id)

        if not user_dir.exists():
            return {"success": True, "data": []}

        files = []

        # Iterate through all project directories
        for project_dir in user_dir.iterdir():
            if not project_dir.is_dir() or project_dir.name.startswith('.'):
                continue

            project_id = project_dir.name

            # Read project metadata to get file IDs
            metadata_path = project_dir / ".metadata.json"
            file_metadata = {}
            if metadata_path.exists():
                try:
                    meta = json.loads(metadata_path.read_text())
                    for f in meta.get("files", []):
                        file_metadata[f.get("filename")] = f
                except Exception:
                    pass

            # List files in each category
            for category in ["uploads", "generated", "workspace"]:
                cat_dir = project_dir / category
                if cat_dir.exists():
                    for file_path in cat_dir.iterdir():
                        if file_path.is_file() and not file_path.name.startswith('.'):
                            stat = file_path.stat()
                            content_type = mimetypes.guess_type(file_path.name)[0] or 'application/octet-stream'

                            # Get file_id from metadata if available
                            # Use composite key for uniqueness: project_id/category/filename
                            meta_info = file_metadata.get(file_path.name, {})
                            composite_id = f"{project_id}/{category}/{file_path.name}"
                            file_id = meta_info.get("file_id", composite_id)

                            files.append({
                                "id": file_id,
                                "original_filename": meta_info.get("original_filename", file_path.name),
                                "filename": file_path.name,
                                "file_size": stat.st_size,
                                "file_type": content_type,
                                "category": category,
                                "project_id": project_id,
                                "created_by_agent": category == "generated",
                                "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                "created_at": meta_info.get("created_at", datetime.fromtimestamp(stat.st_ctime).isoformat()),
                            })

        # Sort by updated time (newest first)
        files.sort(key=lambda x: x["updated_at"], reverse=True)

        return {"success": True, "data": files}

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/{file_id:path}/download")
async def download_file_by_id(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Download a file by its file_id.

    Args:
        file_id: The file ID - can be:
                 - Composite ID: "project_id/category/filename"
                 - UUID from metadata
                 - Filename (legacy)

    Returns:
        File download response
    """
    try:
        user_id = await get_user_uuid(request, db)

        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()

        user_dir = sandbox.get_user_sandbox(user_id)

        if not user_dir.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Try to parse as composite ID first: "project_id/category/filename"
        parts = file_id.split('/')
        if len(parts) >= 3:
            project_id = parts[0]
            category = parts[1]
            filename = '/'.join(parts[2:])

            if category in ["uploads", "generated", "workspace"]:
                file_path = user_dir / project_id / category / filename

                # Security check
                try:
                    file_path.resolve().relative_to(user_dir.resolve())
                except ValueError:
                    raise HTTPException(status_code=403, detail="Access denied")

                if file_path.exists():
                    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                    return FileResponse(
                        path=str(file_path),
                        filename=filename,
                        media_type=content_type
                    )

        # Fallback: Search through all projects
        for project_dir in user_dir.iterdir():
            if not project_dir.is_dir() or project_dir.name.startswith('.'):
                continue

            # Check metadata first
            metadata_path = project_dir / ".metadata.json"
            if metadata_path.exists():
                try:
                    meta = json.loads(metadata_path.read_text())
                    for f in meta.get("files", []):
                        if f.get("file_id") == file_id:
                            # Found! Get the file path
                            category = f.get("category", "generated")
                            filename = f.get("filename")
                            file_path = project_dir / category / filename

                            if file_path.exists():
                                content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                                return FileResponse(
                                    path=str(file_path),
                                    filename=f.get("original_filename", filename),
                                    media_type=content_type
                                )
                except Exception:
                    pass

            # Fallback: search by filename matching file_id
            for category in ["uploads", "generated", "workspace"]:
                cat_dir = project_dir / category
                if cat_dir.exists():
                    for file_path in cat_dir.iterdir():
                        if file_path.is_file() and file_path.name == file_id:
                            content_type = mimetypes.guess_type(file_path.name)[0] or 'application/octet-stream'
                            return FileResponse(
                                path=str(file_path),
                                filename=file_path.name,
                                media_type=content_type
                            )

        # Final fallback: Check database for files saved with storage_provider="database"
        # This handles files saved by save_agent_file() which stores in database, not sandbox
        try:
            from uuid import UUID as UUIDType

            # Try to parse file_id as UUID (database file ID)
            try:
                file_uuid = UUIDType(file_id)
            except ValueError:
                # Not a valid UUID, file not found anywhere
                raise HTTPException(status_code=404, detail="File not found")

            # Check database
            from app.database.connection import async_session_maker
            from app.models import ProjectFile
            from sqlalchemy import select

            async with async_session_maker() as session:
                result = await session.execute(
                    select(ProjectFile).where(ProjectFile.id == file_uuid)
                )
                pf = result.scalar_one_or_none()

                if pf and pf.file_data:
                    content_type = pf.content_type or 'application/octet-stream'
                    filename = pf.original_filename or pf.filename or "download"

                    return Response(
                        content=pf.file_data,
                        media_type=content_type,
                        headers={
                            "Content-Disposition": f'attachment; filename="{filename}"'
                        }
                    )
        except HTTPException:
            raise
        except Exception as db_error:
            # Log error but don't expose internal details
            print(f"⚠️ Database file lookup failed: {db_error}")

        raise HTTPException(status_code=404, detail="File not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id:path}")
async def delete_file_by_id(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete a file by its file_id.

    Args:
        file_id: The file ID - can be:
                 - Composite ID: "project_id/category/filename"
                 - UUID from metadata
                 - Filename (legacy)

    Returns:
        Success message
    """
    try:
        user_id = await get_user_uuid(request, db)

        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()

        user_dir = sandbox.get_user_sandbox(user_id)

        if not user_dir.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Try to parse as composite ID first: "project_id/category/filename"
        parts = file_id.split('/')
        if len(parts) >= 3:
            # Composite ID format: project_id/category/filename
            project_id = parts[0]
            category = parts[1]
            filename = '/'.join(parts[2:])  # Handle filenames with slashes

            if category in ["uploads", "generated", "workspace"]:
                file_path = user_dir / project_id / category / filename

                # Security check
                try:
                    file_path.resolve().relative_to(user_dir.resolve())
                except ValueError:
                    raise HTTPException(status_code=403, detail="Access denied")

                if file_path.exists():
                    file_path.unlink()

                    # Update metadata if exists
                    metadata_path = user_dir / project_id / ".metadata.json"
                    if metadata_path.exists():
                        try:
                            meta = json.loads(metadata_path.read_text())
                            meta["files"] = [
                                f for f in meta.get("files", [])
                                if f.get("filename") != filename
                            ]
                            metadata_path.write_text(json.dumps(meta, indent=2))
                        except Exception:
                            pass

                    return {
                        "success": True,
                        "message": f"File '{filename}' deleted successfully"
                    }

        # Fallback: Search through all projects
        for project_dir in user_dir.iterdir():
            if not project_dir.is_dir() or project_dir.name.startswith('.'):
                continue

            # Check metadata first
            metadata_path = project_dir / ".metadata.json"
            if metadata_path.exists():
                try:
                    meta = json.loads(metadata_path.read_text())
                    for f in meta.get("files", []):
                        if f.get("file_id") == file_id:
                            # Found! Delete the file
                            category = f.get("category", "generated")
                            filename = f.get("filename")
                            file_path = project_dir / category / filename

                            if file_path.exists():
                                file_path.unlink()

                                # Update metadata
                                meta["files"] = [
                                    x for x in meta.get("files", [])
                                    if x.get("file_id") != file_id
                                ]
                                metadata_path.write_text(json.dumps(meta, indent=2))

                                return {
                                    "success": True,
                                    "message": f"File deleted successfully"
                                }
                except Exception:
                    pass

            # Fallback: search by filename matching file_id
            for category in ["uploads", "generated", "workspace"]:
                cat_dir = project_dir / category
                if cat_dir.exists():
                    for file_path in cat_dir.iterdir():
                        if file_path.is_file() and file_path.name == file_id:
                            file_path.unlink()
                            return {
                                "success": True,
                                "message": f"File deleted successfully"
                            }

        raise HTTPException(status_code=404, detail="File not found")

    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== File Upload API ====================

@router.post("/project/{project_id}/upload")
async def upload_project_file(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    category: str = Query("uploads", description="Category: uploads, generated, workspace"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Upload a file to project sandbox.

    Args:
        project_id: Project UUID
        file: File to upload
        category: Where to save - "uploads" (default), "generated", or "workspace"

    Returns:
        File metadata including file_id and path
    """
    try:
        user_id = await get_user_uuid(request, db)

        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()

        # Validate category
        if category not in ["uploads", "generated", "workspace"]:
            raise HTTPException(status_code=400, detail="Invalid category")

        # Read file content
        content = await file.read()
        original_filename = file.filename or "uploaded_file"

        # Save using sandbox manager (handles ID generation and metadata)
        result = sandbox.save_file(
            user_id=user_id,
            project_id=project_id,
            filename=original_filename,
            content=content,
            category=category
        )

        content_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'

        return {
            "success": True,
            "data": {
                "file_id": result["file_id"],
                "id": result["file_id"],  # Compatibility
                "filename": result["filename"],
                "original_filename": result["original_filename"],
                "category": category,
                "size": result["size"],
                "file_size": result["size"],
                "content_type": content_type,
                "path": result["relative_path"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Project Files API ====================

@router.get("/project/{project_id}")
async def list_project_files(
    project_id: str,
    request: Request,
    category: Optional[str] = Query(None, description="Filter by category: uploads, generated, workspace"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all files in a project's sandbox.

    Args:
        project_id: Project UUID
        category: Optional filter (uploads, generated, workspace)

    Returns:
        List of files with metadata
    """
    try:
        user_id = await get_user_uuid(request, db)

        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()

        # Get sandbox path
        sandbox_root = sandbox.get_project_sandbox(user_id, project_id)

        # Read metadata for file IDs
        metadata_path = sandbox_root / ".metadata.json"
        file_metadata = {}
        if metadata_path.exists():
            try:
                meta = json.loads(metadata_path.read_text())
                for f in meta.get("files", []):
                    file_metadata[f.get("filename")] = f
            except Exception:
                pass

        files = []
        categories = [category] if category else ["uploads", "generated", "workspace"]

        for cat in categories:
            cat_dir = sandbox_root / cat
            if cat_dir.exists():
                for file_path in cat_dir.iterdir():
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        stat = file_path.stat()
                        content_type = mimetypes.guess_type(file_path.name)[0] or 'application/octet-stream'

                        meta_info = file_metadata.get(file_path.name, {})
                        composite_id = f"{project_id}/{cat}/{file_path.name}"

                        files.append({
                            "id": meta_info.get("file_id", composite_id),
                            "filename": file_path.name,
                            "original_filename": meta_info.get("original_filename", file_path.name),
                            "category": cat,
                            "size": stat.st_size,
                            "content_type": content_type,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "path": f"{cat}/{file_path.name}"
                        })

        # Sort by modified time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)

        return {"success": True, "data": files}

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/project/{project_id}/download/{category}/{filename:path}")
async def download_project_file(
    project_id: str,
    category: str,
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Download a file from project sandbox.

    Args:
        project_id: Project UUID
        category: File category (uploads, generated, workspace)
        filename: File name

    Returns:
        File download response
    """
    try:
        user_id = await get_user_uuid(request, db)

        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()

        # Validate category
        if category not in ["uploads", "generated", "workspace"]:
            raise HTTPException(status_code=400, detail="Invalid category")

        # Get file path
        sandbox_root = sandbox.get_project_sandbox(user_id, project_id)
        file_path = sandbox_root / category / filename

        # Security check: ensure path is within sandbox
        try:
            file_path.resolve().relative_to(sandbox_root.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Determine content type
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=content_type
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}/content/{category}/{filename:path}")
async def get_project_file_content(
    project_id: str,
    category: str,
    filename: str,
    request: Request,
    as_base64: bool = Query(False, description="Return content as base64 (for images)"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get file content from project sandbox.

    Args:
        project_id: Project UUID
        category: File category (uploads, generated, workspace)
        filename: File name
        as_base64: If True, return binary content as base64

    Returns:
        File content (text or base64)
    """
    try:
        user_id = await get_user_uuid(request, db)

        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()

        # Validate category
        if category not in ["uploads", "generated", "workspace"]:
            raise HTTPException(status_code=400, detail="Invalid category")

        # Get file path
        sandbox_root = sandbox.get_project_sandbox(user_id, project_id)
        file_path = sandbox_root / category / filename

        # Security check
        try:
            file_path.resolve().relative_to(sandbox_root.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Determine content type
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()

        # Return as base64 for images/binary files
        if as_base64 or content_type.startswith('image/'):
            b64_data = base64.b64encode(file_data).decode('utf-8')
            return {
                "success": True,
                "data": {
                    "filename": filename,
                    "content_type": content_type,
                    "size": len(file_data),
                    "base64": f"data:{content_type};base64,{b64_data}"
                }
            }

        # Try to decode as text
        try:
            content = file_data.decode('utf-8')
            return {
                "success": True,
                "data": {
                    "filename": filename,
                    "content_type": content_type,
                    "size": len(file_data),
                    "content": content
                }
            }
        except UnicodeDecodeError:
            # Fall back to base64 for binary files
            b64_data = base64.b64encode(file_data).decode('utf-8')
            return {
                "success": True,
                "data": {
                    "filename": filename,
                    "content_type": content_type,
                    "size": len(file_data),
                    "base64": f"data:{content_type};base64,{b64_data}"
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/project/{project_id}/{category}/{filename:path}")
async def delete_project_file(
    project_id: str,
    category: str,
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete a file from project sandbox.

    Args:
        project_id: Project UUID
        category: File category (uploads, generated, workspace)
        filename: File name

    Returns:
        Success message
    """
    try:
        user_id = await get_user_uuid(request, db)

        from app.services.sandbox import get_sandbox_manager
        sandbox = get_sandbox_manager()

        # Validate category
        if category not in ["uploads", "generated", "workspace"]:
            raise HTTPException(status_code=400, detail="Invalid category")

        # Get file path
        sandbox_root = sandbox.get_project_sandbox(user_id, project_id)
        file_path = sandbox_root / category / filename

        # Security check
        try:
            file_path.resolve().relative_to(sandbox_root.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Delete file
        file_path.unlink()

        # Update metadata if exists
        metadata_path = sandbox_root / ".metadata.json"
        if metadata_path.exists():
            try:
                meta = json.loads(metadata_path.read_text())
                meta["files"] = [
                    f for f in meta.get("files", [])
                    if f.get("filename") != filename
                ]
                metadata_path.write_text(json.dumps(meta, indent=2))
            except Exception:
                pass

        return {
            "success": True,
            "message": f"File '{filename}' deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}
