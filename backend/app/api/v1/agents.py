"""
Agents API - Endpoints for agent management

DEPRECATED: V1 Smolagents-based agent management has been replaced by V2 LangChain Multi-Agent System.
These endpoints return deprecation notices. Use V2 API instead.
"""

from fastapi import APIRouter
from typing import Dict, Any

# from app.services.labos_service import LabOSService  # V1 DEPRECATED - Smolagents engine disabled

router = APIRouter()

# V1 Smolagents service disabled - endpoints return deprecation notice

@router.get("")
async def get_agents():
    """Get all agents and their status - DEPRECATED"""
    return {
        "success": False,
        "error": "V1 Smolagents API is deprecated. Please use V2 LangChain Multi-Agent System.",
        "message": "This endpoint has been replaced by V2 API. V1 Smolagents engine has been disabled."
    }

@router.get("/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get specific agent status - DEPRECATED"""
    return {
        "success": False,
        "error": "V1 Smolagents API is deprecated. Please use V2 LangChain Multi-Agent System.",
        "message": "This endpoint has been replaced by V2 API. V1 Smolagents engine has been disabled."
    }

@router.post("/reset")
async def reset_agents():
    """Reset all agents - DEPRECATED"""
    return {
        "success": False,
        "error": "V1 Smolagents API is deprecated. Please use V2 LangChain Multi-Agent System.",
        "message": "This endpoint has been replaced by V2 API. V1 Smolagents engine has been disabled."
    }
