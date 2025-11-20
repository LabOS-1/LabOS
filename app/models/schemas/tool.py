"""
Tool schemas for API requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class ToolParameter(BaseModel):
    """Tool parameter definition"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolCreate(BaseModel):
    """Schema for creating a new tool"""
    name: str = Field(..., description="Tool function name")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    description: str = Field(..., description="Tool description")
    category: str = Field("general", description="Tool category")
    tool_code: str = Field(..., description="Python code for the tool")
    parameters: List[ToolParameter] = Field(default_factory=list)
    return_type: Optional[str] = Field(None, description="Return type description")
    examples: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    tool_metadata: Dict[str, Any] = Field(default_factory=dict)
    project_id: Optional[UUID] = None
    workflow_id: Optional[str] = None
    message_id: Optional[UUID] = None


class ToolUpdate(BaseModel):
    """Schema for updating a tool"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tool_code: Optional[str] = None
    parameters: Optional[List[ToolParameter]] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None


class ToolResponse(BaseModel):
    """Schema for tool response"""
    id: UUID
    name: str
    display_name: Optional[str]
    description: str
    category: str
    parameters: List[Dict[str, Any]]
    return_type: Optional[str]
    examples: List[str]
    dependencies: List[str]
    usage_count: int
    last_used_at: Optional[datetime]
    success_count: int
    error_count: int
    version: str
    status: str
    is_public: bool
    is_verified: bool
    created_by_agent: Optional[str]
    created_at: datetime
    updated_at: datetime
    project_id: Optional[UUID]

    class Config:
        from_attributes = True


class ToolListResponse(BaseModel):
    """Schema for listing tools"""
    tools: List[ToolResponse]
    total: int
    page: int
    page_size: int