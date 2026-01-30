# """
# Chat API - Endpoints for chat functionality
# """

# from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
# from pydantic import BaseModel
# from typing import List, Dict, Any, Optional
# from datetime import datetime
# import json
# import asyncio
# import re

# from app.services.labos_service import LabOSService

# router = APIRouter()

# # Dependency to get LabOS service
# async def get_labos_service() -> LabOSService:
#     # This would normally be injected, but for simplicity we'll create a global instance
#     if not hasattr(get_labos_service, "_instance"):
#         get_labos_service._instance = LabOSService()
#         await get_labos_service._instance.initialize()
#     return get_labos_service._instance

# class ChatMessageRequest(BaseModel):
#     message: str
#     workflow_id: str = None

# class ChatMessageResponse(BaseModel):
#     success: bool
#     data: Dict[str, Any] = None
#     error: str = None

# @router.post("/send", response_model=ChatMessageResponse)
# async def send_message(
#     request: ChatMessageRequest,
#     labos_service: LabOSService = Depends(get_labos_service)
# ):
#     """Send a message to LabOS AI (Async Processing)"""
#     try:
#         if not request.message.strip():
#             raise HTTPException(status_code=400, detail="Message cannot be empty")
        
#         # Generate workflow ID if not provided
#         import time
#         workflow_id = request.workflow_id or f"workflow_{int(time.time() * 1000)}"
        
#         # Start async processing (don't await - fire and forget)
#         import asyncio
#         asyncio.create_task(
#             labos_service.process_message_async(request.message, workflow_id)
#         )
        
#         # Return immediately with workflow ID
#         return ChatMessageResponse(
#             success=True,
#             data={
#                 "message": "Processing started",
#                 "workflow_id": workflow_id,
#                 "status": "processing",
#                 "note": "Results will be sent via WebSocket"
#             }
#         )
        
#     except Exception as e:
#         return ChatMessageResponse(
#             success=False,
#             error=str(e)
#         )

# @router.get("/history")
# async def get_chat_history(
#     labos_service: LabOSService = Depends(get_labos_service)
# ):
#     """Get chat history"""
#     try:
#         history = await labos_service.get_chat_history()
        
#         return {
#             "success": True,
#             "data": history
#         }
        
#     except Exception as e:
#         return {
#             "success": False,
#             "error": str(e)
#         }

# @router.delete("/history")
# async def clear_chat_history(
#     labos_service: LabOSService = Depends(get_labos_service)
# ):
#     """Clear chat history"""
#     try:
#         await labos_service.clear_chat_history()
        
#         return {
#             "success": True,
#             "message": "Chat history cleared successfully"
#         }
        
#     except Exception as e:
#         return {
#             "success": False,
#             "error": str(e)
#         }


# # WebSocket connection manager
# class ConnectionManager:
#     def __init__(self):
#         self.active_connections: List[WebSocket] = []

#     async def connect(self, websocket: WebSocket):
#         await websocket.accept()
#         self.active_connections.append(websocket)

#     def disconnect(self, websocket: WebSocket):
#         self.active_connections.remove(websocket)

#     async def send_personal_message(self, message: str, websocket: WebSocket):
#         await websocket.send_text(message)

#     async def broadcast(self, message: str):
#         for connection in self.active_connections:
#             try:
#                 await connection.send_text(message)
#             except:
#                 # Remove disconnected connections
#                 self.active_connections.remove(connection)

# manager = ConnectionManager()

# def parse_workflow_step(log_line: str) -> Optional[Dict[str, Any]]:
#     """Parse a single log line to extract workflow step information"""

#     # Debug: print all lines to see what we're missing
#     if "Step" in log_line or "Executing" in log_line or "HTTP Request" in log_line:
#         print(f"🔍 Parsing line: {log_line[:100]}...")

#     # Step pattern: ━━━ Step N ━━━
#     step_pattern = r'━+\s*Step\s+(\d+)\s*━+'
#     step_match = re.search(step_pattern, log_line)
#     if step_match:
#         step_info = {
#             "type": "step_start",
#             "step_number": int(step_match.group(1)),
#             "timestamp": datetime.now().isoformat()
#         }
#         print(f"✅ Parsed step_start: {step_info}")
#         return step_info

#     # Duration pattern: [Step N: Duration X.XX seconds| Input tokens: XXX | Output tokens: XXX]
#     duration_pattern = r'\[Step\s+(\d+):\s+Duration\s+([\d.]+)\s+seconds.*?Input\s+tokens:\s+([\d,]+).*?Output\s+tokens:\s+([\d,]+)\]'
#     duration_match = re.search(duration_pattern, log_line)
#     if duration_match:
#         step_info = {
#             "type": "step_complete",
#             "step_number": int(duration_match.group(1)),
#             "duration": float(duration_match.group(2)),
#             "input_tokens": int(duration_match.group(3).replace(',', '')),
#             "output_tokens": int(duration_match.group(4).replace(',', '')),
#             "timestamp": datetime.now().isoformat()
#         }
#         print(f"✅ Parsed step_complete: {step_info}")
#         return step_info

#     # Tool execution pattern: search_results = web_search(query="...")
#     tool_pattern = r'(\w+)\s*=\s*(\w+)\(([^)]*)\)'
#     tool_match = re.search(tool_pattern, log_line)
#     if tool_match:
#         step_info = {
#             "type": "tool_call",
#             "variable": tool_match.group(1),
#             "tool_name": tool_match.group(2),
#             "parameters": tool_match.group(3),
#             "timestamp": datetime.now().isoformat()
#         }
#         print(f"✅ Parsed tool_call: {step_info}")
#         return step_info

#     # Executing parsed code pattern
#     executing_pattern = r'─ Executing parsed code:'
#     if re.search(executing_pattern, log_line):
#         step_info = {
#             "type": "code_execution",
#             "description": "Executing parsed code",
#             "timestamp": datetime.now().isoformat()
#         }
#         print(f"✅ Parsed code_execution: {step_info}")
#         return step_info

#     # Command execution pattern: Command: conda create -n ml_bio_demo
#     command_pattern = r'Command:\s+(.+)'
#     command_match = re.search(command_pattern, log_line)
#     if command_match:
#         step_info = {
#             "type": "command_execution",
#             "command": command_match.group(1),
#             "timestamp": datetime.now().isoformat()
#         }
#         print(f"✅ Parsed command_execution: {step_info}")
#         return step_info

#     # HTTP Request pattern: INFO:httpx:HTTP Request: POST https://openrouter.ai/api/v1/chat/completions
#     http_pattern = r'INFO:httpx:HTTP\s+Request:\s+(\w+)\s+(https?://[^\s]+)'
#     http_match = re.search(http_pattern, log_line)
#     if http_match:
#         step_info = {
#             "type": "api_call",
#             "method": http_match.group(1),
#             "url": http_match.group(2),
#             "timestamp": datetime.now().isoformat()
#         }
#         print(f"✅ Parsed api_call: {step_info}")
#         return step_info

#     # Final answer pattern: final_answer("...")
#     final_pattern = r'final_answer\("([^"]*)"'
#     final_match = re.search(final_pattern, log_line)
#     if final_match:
#         step_info = {
#             "type": "final_answer",
#             "content": final_match.group(1)[:200] + "..." if len(final_match.group(1)) > 200 else final_match.group(1),
#             "timestamp": datetime.now().isoformat()
#         }
#         print(f"✅ Parsed final_answer: {step_info}")
#         return step_info

#     return None

# @router.websocket("/workflow")
# async def websocket_endpoint(websocket: WebSocket):
#     """WebSocket endpoint for real-time workflow updates"""
#     await manager.connect(websocket)
#     print(f"🔗 WebSocket client connected. Total connections: {len(manager.active_connections)}")

#     try:
#         # Send welcome message
#         await websocket.send_text(json.dumps({
#             "type": "connection_established",
#             "message": "WebSocket connected successfully"
#         }))

#         while True:
#             # Wait for messages from client or keep alive
#             try:
#                 data = await asyncio.wait_for(websocket.receive_text(), timeout=120.0)
#                 print(f"📨 Received WebSocket message: {data}")

#                 # Echo back for testing
#                 await websocket.send_text(json.dumps({
#                     "type": "echo",
#                     "original_message": data
#                 }))
#             except asyncio.TimeoutError:
#                 # Send keep-alive ping
#                 await websocket.send_text(json.dumps({
#                     "type": "ping",
#                     "timestamp": datetime.now().isoformat()
#                 }))

#     except WebSocketDisconnect:
#         print(f"🔌 WebSocket client disconnected")
#         manager.disconnect(websocket)
#     except Exception as e:
#         print(f"❌ WebSocket error: {e}")
#         manager.disconnect(websocket)
