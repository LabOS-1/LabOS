"""
Workflow execution database models
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship

from app.core.infrastructure.database import Base
from app.models.enums import WorkflowStatus, StepStatus


class WorkflowExecution(Base):
    """Workflow execution model - tracks AI workflow runs, directly belongs to project"""
    __tablename__ = "workflow_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('chat_projects.id'), nullable=False)
    message_id = Column(UUID(as_uuid=True), ForeignKey('chat_messages.id'), nullable=True)
    workflow_id = Column(String(255), nullable=False)  # Internal workflow identifier
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.RUNNING, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    result = Column(JSON)  # Workflow execution result
    
    # Relationships
    project = relationship("ChatProject", back_populates="workflows")
    trigger_message = relationship("ChatMessage", back_populates="workflows")
    steps = relationship("WorkflowStep", back_populates="execution", cascade="all, delete-orphan")


class WorkflowStep(Base):
    """Individual workflow step model"""
    __tablename__ = "workflow_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey('workflow_executions.id'), nullable=False)
    step_index = Column(Integer, nullable=False)
    type = Column(String(100), nullable=False)  # 'manager_start', 'agent_execution', etc.
    title = Column(String(255))
    description = Column(Text)
    status = Column(Enum(StepStatus), default=StepStatus.PENDING, nullable=False)
    
    # Legacy fields (keep for backward compatibility)
    tool_name = Column(String(255))
    tool_result = Column(JSON)
    
    # New Agent-aware fields
    agent_name = Column(String(100), nullable=True)      # Which agent executed this step
    agent_task = Column(Text, nullable=True)             # Task given to the agent
    tools_used = Column(JSON, default=list)             # Array of tool executions
    execution_result = Column(Text, nullable=True)      # Agent's final result
    execution_duration = Column(Float, nullable=True)   # Duration in seconds
    step_metadata = Column(JSON, default=dict)          # Extended metadata for visualizations, code, etc.
    
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    
    # Relationships
    execution = relationship("WorkflowExecution", back_populates="steps")

