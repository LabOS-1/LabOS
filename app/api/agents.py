"""
Agents API - Endpoints for agent management
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

@router.get("")
async def get_agents(
    labos_service: LabOSService = Depends(get_labos_service)
):
    """Get all agents and their status"""
    try:
        agents = await labos_service.get_agents()
        
        return {
            "success": True,
            "data": agents
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/{agent_id}/status")
async def get_agent_status(
    agent_id: str,
    labos_service: LabOSService = Depends(get_labos_service)
):
    """Get specific agent status"""
    try:
        agents = await labos_service.get_agents()
        
        if agent_id not in agents:
            return {
                "success": False,
                "error": f"Agent {agent_id} not found"
            }
            
        return {
            "success": True,
            "data": agents[agent_id]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/reset")
async def reset_agents(
    labos_service: LabOSService = Depends(get_labos_service)
):
    """Reset all agents"""
    try:
        await labos_service.reset_agents()
        
        return {
            "success": True,
            "message": "Agents reset successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
