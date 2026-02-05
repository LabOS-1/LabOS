"""
Tool database model
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship

from app.core.infrastructure.database import Base


class ToolStatus:
    """Tool status enum"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ERROR = "error"


class ProjectTool(Base):
    """Project tool model - stores dynamically created tools for each project"""
    __tablename__ = "project_tools"

    # Primary key and associations
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('chat_projects.id'), nullable=True)  # Can be null for global tools
    user_id = Column(String(255), nullable=False, index=True)  # User who created/owns the tool

    # Basic tool information
    name = Column(String(255), nullable=False)  # Tool function name (e.g., "analyze_protein_sequence")
    display_name = Column(String(255))  # Human-readable name
    description = Column(Text, nullable=False)  # Tool description
    category = Column(String(50))  # 'data_analysis', 'visualization', 'file_processing', etc.

    # Tool code and implementation
    tool_code = Column(Text, nullable=False)  # The actual Python code
    code_hash = Column(String(64))  # SHA256 hash for deduplication and version tracking

    # Tool metadata
    parameters = Column(JSON, default=list)  # List of parameter definitions
    return_type = Column(String(100))  # Return type description
    examples = Column(JSON, default=list)  # Usage examples
    dependencies = Column(JSON, default=list)  # Required Python packages
    tool_metadata = Column(JSON, default=dict)  # Additional metadata

    # Agent and workflow tracking
    created_by_agent = Column(String(100))  # 'tool_creation_agent', 'user', etc.
    workflow_id = Column(String(255))  # Link to workflow that created this tool
    message_id = Column(UUID(as_uuid=True), ForeignKey('chat_messages.id'), nullable=True)  # Link to message

    # Usage statistics
    usage_count = Column(Integer, default=0)  # How many times the tool has been used
    last_used_at = Column(DateTime)  # When it was last used
    success_count = Column(Integer, default=0)  # Successful executions
    error_count = Column(Integer, default=0)  # Failed executions

    # Version control
    version = Column(String(20), default="1.0.0")  # Semantic versioning
    parent_tool_id = Column(UUID(as_uuid=True), ForeignKey('project_tools.id'), nullable=True)  # For tool updates/forks

    # Status management
    status = Column(String(20), default=ToolStatus.ACTIVE, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)  # Can be shared across projects
    is_verified = Column(Boolean, default=False)  # Admin-verified tool

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships (tools now stored in sandbox, project relationship removed)
    message = relationship("ChatMessage", backref="created_tools")
    parent_tool = relationship("ProjectTool", remote_side=[id], backref="versions")