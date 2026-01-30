"""
User-related Pydantic schemas
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.models.enums import UserStatus


class UserResponse(BaseModel):
    """User response model for admin endpoints"""
    id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    status: UserStatus
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    institution: Optional[str] = None
    research_field: Optional[str] = None
    application_reason: Optional[str] = None
    email_verified: bool
    auth0_metadata: Dict[str, Any]

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """User update request model"""
    name: Optional[str] = None
    status: Optional[UserStatus] = None
    is_admin: Optional[bool] = None
    institution: Optional[str] = None
    research_field: Optional[str] = None
    application_reason: Optional[str] = None
    rejection_reason: Optional[str] = None

