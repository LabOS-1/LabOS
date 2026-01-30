"""
WebSocket endpoints for real-time workflow updates
"""

import asyncio
import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.workflows import workflow_service
from app.services.websocket_broadcast import websocket_broadcaster

router = APIRouter()

# Removed unused ConnectionManager - using websocket_broadcaster directly

@router.websocket("/ws")
async def websocket_general_endpoint(websocket: WebSocket):
    """General WebSocket endpoint - for frontend connections"""
    await websocket.accept()  # Accept the WebSocket connection first
    await websocket_broadcaster.connect(websocket)

    try:
        while True:
            # Keep connection alive, listen for messages
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different types of messages
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": message.get("timestamp"),
                    "workflow_id": message.get("workflow_id")
                }))
                print(f"📤 Sent pong response for workflow: {message.get('workflow_id')}")
            elif message.get("type") == "subscribe_project":
                # Subscribe to project-specific messages
                project_id = message.get("project_id")
                if project_id:
                    websocket_broadcaster.subscribe_to_project(websocket, project_id)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "project_id": project_id
                    }))
                    print(f"📌 Client subscribed to project: {project_id}")
            elif message.get("type") == "unsubscribe_project":
                # Unsubscribe from project
                project_id = message.get("project_id")
                if project_id:
                    websocket_broadcaster.unsubscribe_from_project(websocket, project_id)
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "project_id": project_id
                    }))
                    print(f"📌 Client unsubscribed from project: {project_id}")
            elif message.get("type") == "subscribe_workflow":
                workflow_id = message.get("workflow_id")
                if workflow_id:
                    # Send workflow status
                    steps = workflow_service.get_workflow_steps(workflow_id)
                    progress = workflow_service.get_workflow_progress(workflow_id)

                    await websocket.send_text(json.dumps({
                        "type": "workflow_status",
                        "workflow_id": workflow_id,
                        "steps": [step.dict() for step in steps],
                        "progress": progress
                    }))

    except WebSocketDisconnect:
        websocket_broadcaster.disconnect(websocket)
        print("🔌 General WebSocket disconnected")
    except Exception as e:
        websocket_broadcaster.disconnect(websocket)
        print(f"❌ General WebSocket error: {e}")

# Removed unused workflow-specific WebSocket endpoint - frontend uses general /ws endpoint

# HTTP endpoint for testing
@router.post("/workflow/{workflow_id}/test")
async def test_workflow_updates(workflow_id: str):
    """Test workflow updates (for development only)"""
    from app.services.workflows import WorkflowStep, WorkflowStepType, WorkflowStepStatus
    
    # Create workflow
    workflow_service.create_workflow(workflow_id)
    
    # Add test step
    step1 = WorkflowStep(
        id=f"{workflow_id}_test_1",
        type=WorkflowStepType.THINKING,
        title="Test Thinking Step",
        description="This is a test step",
        status=WorkflowStepStatus.RUNNING
    )
    
    await workflow_service.add_step(workflow_id, step1)
    await workflow_service.update_progress(workflow_id, 25)
    
    # Simulate step completion
    await asyncio.sleep(1)
    await workflow_service.update_step(
        workflow_id, 
        step1.id, 
        status=WorkflowStepStatus.COMPLETED
    )
    
    # Add tool call step
    step2 = WorkflowStep(
        id=f"{workflow_id}_test_2",
        type=WorkflowStepType.TOOL_CALL,
        title="Test Tool Call",
        description="Call search tool",
        status=WorkflowStepStatus.RUNNING,
        tool_name="search_arxiv_papers",
        tool_params={"query": "test", "max_results": 5}
    )
    
    await workflow_service.add_step(workflow_id, step2)
    await workflow_service.update_progress(workflow_id, 50)
    
    # Simulate tool execution
    await asyncio.sleep(2)
    await workflow_service.update_step(
        workflow_id,
        step2.id,
        status=WorkflowStepStatus.COMPLETED,
        tool_result="Search completed, found 5 papers"
    )
    
    await workflow_service.update_progress(workflow_id, 100)
    await workflow_service.complete_workflow(workflow_id)
    
    return {"success": True, "message": f"Test workflow {workflow_id} completed"}

@router.get("/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get workflow status"""
    steps = workflow_service.get_workflow_steps(workflow_id)
    progress = workflow_service.get_workflow_progress(workflow_id)
    
    return {
        "success": True,
        "data": {
            "workflow_id": workflow_id,
            "steps": steps,
            "progress": progress,
            "active_connections": websocket_broadcaster.get_connection_count()
        }
    }

@router.delete("/workflow/{workflow_id}")
async def cleanup_workflow(workflow_id: str):
    """Clean up workflow"""
    workflow_service.cleanup_workflow(workflow_id)
    
    # Notify all connected clients that workflow has been cleaned up
    await websocket_broadcaster.broadcast({
        "type": "workflow_cleaned",
        "workflow_id": workflow_id
    })
    
    return {"success": True, "message": f"Workflow {workflow_id} cleaned up"}
