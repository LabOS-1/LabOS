"""
File-related Pydantic schemas
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class ProjectFileResponse(BaseModel):
    """Project file response model"""
    id: str
    filename: str
    original_filename: str
    file_size: int
    content_type: Optional[str]
    file_type: str
    category: Optional[str]
    tags: List[str]
    created_by_agent: Optional[str]
    status: str
    is_public: bool
    created_at: datetime
    updated_at: datetime
    project_id: Optional[str]
    
    class Config:
        from_attributes = True

