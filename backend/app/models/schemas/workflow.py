"""
Workflow-related Pydantic schemas
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.models.enums import WorkflowStatus, StepStatus

# New tool execution schema
class ToolExecution(BaseModel):
    name: str
    args: Dict[str, Any]
    result: str
    duration: Optional[float] = None
    status: str = "success"  # "success" | "error"
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Extended step metadata schema
class StepMetadata(BaseModel):
    visualizations: Optional[List[Dict[str, Any]]] = None
    code_blocks: Optional[List[Dict[str, str]]] = None
    files_created: Optional[List[str]] = None
    performance_metrics: Optional[Dict[str, Any]] = None


class WorkflowStepResponse(BaseModel):
    """Workflow step response model"""
    id: str
    step_index: int
    type: str
    title: Optional[str]
    description: Optional[str]
    status: StepStatus
    
    # Legacy fields (for backward compatibility)
    tool_name: Optional[str]
    tool_result: Optional[Dict[str, Any]]
    
    # New Agent-aware fields
    agent_name: Optional[str] = None
    agent_task: Optional[str] = None
    tools_used: Optional[List[ToolExecution]] = None
    execution_result: Optional[str] = None
    execution_duration: Optional[float] = None
    step_metadata: Optional[StepMetadata] = None
    
    started_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class WorkflowExecutionResponse(BaseModel):
    """Workflow execution response model"""
    id: str
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime]
    steps: List[WorkflowStepResponse]
    
    class Config:
        from_attributes = True

