"""
Admin API endpoints for user management and waitlist approval
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from pydantic import BaseModel
import asyncio

from app.core.database import get_db_session
from app.models import User, UserStatus
from app.api.chat_projects import get_current_user_id
from app.services.email_service import send_approval_email

logger = logging.getLogger(__name__)

router = APIRouter()

# ========== Pydantic Models ==========

class UserApprovalRequest(BaseModel):
    """Request to approve or reject a user"""
    user_id: str
    status: UserStatus  # 'approved' or 'rejected'
    rejection_reason: Optional[str] = None

class UserUpdateRequest(BaseModel):
    """Request to update user information"""
    status: Optional[UserStatus] = None
    is_admin: Optional[bool] = None
    rejection_reason: Optional[str] = None

class UserResponse(BaseModel):
    """User response model"""
    id: str
    email: str
    name: Optional[str]
    picture: Optional[str]
    status: str
    is_admin: bool
    institution: Optional[str]
    research_field: Optional[str]
    application_reason: Optional[str]
    created_at: str
    last_login: Optional[str]
    approved_at: Optional[str]
    approved_by: Optional[str]

# ========== Helper Functions ==========

async def check_admin_permission(request: Request, db: AsyncSession) -> User:
    """Check if current user is an admin"""
    try:
        # Get current user ID from auth
        from app.api.chat_projects import get_current_user_id as get_user_id_from_auth
        user_id = await get_user_id_from_auth(request)
        
        # Query user from database
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        current_user = result.scalar_one_or_none()
        
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin permission required")
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin permission check error: {e}")
        raise HTTPException(status_code=500, detail="Permission check failed")

# ========== API Endpoints ==========

@router.get("/users/waitlist")
async def get_waitlist_users(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get users in waitlist or all users
    Requires admin permission
    """
    try:
        # Check admin permission
        admin_user = await check_admin_permission(request, db)
        logger.info(f"📋 Admin {admin_user.email} requesting user list")
        
        # Build query
        stmt = select(User)
        
        # Filter by status if provided
        if status:
            try:
                status_enum = UserStatus(status)
                stmt = stmt.where(User.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        # Add ordering and pagination
        stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
        
        # Execute query
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        # Get total count
        count_stmt = select(func.count(User.id))
        if status:
            count_stmt = count_stmt.where(User.status == status_enum)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar()
        
        # Convert to response format
        user_list = [
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "status": user.status.value,
                "is_admin": user.is_admin,
                # Waitlist application fields
                "institution": user.institution,
                "research_field": user.research_field,
                "application_reason": user.application_reason,
                # Enhanced waitlist fields
                "first_name": user.first_name,
                "last_name": user.last_name,
                "job_title": user.job_title,
                "organization": user.organization,
                "country": user.country,
                "experience_level": user.experience_level,
                "use_case": user.use_case,
                # Timestamps and metadata
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "approved_at": user.approved_at.isoformat() if user.approved_at else None,
                "approved_by": user.approved_by,
                "rejection_reason": user.rejection_reason
            }
            for user in users
        ]
        
        return {
            "success": True,
            "data": user_list,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get waitlist users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Approve a user from waitlist
    Requires admin permission
    """
    try:
        # Check admin permission
        admin_user = await check_admin_permission(request, db)
        
        # Get target user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user status
        target_user.status = UserStatus.APPROVED
        target_user.approved_at = datetime.utcnow()
        target_user.approved_by = admin_user.id
        target_user.rejection_reason = None  # Clear any previous rejection reason
        
        await db.commit()
        
        logger.info(f"✅ Admin {admin_user.email} approved user {target_user.email}")
        
        # Send approval email asynchronously (non-blocking)
        user_name = target_user.name or f"{target_user.first_name or ''} {target_user.last_name or ''}".strip() or None
        asyncio.create_task(
            asyncio.to_thread(send_approval_email, target_user.email, user_name)
        )
        
        return {
            "success": True,
            "message": f"User {target_user.email} has been approved",
            "data": {
                "user_id": target_user.id,
                "email": target_user.email,
                "status": target_user.status.value,
                "approved_at": target_user.approved_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approve user error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/reject")
async def reject_user(
    user_id: str,
    request: Request,
    rejection_reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Reject a user from waitlist
    Requires admin permission
    """
    try:
        # Check admin permission
        admin_user = await check_admin_permission(request, db)
        
        # Get target user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user status
        target_user.status = UserStatus.REJECTED
        target_user.rejection_reason = rejection_reason
        target_user.approved_at = None
        target_user.approved_by = None
        
        await db.commit()
        
        logger.info(f"❌ Admin {admin_user.email} rejected user {target_user.email}")
        
        return {
            "success": True,
            "message": f"User {target_user.email} has been rejected",
            "data": {
                "user_id": target_user.id,
                "email": target_user.email,
                "status": target_user.status.value,
                "rejection_reason": rejection_reason
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reject user error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update user information
    Requires admin permission
    """
    try:
        # Check admin permission
        admin_user = await check_admin_permission(request, db)
        
        # Get target user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields
        if update_data.status is not None:
            target_user.status = update_data.status
            if update_data.status == UserStatus.APPROVED:
                target_user.approved_at = datetime.utcnow()
                target_user.approved_by = admin_user.id
        
        if update_data.is_admin is not None:
            target_user.is_admin = update_data.is_admin
        
        if update_data.rejection_reason is not None:
            target_user.rejection_reason = update_data.rejection_reason
        
        await db.commit()
        
        logger.info(f"✏️ Admin {admin_user.email} updated user {target_user.email}")
        
        return {
            "success": True,
            "message": f"User {target_user.email} has been updated",
            "data": {
                "user_id": target_user.id,
                "email": target_user.email,
                "status": target_user.status.value,
                "is_admin": target_user.is_admin
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_admin_stats(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get admin statistics
    Requires admin permission
    """
    try:
        # Check admin permission
        admin_user = await check_admin_permission(request, db)
        
        # Count users by status
        waitlist_stmt = select(func.count(User.id)).where(User.status == UserStatus.WAITLIST)
        approved_stmt = select(func.count(User.id)).where(User.status == UserStatus.APPROVED)
        rejected_stmt = select(func.count(User.id)).where(User.status == UserStatus.REJECTED)
        suspended_stmt = select(func.count(User.id)).where(User.status == UserStatus.SUSPENDED)
        total_stmt = select(func.count(User.id))
        
        waitlist_count = (await db.execute(waitlist_stmt)).scalar()
        approved_count = (await db.execute(approved_stmt)).scalar()
        rejected_count = (await db.execute(rejected_stmt)).scalar()
        suspended_count = (await db.execute(suspended_stmt)).scalar()
        total_count = (await db.execute(total_stmt)).scalar()
        
        return {
            "success": True,
            "data": {
                "total_users": total_count,
                "waitlist": waitlist_count,
                "approved": approved_count,
                "rejected": rejected_count,
                "suspended": suspended_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get admin stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

