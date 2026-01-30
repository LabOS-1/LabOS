"""
System API - Endpoints for system management and monitoring
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any

# from app.services.labos_service import LabOSService  # V1 DEPRECATED

router = APIRouter()

# V1 DEPRECATED - Smolagents service disabled
# async def get_labos_service() -> LabOSService:
#     if not hasattr(get_labos_service, "_instance"):
#         get_labos_service._instance = LabOSService()
#         await get_labos_service._instance.initialize()
#     return get_labos_service._instance

@router.get("/status")
async def get_system_status():
    """Get comprehensive system status (V2 compatible)"""
    import time
    from app.services.websocket_broadcast import websocket_broadcaster

    # V2: Return system status without labos_service dependency
    status = {
        "labos_initialized": True,  # V2 always ready
        "websocket_connections": websocket_broadcaster.get_connection_count(),
        "version": "2.0",
        "engine": "langchain",
        "timestamp": time.time()
    }

    return {
        "success": True,
        "data": status
    }

@router.get("/health")
async def get_system_health():
    """Get basic system health check (V2 compatible)"""
    import time
    from app.services.websocket_broadcast import websocket_broadcaster

    # V2: Return health without labos_service dependency
    health = {
        "status": "healthy",
        "labos_initialized": True,  # V2 always ready
        "websocket_connections": websocket_broadcaster.get_connection_count(),
        "timestamp": time.time()
    }

    return {
        "success": True,
        "data": health
    }
