"""
File database model
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, LargeBinary, BigInteger, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship

from app.core.infrastructure.database import Base
from app.models.enums import FileType, FileStatus


class ProjectFile(Base):
    """Project file model - follows same pattern as ChatMessage"""
    __tablename__ = "project_files"
    
    # Primary key and associations - consistent with ChatMessage pattern
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('chat_projects.id'), nullable=True)  # Can be null for global files
    user_id = Column(String(255), nullable=False, index=True)  # Direct user isolation, consistent with ChatProject
    
    # Basic file information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    content_type = Column(String(100))
    file_hash = Column(String(64))  # SHA256 for deduplication
    
    # Storage strategy - choose based on size
    file_data = Column(LargeBinary)  # Small files directly in DB (<1MB)
    storage_path = Column(Text)      # Large file storage path
    storage_provider = Column(String(20), default='database')  # 'database', 'local', 'cloud'
    
    # Classification and tags - use JSON, consistent with existing settings field
    file_type = Column(Enum(FileType), nullable=False)
    category = Column(String(50))  # 'document', 'data', 'image', 'code', 'report'
    tags = Column(JSON, default=list)
    file_metadata = Column(JSON, default=dict)  # Consistent with message_metadata naming
    
    # Agent related
    created_by_agent = Column(String(100))  # 'user', 'manager_agent', 'dev_agent'
    workflow_id = Column(String(255))  # Link to workflow
    message_id = Column(UUID(as_uuid=True), ForeignKey('chat_messages.id'), nullable=True)  # Link to message
    
    # Status management
    status = Column(Enum(FileStatus), default=FileStatus.ACTIVE, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    
    # Timestamps - consistent with existing tables
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    # Relationship definitions - consistent with existing pattern
    project = relationship("ChatProject", backref="files")
    message = relationship("ChatMessage", backref="attached_files")

