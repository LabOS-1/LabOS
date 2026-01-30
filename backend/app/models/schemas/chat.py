"""
Chat-related Pydantic schemas
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.models.enums import MessageRole


class ChatProjectResponse(BaseModel):
    """Chat project response model"""
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    message_count: int

    class Config:
        from_attributes = True
        json_encoders = {
            # Ensure datetime is serialized as ISO 8601 with 'Z' suffix for UTC
            datetime: lambda v: v.isoformat() + 'Z' if v else None
        }


class ChatMessageResponse(BaseModel):
    """Chat message response model"""
    id: str
    role: MessageRole
    content: str
    message_metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            # Ensure datetime is serialized as ISO 8601 with 'Z' suffix for UTC
            datetime: lambda v: v.isoformat() + 'Z' if v else None
        }

