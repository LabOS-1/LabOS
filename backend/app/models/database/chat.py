"""
Chat project and message database models
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship

from app.core.infrastructure.database import Base
from app.models.enums import MessageRole


class ChatProject(Base):
    """Chat project model - direct conversation without sessions"""
    __tablename__ = "chat_projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(JSON, default=dict)
    
    # Direct relationships (no sessions)
    messages = relationship("ChatMessage", back_populates="project", cascade="all, delete-orphan")
    workflows = relationship("WorkflowExecution", back_populates="project", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Chat message model - directly belongs to project"""
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('chat_projects.id'), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, default=dict)  # Additional message data (files, etc.)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("ChatProject", back_populates="messages")
    workflows = relationship("WorkflowExecution", back_populates="trigger_message")

