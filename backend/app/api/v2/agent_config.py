"""
Agent Configuration API
Allows users to dynamically configure LLM settings for individual agents
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from app.core.llm.config import LLMConfig, get_default_agent_configs
from app.core.llm.factory import LLMFactory

router = APIRouter()
logger = logging.getLogger(__name__)


class AgentLLMConfigRequest(BaseModel):
    """Request model for updating agent LLM configuration"""
    agent_name: str  # "manager", "dev_agent", "critic_agent", "tool_creation_agent"
    provider: str  # "gemini", "anthropic", "openai", "openrouter"
    model: str  # e.g., "gemini-3-pro-preview", "claude-sonnet-4", "gpt-4o"
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    extra_params: Optional[Dict[str, Any]] = None


class AgentLLMConfigResponse(BaseModel):
    """Response model for agent configuration"""
    success: bool
    message: str
    agent_name: str
    config: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.get("/agents/llm-configs")
async def get_agent_llm_configs():
    """
    Get current LLM configurations for all agents

    Returns:
        Dictionary mapping agent names to their LLM configurations
    """
    try:
        configs = get_default_agent_configs()

        return {
            "success": True,
            "configs": {
                agent_name: config.to_dict()
                for agent_name, config in configs.items()
            }
        }
    except Exception as e:
        logger.error(f"Error getting agent LLM configs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/llm-config/validate", response_model=AgentLLMConfigResponse)
async def validate_agent_llm_config(request: AgentLLMConfigRequest):
    """
    Validate an agent LLM configuration without applying it

    This endpoint allows users to test if their configuration is valid
    before actually using it in a workflow.
    """
    try:
        # Create LLMConfig from request
        config = LLMConfig(
            provider=request.provider,
            model=request.model,
            temperature=request.temperature or 0.1,
            max_tokens=request.max_tokens or 4096,
            extra_params=request.extra_params or {}
        )

        # Try to create the model (this will validate API keys, etc.)
        try:
            model = LLMFactory.create(config)
            model_type = type(model).__name__

            return AgentLLMConfigResponse(
                success=True,
                message=f"Configuration valid. Model type: {model_type}",
                agent_name=request.agent_name,
                config=config.to_dict()
            )
        except Exception as model_error:
            return AgentLLMConfigResponse(
                success=False,
                message="Configuration invalid",
                agent_name=request.agent_name,
                error=f"Failed to create model: {str(model_error)}"
            )

    except Exception as e:
        logger.error(f"Error validating config: {str(e)}")
        return AgentLLMConfigResponse(
            success=False,
            message="Validation failed",
            agent_name=request.agent_name,
            error=str(e)
        )


@router.get("/agents/available-models")
async def get_available_models():
    """
    Get list of available LLM models grouped by provider

    Returns:
        Dictionary of providers and their available models
    """
    import os

    available = {
        "providers": []
    }

    # Check which providers have API keys configured
    if os.getenv("GOOGLE_API_KEY"):
        available["providers"].append({
            "name": "gemini",
            "display_name": "Google Gemini",
            "models": [
                {"id": "gemini-3-pro-preview", "name": "Gemini 3 Pro (Preview)"},
                {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash (Experimental)"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"}
            ],
            "configured": True
        })

    if os.getenv("ANTHROPIC_API_KEY"):
        available["providers"].append({
            "name": "anthropic",
            "display_name": "Anthropic Claude",
            "models": [
                {"id": "claude-sonnet-4", "name": "Claude Sonnet 4"},
                {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
                {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus"}
            ],
            "configured": True
        })

    if os.getenv("OPENAI_API_KEY"):
        available["providers"].append({
            "name": "openai",
            "display_name": "OpenAI",
            "models": [
                {"id": "gpt-4o", "name": "GPT-4o"},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
                {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"}
            ],
            "configured": True
        })

    if os.getenv("OPENROUTER_API_KEY"):
        available["providers"].append({
            "name": "openrouter",
            "display_name": "OpenRouter",
            "models": [
                {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4 (via OpenRouter)"},
                {"id": "google/gemini-3-pro", "name": "Gemini 3 Pro (via OpenRouter)"},
                {"id": "openai/gpt-4o", "name": "GPT-4o (via OpenRouter)"}
            ],
            "configured": True
        })

    return available


@router.get("/agents/info")
async def get_agents_info():
    """
    Get information about all available agents

    Returns:
        List of agents with their roles and descriptions
    """
    return {
        "agents": [
            {
                "name": "manager",
                "display_name": "Manager Agent",
                "role": "coordinator",
                "description": "Coordinates and delegates tasks to specialized agents",
                "configurable": True
            },
            {
                "name": "dev_agent",
                "display_name": "Dev Agent",
                "role": "execution",
                "description": "Handles code execution, data analysis, and tool calling",
                "configurable": True
            },
            {
                "name": "critic_agent",
                "display_name": "Critic Agent",
                "role": "evaluation",
                "description": "Evaluates quality and provides feedback",
                "configurable": True
            },
            {
                "name": "tool_creation_agent",
                "display_name": "Tool Creation Agent",
                "role": "tool_creation",
                "description": "Creates and tests new tools dynamically",
                "configurable": True
            }
        ]
    }
