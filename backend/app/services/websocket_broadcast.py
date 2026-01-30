"""
WebSocket broadcast service - For sending real-time updates to connected clients with room isolation
"""

import json
import asyncio
import logging
from typing import Set, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger('labos.websocket')

class WebSocketBroadcaster:
    """WebSocket broadcaster with room-based isolation"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        # Map project_id -> set of websockets subscribed to that project
        self.project_rooms: Dict[str, Set[WebSocket]] = {}
        # Map websocket -> set of project_ids it's subscribed to
        self.socket_subscriptions: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket):
        """Add WebSocket connection"""
        # No need to accept again, as websocket_manager has already accepted
        self.active_connections.add(websocket)
        self.socket_subscriptions[websocket] = set()
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def subscribe_to_project(self, websocket: WebSocket, project_id: str):
        """Subscribe a websocket to a specific project room"""
        if project_id not in self.project_rooms:
            self.project_rooms[project_id] = set()

        self.project_rooms[project_id].add(websocket)

        if websocket in self.socket_subscriptions:
            self.socket_subscriptions[websocket].add(project_id)

        logger.info(f"WebSocket subscribed to project {project_id}. Room size: {len(self.project_rooms[project_id])}")

    def unsubscribe_from_project(self, websocket: WebSocket, project_id: str):
        """Unsubscribe a websocket from a specific project room"""
        if project_id in self.project_rooms:
            self.project_rooms[project_id].discard(websocket)
            if not self.project_rooms[project_id]:
                del self.project_rooms[project_id]

        if websocket in self.socket_subscriptions:
            self.socket_subscriptions[websocket].discard(project_id)

        logger.info(f"WebSocket unsubscribed from project {project_id}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection and clean up all subscriptions"""
        self.active_connections.discard(websocket)

        # Remove from all project rooms
        if websocket in self.socket_subscriptions:
            for project_id in self.socket_subscriptions[websocket]:
                if project_id in self.project_rooms:
                    self.project_rooms[project_id].discard(websocket)
                    if not self.project_rooms[project_id]:
                        del self.project_rooms[project_id]
            del self.socket_subscriptions[websocket]

        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[Any, Any]):
        """
        Broadcast message to connected clients
        - If message has project_id: send only to clients subscribed to that project
        - Otherwise: send to all connected clients (for backward compatibility)
        """
        message_type = message.get('type', 'unknown')
        project_id = message.get('project_id')

        # Determine target connections
        if project_id and project_id in self.project_rooms:
            # Send to project room only
            target_connections = self.project_rooms[project_id]
            logger.debug(f"Broadcasting {message_type} to project {project_id} ({len(target_connections)} clients)")
        else:
            # Send to all connections (for messages without project_id)
            target_connections = self.active_connections
            logger.debug(f"Broadcasting {message_type} to all connections ({len(target_connections)} clients)")

        if not target_connections:
            logger.debug(f"No target connections for message type: {message_type}")
            return

        message_str = json.dumps(message)
        disconnected = set()

        for connection in target_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning(f"Failed to send {message_type} to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        if disconnected:
            for connection in disconnected:
                self.disconnect(connection)
            logger.info(f"Cleaned up {len(disconnected)} disconnected clients")
    
    async def send_workflow_step(self, workflow_id: str, step_data: Dict[Any, Any], project_id: str = None):
        """Send workflow step update"""
        message = {
            "type": "workflow_step",
            "workflow_id": workflow_id,
            "step_type": step_data.get("step_type", "thinking"),
            "title": step_data.get("title"),
            "description": step_data.get("description"),
            "tool_name": step_data.get("tool_name"),
            "tool_result": step_data.get("tool_result"),
            "step_number": step_data.get("step_number"),
            "observations": step_data.get("observations", []),
            "timestamp": step_data.get("timestamp")
        }

        # Include project_id for user isolation
        if project_id:
            message["project_id"] = project_id

        # Include step_metadata if present (for visualizations, etc.)
        if "step_metadata" in step_data and step_data["step_metadata"]:
            message["step_metadata"] = step_data["step_metadata"]
            logger.debug(f"Including step_metadata for workflow {workflow_id}")

        await self.broadcast(message)
    
    async def send_workflow_progress(self, workflow_id: str, progress: float, current_step: int = 0, total_steps: int = 0, is_processing: bool = True, project_id: str = None):
        """Send workflow progress update"""
        message = {
            "type": "workflow_progress",
            "workflow_id": workflow_id,
            "progress": progress,
            "current_step": current_step,
            "total_steps": total_steps,
            "is_processing": is_processing
        }
        if project_id:
            message["project_id"] = project_id  # Include project_id for user isolation
        await self.broadcast(message)

    def get_connection_count(self) -> int:
        """Get current connection count"""
        return len(self.active_connections)

# Global broadcaster instance
websocket_broadcaster = WebSocketBroadcaster()
