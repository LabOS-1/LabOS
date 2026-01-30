"""
LangChain Chat API
New chat endpoint using LangChain engine instead of Smolagents
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.engines.langchain.langchain_engine import (
    initialize_langchain_labos,
    run_query,
    get_agent_info,
    langchain_agent
)
from app.core.engines.langchain.langchain_websocket_callback import LangChainWebSocketCallback
from app.services.workflows.workflow_event_listener import start_workflow_listener, stop_workflow_listener
from app.services.workflows.workflow_events import workflow_event_queue

router = APIRouter()
logger = logging.getLogger(__name__)

# Track initialization state
_initialized = False


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    query: str
    conversation_history: Optional[List] = None
    model_type: Optional[str] = "gemini"  # "gemini", "claude", or "gpt"
    project_id: Optional[str] = None  # For WebSocket room isolation
    use_websocket: Optional[bool] = False  # Enable WebSocket streaming


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    output: str
    success: bool
    steps: Optional[List] = None
    error: Optional[str] = None
    agent_info: Optional[dict] = None
    workflow_id: Optional[str] = None  # Returned when use_websocket=True


@router.post("/chat", response_model=ChatResponse)
async def langchain_chat(request: ChatRequest):
    """
    Chat endpoint using LangChain engine

    This is the new endpoint that uses LangChain + direct API calls (Gemini/Claude/GPT)
    instead of Smolagents + OpenRouter
    """
    global _initialized

    try:
        # Initialize agent if not already initialized
        if not _initialized:
            logger.info(f"Initializing LangChain agent with model: {request.model_type}")
            success = initialize_langchain_labos(
                model_type=request.model_type,
                verbose=False  # Don't print verbose output in API
            )

            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to initialize LangChain agent"
                )

            _initialized = True
            logger.info("✅ LangChain agent initialized")

        # Run query
        logger.info(f"Processing query: {request.query[:100]}...")

        # Create callback handler if WebSocket streaming is enabled
        callbacks = None
        workflow_id = None
        listener_task = None

        if request.use_websocket:
            # Generate unique workflow ID
            workflow_id = str(uuid.uuid4())

            # Register workflow as active in the queue
            workflow_event_queue.register_workflow(workflow_id)

            # Start event listener FIRST (it will monitor the queue and broadcast events)
            listener_task = await start_workflow_listener(
                workflow_id=workflow_id,
                project_id=request.project_id
            )
            logger.info(f"📡 Event listener started for workflow: {workflow_id}")

            # Create WebSocket callback handler (it will put events in the queue)
            ws_callback = LangChainWebSocketCallback(
                workflow_id=workflow_id,
                project_id=request.project_id
            )
            callbacks = [ws_callback]

            logger.info(f"✅ WebSocket streaming enabled. Workflow ID: {workflow_id}")
            logger.info(f"✅ Callback handler created: {ws_callback}")
            logger.info(f"✅ Project ID: {request.project_id}")

        try:
            # Run query with callbacks if enabled
            # If WebSocket is enabled, run in thread executor so listener can run concurrently
            if request.use_websocket:
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(
                        executor,
                        lambda: run_query(
                            query=request.query,
                            conversation_history=request.conversation_history,
                            callbacks=callbacks
                        )
                    )
            else:
                # No WebSocket, run synchronously
                result = run_query(
                    query=request.query,
                    conversation_history=request.conversation_history,
                    callbacks=callbacks
                )
        finally:
            # Stop event listener if it was started
            if listener_task:
                logger.info(f"🛑 Stopping event listener for workflow: {workflow_id}")
                await stop_workflow_listener(listener_task)
                workflow_event_queue.unregister_workflow(workflow_id)
                logger.info(f"📡 Event listener stopped for workflow: {workflow_id}")

        # Get agent info
        agent_info = get_agent_info()

        return ChatResponse(
            output=result.get("output", ""),
            success=result.get("success", False),
            steps=result.get("steps", []),
            error=result.get("error"),
            agent_info=agent_info,
            workflow_id=workflow_id
        )

    except Exception as e:
        logger.error(f"Error in LangChain chat: {str(e)}")
        import traceback
        traceback.print_exc()

        return ChatResponse(
            output="",
            success=False,
            error=str(e)
        )


@router.get("/status")
async def langchain_status():
    """Get LangChain agent status"""
    agent_info = get_agent_info()

    return {
        "initialized": _initialized,
        "agent_info": agent_info,
        "available_models": ["gemini", "claude", "gpt"]
    }


@router.post("/reinitialize")
async def reinitialize_agent(model_type: str = "gemini"):
    """Reinitialize agent with a different model"""
    global _initialized

    try:
        logger.info(f"Reinitializing LangChain agent with model: {model_type}")

        success = initialize_langchain_labos(
            model_type=model_type,
            verbose=False
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to reinitialize agent with model: {model_type}"
            )

        _initialized = True
        agent_info = get_agent_info()

        return {
            "success": True,
            "message": f"Agent reinitialized with {model_type}",
            "agent_info": agent_info
        }

    except Exception as e:
        logger.error(f"Error reinitializing agent: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
