"""
System API - Endpoints for system management and monitoring
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.services.labos_service import LabOSService

router = APIRouter()

async def get_labos_service() -> LabOSService:
    if not hasattr(get_labos_service, "_instance"):
        get_labos_service._instance = LabOSService()
        await get_labos_service._instance.initialize()
    return get_labos_service._instance

@router.get("/status")
async def get_system_status(
    labos_service: LabOSService = Depends(get_labos_service)
):
    """Get comprehensive system status"""
    try:
        status = await labos_service.get_system_status()
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/health")
async def get_system_health(
    labos_service: LabOSService = Depends(get_labos_service)
):
    """Get basic system health check"""
    try:
        import time
        
        health = {
            "status": "healthy",
            "uptime": time.time() - labos_service.system_stats["uptime_start"],
            "stella_initialized": labos_service.is_initialized(),
            "timestamp": time.time()
        }
        
        return {
            "success": True,
            "data": health
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
