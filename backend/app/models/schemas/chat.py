"""
Chat-related Pydantic schemas
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.models.enums import MessageRole


class ChatSessionResponse(BaseModel):
    """Chat session response model"""
    id: str
    project_id: str
    name: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v else None
        }


class ChatSessionCreate(BaseModel):
    """Create chat session request"""
    name: str = "New Chat"


class ChatProjectResponse(BaseModel):
    """Chat project response model"""
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    session_count: int = 0
    sessions: List[ChatSessionResponse] = []

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v else None
        }


class ChatMessageResponse(BaseModel):
    """Chat message response model"""
    id: str
    session_id: str
    role: MessageRole
    content: str
    message_metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v else None
        }
