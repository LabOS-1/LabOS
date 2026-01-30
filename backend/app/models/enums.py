"""
Unified Enums for LABOS Backend
All enum types used across database models and API schemas
"""

import enum


class UserStatus(str, enum.Enum):
    """User account status for waitlist/approval system"""
    WAITLIST = "waitlist"        # Waiting for approval
    APPROVED = "approved"        # Approved to use the system
    REJECTED = "rejected"        # Access denied
    SUSPENDED = "suspended"      # Temporarily suspended


class MessageRole(str, enum.Enum):
    """Message role in chat conversations"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class WorkflowStatus(str, enum.Enum):
    """Workflow execution status"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, enum.Enum):
    """Individual workflow step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, enum.Enum):
    """File type classification"""
    USER_UPLOAD = "user_upload"
    AGENT_GENERATED = "agent_generated"
    PROCESSED = "processed"
    TEMPORARY = "temporary"


class FileStatus(str, enum.Enum):
    """File status in the system"""
    ACTIVE = "active"
    PROCESSING = "processing"
    ARCHIVED = "archived"
    DELETED = "deleted"


class WorkflowStepType(str, enum.Enum):
    """Types of workflow steps (for API schemas)"""
    # New Agent-aware types
    MANAGER_START = "manager_start"
    AGENT_EXECUTION = "agent_execution"
    MANAGER_SYNTHESIS = "manager_synthesis"
    WORKFLOW_COMPLETE = "workflow_complete"
    
    # Legacy types (for backward compatibility)
    THINKING = "thinking"
    TOOL_EXECUTION = "tool_execution"
    API_CALL = "api_call"
    SYNTHESIS = "synthesis"
    STEP_COMPLETE = "step_complete"

