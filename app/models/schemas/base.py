"""
Base Pydantic schemas
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response model"""
    success: bool
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = False
    error: str
    error_code: Optional[str] = None


class SuccessResponse(BaseResponse):
    """Success response model"""
    success: bool = True
    data: Any

