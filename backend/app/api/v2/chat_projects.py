"""
LangChain V2 Chat Projects API
Handles project-based conversations with chat history and workflow persistence
"""

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import logging
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.engines.langchain.langchain_engine import (
    initialize_langchain_labos,
    run_query,
    langchain_agent
)
from app.core.engines.langchain.multi_agent_system import (
    initialize_multi_agent_system,
    run_multi_agent_query,
    get_multi_agent_system,
    _register_agents_to_system,
    MultiAgentSystem
)
from app.core.llm.config import get_default_agent_configs, merge_agent_configs
from app.core.engines.langchain.langchain_websocket_callback import LangChainWebSocketCallback
from app.services.workflows.workflow_event_listener import start_workflow_listener, stop_workflow_listener
from app.services.workflows.workflow_events import workflow_event_queue
from app.services.workflows.workflow_database import WorkflowDatabase
from app.models.database.chat import ChatMessage, MessageRole, ChatProject
from app.core.infrastructure.database import get_db_session
from app.api.v1.auth import get_current_user_id
from app.core.infrastructure.cloud_logging import set_log_context
from app.services.sandbox import get_sandbox_manager

router = APIRouter()
logger = logging.getLogger(__name__)

# Track initialization state
_initialized = False
_multi_agent_initialized = False


# ============================================================================
# Shared function for processing messages with AI agent
# ============================================================================
async def process_message_with_agent(
    user_id: str,
    project_id: str,
    message_content: str,
    use_multi_agent: bool,
    mode: str,
    db: AsyncSession,
    user_message_id: uuid.UUID,
    attached_file: Optional[dict] = None,
    attached_files: Optional[List[dict]] = None,
    agent_configs: Optional[Dict[str, Dict[str, Any]]] = None
):
    """
    Process a message (with optional file(s)) using the AI agent system.

    This function handles:
    - Initializing the agent system (if needed)
    - Loading chat history
    - Running the agent with workflow tracking
    - Saving the response

    Args:
        user_id: User ID
        project_id: Project ID
        message_content: The message text
        use_multi_agent: Whether to use multi-agent system
        mode: Agent mode ("fast" or "deep")
        db: Database session
        user_message_id: ID of the saved user message
        attached_file: Optional dict with file info {"file_id": str, "filename": str} (legacy single file)
        attached_files: Optional list of file dicts [{"file_id": str, "filename": str, "content_type": str}, ...]
        agent_configs: Optional agent LLM configurations from frontend
            Example: {"manager": {"provider": "anthropic", "model": "claude-sonnet-4"}}

    Returns:
        Dict with workflow_id and success status
    """
    global _initialized, _multi_agent_initialized

    # ===== NEW: Merge agent configs =====
    # 1. Load default configs from environment variables
    default_configs = get_default_agent_configs()

    # 2. Merge with user-provided overrides (if any)
    final_configs = merge_agent_configs(default_configs, agent_configs)

    logger.info(f"[V2] Agent configs: {', '.join([f'{k}={v.provider}/{v.model}' for k, v in final_configs.items()])}")

    # Initialize agent system if needed (always use multi-agent, mode determines capabilities)
    if use_multi_agent:
        if not _multi_agent_initialized:
            logger.info(f"[V2] Initializing Multi-Agent System")

            # Import tool collections
            from app.core.engines.smolagents.tool_adapter import batch_convert_tools
            from app.tools.python_interpreter import python_interpreter
            from app.tools.predefined import (
                visit_webpage, search_google, enhanced_google_search,
                search_github_repositories, search_github_code, get_github_repository_info,
                check_gpu_status, create_requirements_file,
                query_arxiv, query_scholar, query_pubmed,
            )
            from app.tools.visualization import (
                create_line_plot, create_bar_chart, create_scatter_plot,
                create_heatmap, create_distribution_plot
            )
            from app.tools.core import (
                read_project_file, save_agent_file,
                analyze_media_file, analyze_gcs_media,
            )
            from app.tools.search import gemini_google_search, gemini_realtime_search

            smolagent_tools = [
                python_interpreter, visit_webpage, search_google, enhanced_google_search,
                search_github_repositories, search_github_code, get_github_repository_info,
                check_gpu_status, create_requirements_file,
                create_line_plot, create_bar_chart, create_scatter_plot,
                create_heatmap, create_distribution_plot,
                read_project_file, save_agent_file,
                analyze_media_file, analyze_gcs_media,
                query_arxiv, query_scholar, query_pubmed,
                # Gemini Google Search (grounding-based real-time search)
                gemini_google_search, gemini_realtime_search,
            ]

            all_tools = batch_convert_tools(smolagent_tools)
            manager_tools = []
            base_tools = all_tools

            system = initialize_multi_agent_system(
                base_tools=base_tools,
                manager_tools=manager_tools,
                mode=mode or "deep",
                verbose=False
            )
            if not system:
                raise HTTPException(status_code=500, detail="Failed to initialize Multi-Agent System")
            _multi_agent_initialized = True
            logger.info(f"[V2] Multi-Agent System initialized")
    else:
        if not _initialized:
            logger.info(f"[V2] Initializing Single LangChain Agent")
            success = initialize_langchain_labos(verbose=False)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to initialize LangChain agent")
            _initialized = True

    # Generate workflow ID
    workflow_id = f"v2_project_{project_id}_{int(datetime.utcnow().timestamp() * 1000)}"
    set_log_context(user_id=user_id, project_id=project_id, workflow_id=workflow_id)

    try:
        # Load recent chat history
        recent_messages = await get_recent_messages(project_id, db, limit=11)
        if recent_messages and recent_messages[-1].id == user_message_id:
            chat_history = recent_messages[:-1]
        else:
            chat_history = recent_messages

        formatted_history = format_messages_for_langchain(chat_history)
        logger.info(f"[V2] Loaded {len(formatted_history)} messages as chat history")

        # Prepare query (string or multimodal list)
        query_content = message_content

        # Normalize file attachments to a list
        files_to_process = []
        if attached_files:
            files_to_process = attached_files
        elif attached_file:
            files_to_process = [attached_file]

        # If files attached, add file context to message
        if files_to_process:
            file_contexts = []

            for file_info in files_to_process:
                file_id = file_info.get("file_id")
                filename = file_info.get("filename", "unknown")
                content_type = file_info.get("content_type", "")

                # Check file type
                is_image = content_type.startswith('image/')
                is_video = content_type.startswith('video/')
                is_csv = content_type == 'text/csv' or filename.endswith('.csv')
                is_text = content_type.startswith('text/') or filename.endswith(('.txt', '.md', '.json', '.yaml', '.yml'))

                if is_image or is_video:
                    # For media files (images/videos), use analyze_media_file tool
                    file_contexts.append(f"- '{filename}' (File ID: {file_id}): Use analyze_media_file('{file_id}', prompt) to analyze")
                    logger.info(f"[V2] Added media file context: {filename} (ID: {file_id})")

                elif is_csv or is_text:
                    # For CSV and text files, use read_project_file tool
                    file_contexts.append(f"- '{filename}' (File ID: {file_id}): Use read_project_file('{file_id}') to read contents")
                    logger.info(f"[V2] Added data file context: {filename} (ID: {file_id})")

                else:
                    # For other file types, provide generic file info
                    file_contexts.append(f"- '{filename}' (File ID: {file_id}, type: {content_type}): Use read_project_file('{file_id}') to access")
                    logger.info(f"[V2] Added generic file context: {filename} (ID: {file_id})")

            # Build combined file context message
            if len(files_to_process) == 1:
                file_context = f"\n\n[System: User uploaded a file. {file_contexts[0]}]"
            else:
                files_list = "\n".join(file_contexts)
                file_context = f"\n\n[System: User uploaded {len(files_to_process)} files:\n{files_list}\n\nUse the appropriate tool for each file to read/analyze them.]"

            query_content = message_content + file_context

        # Register workflow
        workflow_event_queue.register_workflow(workflow_id)

        # Start event listener
        listener_task = await start_workflow_listener(
            workflow_id=workflow_id,
            project_id=project_id
        )
        logger.info(f"[V2] Event listener started for workflow: {workflow_id}")

        # Create WebSocket callback
        ws_callback = LangChainWebSocketCallback(
            workflow_id=workflow_id,
            project_id=project_id
        )
        callbacks = [ws_callback]

        # Process in background
        async def process_in_background():
            try:
                from app.services.workflows import set_workflow_context

                def run_with_context():
                    step_counter = {'count': 0}

                    # Initialize sandbox for this user/project
                    from app.services.sandbox import get_sandbox_manager
                    sandbox = get_sandbox_manager()
                    sandbox_root = sandbox.ensure_project_sandbox(user_id, project_id)

                    set_workflow_context(
                        workflow_id=workflow_id,
                        step_counter=step_counter,
                        metadata={
                            'user_id': user_id,
                            'project_id': project_id,
                            'sandbox_root': str(sandbox_root),
                        },
                        ws_callback=ws_callback
                    )
                    if use_multi_agent:
                        # ===== Create Multi-Agent System with SANDBOX-SAFE tools =====
                        from app.core.engines.langchain.multi_agent_system import create_workflow_multi_agent_system
                        from app.core.engines.smolagents.tool_adapter import batch_convert_tools

                        # Import SANDBOX-SAFE tools (restricted file access, no shell commands)
                        from app.tools.core.sandbox_python import python_interpreter
                        from app.tools.core.sandbox_files import (
                            save_file, read_file, list_project_files,
                            save_binary_file, read_binary_file, delete_file, file_exists,
                        )
                        from app.tools.predefined import (
                            visit_webpage, search_google, enhanced_google_search,
                            search_github_repositories, search_github_code, get_github_repository_info,
                            query_arxiv, query_scholar, query_pubmed,
                            # NOTE: Removed dangerous tools: check_gpu_status, create_requirements_file
                        )
                        from app.tools.visualization import (
                            create_line_plot, create_bar_chart, create_scatter_plot,
                            create_heatmap, create_distribution_plot
                        )
                        from app.tools.core import (
                            analyze_media_file, analyze_gcs_media,
                        )

                        # Load SANDBOX-SAFE tools
                        # - python_interpreter: runs in sandbox directory, blocked dangerous imports
                        # - save_file/read_file: restricted to sandbox/{user}/{project}/
                        # - NO shell commands, NO package installation
                        smolagent_tools = [
                            # Code execution (sandbox-restricted)
                            python_interpreter,
                            # File operations (sandbox-restricted)
                            save_file, read_file, list_project_files,
                            save_binary_file, read_binary_file, delete_file, file_exists,
                            # Search tools (read-only, safe)
                            visit_webpage, search_google, enhanced_google_search,
                            search_github_repositories, search_github_code, get_github_repository_info,
                            query_arxiv, query_scholar, query_pubmed,
                            # Visualization (outputs to sandbox)
                            create_line_plot, create_bar_chart, create_scatter_plot,
                            create_heatmap, create_distribution_plot,
                            # Media analysis
                            analyze_media_file, analyze_gcs_media,
                        ]
                        all_tools = batch_convert_tools(smolagent_tools)

                        # Create system with final_configs
                        system = MultiAgentSystem(verbose=False)
                        _register_agents_to_system(
                            system=system,
                            base_tools=all_tools,
                            manager_tools=[],
                            mode=mode,  # Use mode parameter from request (fast/deep)
                            verbose=False,
                            agent_llm_configs=final_configs  # Use merged configs
                        )

                        # Run query
                        return system.run(
                            query=query_content,
                            conversation_history=formatted_history,
                            callbacks=callbacks
                        )
                    else:
                        return run_query(
                            query=query_content,
                            conversation_history=formatted_history,
                            callbacks=callbacks
                        )

                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(executor, run_with_context)

                logger.info(f"[V2] Processing completed")

                # Emit completion step
                # NOTE: Cannot use get_workflow_context() here because we're in async context
                # but the context was set in the executor thread. Use workflow_id directly.
                from app.services.workflows import workflow_event_queue
                from app.services.workflows.workflow_events import WorkflowEvent

                output_content = result.get("output", "")

                # Get step count from collected_steps (starts at 1 for "Start Multi-Agent Processing")
                step_number = len(ws_callback.collected_steps) + 1 if ws_callback.collected_steps else 2

                # Create completion step showing character count only
                # Full response is saved separately in ChatMessage, not displayed in workflow
                completion_step_data = {
                    "step_type": "step",
                    "title": "Multi-Agent Processing Complete",
                    "description": f"Generated response of {len(output_content)} characters",
                    "step_number": step_number,
                    "timestamp": datetime.now().isoformat()
                }

                # Emit to WebSocket
                workflow_event_queue.put(WorkflowEvent(
                    workflow_id=workflow_id,
                    event_type="step",
                    timestamp=datetime.now(),
                    step_number=step_number,
                    title="Multi-Agent Processing Complete",
                    description=f"Generated response of {len(output_content)} characters"
                ))

                # Add to callback's collected_steps for database persistence
                if ws_callback and hasattr(ws_callback, 'collected_steps'):
                    ws_callback.collected_steps.append(completion_step_data)
                    logger.info(f"[V2] Added completion step to collected_steps")

                logger.info(f"[V2] Emitted completion workflow step with {len(output_content)} chars")

                # Save AI response
                response_metadata = {
                    "success": result.get("success", True),
                    "steps_count": len(ws_callback.collected_steps) if ws_callback.collected_steps else 0
                }
                # Support both single file and multiple files
                if attached_files:
                    response_metadata["attached_files"] = attached_files
                elif attached_file:
                    response_metadata["attached_file"] = attached_file

                response_dict = {
                    "content": result.get("output", ""),
                    "metadata": response_metadata
                }
                execution_id = await WorkflowDatabase.save_response_to_project(
                    project_id,
                    response_dict,
                    workflow_id
                )
                logger.info(f"[V2] Saved AI response to database, execution_id: {execution_id}")

                # Save workflow steps if available
                if ws_callback.collected_steps:
                    # Create simple objects from dict steps for database persistence
                    class StepObject:
                        def __init__(self, step_dict):
                            self.type = step_dict.get("step_type", "unknown")
                            self.title = step_dict.get("title", "Untitled")
                            self.description = step_dict.get("description", "")
                            self.status = "completed"
                            self.tool_name = step_dict.get("tool_name")
                            self.tool_result = step_dict.get("tool_result")
                            self.step_metadata = step_dict.get("step_metadata")

                    # Save each step individually
                    saved_count = 0
                    for i, step_dict in enumerate(ws_callback.collected_steps):
                        step_obj = StepObject(step_dict)
                        success = await WorkflowDatabase.save_workflow_step(
                            project_id=project_id,
                            workflow_id=workflow_id,
                            step=step_obj,
                            step_index=i + 1
                        )
                        if success:
                            saved_count += 1

                    logger.info(f"[V2] Saved {saved_count}/{len(ws_callback.collected_steps)} workflow steps")

                # Send chat_completed WebSocket message
                try:
                    from app.services.websocket_broadcast import websocket_broadcaster

                    completion_message = {
                        "type": "chat_completed",
                        "workflow_id": workflow_id,
                        "project_id": project_id,
                        "response": {
                            "id": f"msg_{int(datetime.now().timestamp() * 1000)}",
                            "type": "assistant",
                            "content": output_content,
                            "metadata": {
                                "success": result.get("success", True),
                                "steps_count": len(ws_callback.collected_steps) if ws_callback.collected_steps else 0
                            }
                        },
                        "timestamp": datetime.now().isoformat(),
                        "action": "project_updated"
                    }

                    await websocket_broadcaster.broadcast(completion_message)
                    logger.info(f"[V2] Broadcasted chat_completed message")
                except Exception as ws_error:
                    logger.error(f"[V2] Failed to broadcast chat_completed: {ws_error}")

                # Stop listener
                await stop_workflow_listener(listener_task)
                workflow_event_queue.unregister_workflow(workflow_id)
                logger.info(f"[V2] Workflow completed: {workflow_id}")

            except Exception as e:
                logger.error(f"[V2] Error processing message: {e}")
                import traceback
                traceback.print_exc()
                # Import needed for cleanup in error case
                from app.services.workflows.workflow_events import workflow_event_queue as wf_queue
                await stop_workflow_listener(listener_task)
                wf_queue.unregister_workflow(workflow_id)

        # Start background processing
        asyncio.create_task(process_in_background())

        # Return workflow ID immediately
        return {
            "workflow_id": workflow_id,
            "success": True
        }

    except Exception as e:
        logger.error(f"[V2] Failed to process message: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


class SendMessageRequest(BaseModel):
    """Request model for sending a message to a project"""
    content: str
    role: MessageRole = MessageRole.USER
    mode: Optional[str] = "deep"
    use_multi_agent: bool = True  # Default to multi-agent system (production, not Optional!)


async def get_recent_messages(project_id: str, db: AsyncSession, limit: int = 10) -> List[ChatMessage]:
    """Get recent messages from a project for chat history"""
    query = (
        select(ChatMessage)
        .where(ChatMessage.project_id == uuid.UUID(project_id))
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    messages = result.scalars().all()
    return list(reversed(messages))  # Return in chronological order


def format_messages_for_langchain(messages: List[ChatMessage]) -> List:
    """
    Format database messages for LangChain chat history

    IMPORTANT: This ONLY returns USER and ASSISTANT messages.
    SystemMessage is NOT stored in database - it's agent configuration,
    managed by LangChainAgent class. Even if chat history exceeds 10 messages,
    the SystemMessage will always be present (prepended by the agent).

    CRITICAL: AIMessage objects must NOT contain tool_calls or additional_kwargs
    when recreated from database, as this can cause MALFORMED_FUNCTION_CALL errors
    with Gemini. We only preserve the text content.
    """
    from langchain_core.messages import HumanMessage, AIMessage

    formatted = []
    for msg in messages:
        if msg.role == MessageRole.USER:
            formatted.append(HumanMessage(content=msg.content))
        else:  # ASSISTANT
            # Only include text content, no tool_calls or metadata
            # This prevents MALFORMED_FUNCTION_CALL errors when Gemini sees
            # improperly formatted tool calls from previous messages
            content = msg.content or ""

            # CRITICAL FIX: Skip empty or invalid assistant messages
            # Empty responses like "[]" or "" can corrupt conversation history
            # and cause Gemini to return empty responses in subsequent turns
            if content.strip() and content.strip() != "[]":
                formatted.append(AIMessage(content=content))
            else:
                print(f"⚠️  Filtered out invalid AIMessage: '{content}'")
    return formatted


@router.post("/projects/{project_id}/messages")
async def send_message_to_project_v2(
    http_request: Request,
    project_id: str,
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Send a message to a project using LangChain V2 engine

    This endpoint:
    1. Saves the user message to database
    2. Loads recent chat history (last 10 messages)
    3. Runs LangChain agent with history context
    4. Saves AI response and workflow steps
    """
    global _initialized

    # Get user ID from authentication
    user_id = await get_current_user_id(http_request)

    # Set logging context
    set_log_context(user_id=user_id, project_id=project_id)

    logger.info(f"[V2] User sending message to project", extra={
        "message_length": len(request.content),
        "role": request.role.value
    })

    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user_id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Save user message to database
    user_message = ChatMessage(
        project_id=uuid.UUID(project_id),
        role=MessageRole.USER,
        content=request.content
    )
    db.add(user_message)

    # Update project timestamp
    project.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user_message)

    logger.info(f"[V2] User message saved, ID: {user_message.id}")

    # Initialize agent system based on request parameter
    global _initialized, _multi_agent_initialized

    if request.use_multi_agent:
        # Initialize multi-agent system (production)
        if not _multi_agent_initialized:
            logger.info(f"[V2] Initializing Multi-Agent System")

            # Collect tools (same as single-agent mode)
            from app.core.engines.smolagents.tool_adapter import batch_convert_tools
            from app.tools.python_interpreter import python_interpreter
            from app.tools.predefined import (
                visit_webpage, search_google, enhanced_google_search,
                search_github_repositories, search_github_code, get_github_repository_info,
                check_gpu_status, create_requirements_file,
                query_arxiv, query_scholar, query_pubmed,
            )
            from app.tools.visualization import (
                create_line_plot, create_bar_chart, create_scatter_plot,
                create_heatmap, create_distribution_plot
            )
            from app.tools.core import (
                read_project_file, save_agent_file,
                analyze_media_file, analyze_gcs_media,
            )
            from app.tools.search import gemini_google_search, gemini_realtime_search

            smolagent_tools = [
                # Python execution (CRITICAL for data analysis)
                python_interpreter,
                # Core web and search tools
                visit_webpage,
                search_google,
                enhanced_google_search,
                # GitHub tools
                search_github_repositories,
                search_github_code,
                get_github_repository_info,
                # Development tools
                check_gpu_status,
                create_requirements_file,
                # Visualization tools
                create_line_plot,
                create_bar_chart,
                create_scatter_plot,
                create_heatmap,
                create_distribution_plot,
                # File access tools
                read_project_file,
                save_agent_file,
                analyze_media_file,
                analyze_gcs_media,
                # Academic research tools
                query_arxiv,
                query_scholar,
                query_pubmed,
                # Gemini Google Search (grounding-based real-time search)
                gemini_google_search,
                gemini_realtime_search,
            ]

            # Convert tools using adapter
            all_tools = batch_convert_tools(smolagent_tools)
            logger.info(f"[V2] Collected {len(all_tools)} tools for multi-agent system")

            # Separate tools for manager vs specialized agents
            # Manager gets NO base tools - ONLY delegation tools will be added by initialize_multi_agent_system
            # This FORCES delegation for ALL tasks (visualization, research, computation, etc.)
            manager_tools = []  # Empty list - manager can ONLY delegate

            # Specialized agents get all tools
            base_tools = all_tools

            logger.info(f"[V2] Manager tools: {len(manager_tools)} (delegation-only), Base tools: {len(base_tools)}")

            # Initialize multi-agent system with tools
            # base_tools: for dev_agent, tool_creation_agent, critic_agent (ALL TOOLS)
            # manager_tools: for manager_agent (python_interpreter only + delegation tools added automatically)
            system = initialize_multi_agent_system(
                base_tools=base_tools,
                manager_tools=manager_tools,  # Limited tools - forces delegation
                mode=request.mode or "deep",
                verbose=False
            )
            if not system:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to initialize Multi-Agent System"
                )
            _multi_agent_initialized = True
            logger.info(f"[V2] Multi-Agent System initialized with {len(all_tools)} tools")
    else:
        # Initialize single agent (testing/debugging)
        if not _initialized:
            logger.info(f"[V2] Initializing Single LangChain Agent (debug mode)")
            success = initialize_langchain_labos(verbose=False)
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to initialize LangChain agent"
                )
            _initialized = True
            logger.info("[V2] Single LangChain Agent initialized")

    # Generate workflow ID
    workflow_id = f"v2_project_{project_id}_{int(datetime.utcnow().timestamp() * 1000)}"
    set_log_context(user_id=user_id, project_id=project_id, workflow_id=workflow_id)

    try:
        # Load recent chat history (last 10 messages, excluding the one we just saved)
        recent_messages = await get_recent_messages(project_id, db, limit=11)  # Get 11 to exclude current

        # Remove the last message (the one we just saved) from history
        if recent_messages and recent_messages[-1].id == user_message.id:
            chat_history = recent_messages[:-1]
        else:
            chat_history = recent_messages

        # Format for LangChain
        formatted_history = format_messages_for_langchain(chat_history)

        logger.info(f"[V2] Loaded {len(formatted_history)} messages as chat history")

        # Debug: log the actual history messages (with truncated base64 data)
        for i, msg in enumerate(formatted_history):
            # Handle multimodal content with base64 data
            if hasattr(msg, 'content'):
                if isinstance(msg.content, list):
                    # Multimodal content - truncate base64 data
                    content_parts = []
                    for item in msg.content:
                        if isinstance(item, dict) and item.get('type') == 'media':
                            data = item.get('data', '')
                            mime_type = item.get('mime_type', 'unknown')
                            data_preview = f"{data[:20]}...<{len(data)} bytes base64 truncated>"
                            content_parts.append(f"media({mime_type}, {data_preview})")
                        else:
                            content_parts.append(str(item)[:80])
                    content_preview = f"[{', '.join(content_parts)}]"
                else:
                    content_preview = msg.content[:100]
            else:
                content_preview = str(msg)[:100]

            logger.info(f"[V2] History [{i}] {msg.__class__.__name__}: {content_preview}...")

        logger.info(f"[V2] Current query: {request.content[:100]}...")

        # Register workflow
        workflow_event_queue.register_workflow(workflow_id)

        # Start event listener
        listener_task = await start_workflow_listener(
            workflow_id=workflow_id,
            project_id=project_id
        )
        logger.info(f"[V2] Event listener started for workflow: {workflow_id}")

        # Create WebSocket callback
        ws_callback = LangChainWebSocketCallback(
            workflow_id=workflow_id,
            project_id=project_id
        )
        callbacks = [ws_callback]

        # Create async processing task (like V1)
        async def process_in_background():
            """Process the query in background and save results"""
            try:
                # Import workflow context
                from app.services.workflows import set_workflow_context

                # Create wrapper function that sets context before running agent
                def run_with_context():
                    step_counter = {'count': 0}

                    # Initialize sandbox for this user/project
                    from app.services.sandbox import get_sandbox_manager
                    sandbox = get_sandbox_manager()
                    sandbox_root = sandbox.ensure_project_sandbox(user_id, project_id)

                    set_workflow_context(
                        workflow_id=workflow_id,
                        step_counter=step_counter,
                        metadata={
                            'user_id': user_id,
                            'project_id': project_id,
                            'sandbox_root': str(sandbox_root),
                        },
                        ws_callback=ws_callback  # CRITICAL: Pass callback for step collection
                    )
                    # Use multi-agent or single agent based on request parameter
                    if request.use_multi_agent:
                        logger.info(f"[V2] Running query with Multi-Agent System (sandbox: {sandbox_root})")
                        return run_multi_agent_query(
                            query=request.content,
                            conversation_history=formatted_history,
                            callbacks=callbacks
                        )
                    else:
                        logger.info(f"[V2] Running query with Single Agent (debug mode)")
                        return run_query(
                            query=request.content,
                            conversation_history=formatted_history,
                            callbacks=callbacks
                        )

                # Run query with chat history in thread executor
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(executor, run_with_context)

                logger.info(f"[V2] Query completed, got result")
                logger.info(f"[V2] Result keys: {result.keys()}")
                logger.info(f"[V2] Result output: {result.get('output', 'NO OUTPUT')[:200]}")
                logger.info(f"[V2] Result success: {result.get('success', 'NO SUCCESS FLAG')}")

                # Emit completion workflow step
                # NOTE: Cannot use get_workflow_context() here because we're in async context
                # but the context was set in the executor thread. Use workflow_id directly.
                # NOTE: workflow_event_queue is imported at module level (line 34)
                from app.services.workflows.workflow_events import WorkflowEvent

                output_content = result.get("output", "")

                # Start follow-up generation EARLY (runs in parallel with DB saves)
                # This overlaps follow-up LLM call with database I/O for better UX
                follow_up_future = None
                followup_executor = None
                if result.get("success", True) and output_content:
                    try:
                        from app.core.engines.langchain.multi_agent_system import generate_follow_up_questions as gen_followups
                        followup_executor = ThreadPoolExecutor(max_workers=1)
                        follow_up_future = loop.run_in_executor(
                            followup_executor,
                            lambda: gen_followups(
                                user_query=request.content,
                                ai_response=output_content
                            )
                        )
                        logger.info(f"[V2] ⚡ Follow-up generation started in parallel with DB saves")
                    except Exception as e:
                        logger.warning(f"[V2] Failed to start follow-up generation: {e}")

                # Get step count from collected_steps (starts at 1 for "Start Multi-Agent Processing")
                step_number = len(ws_callback.collected_steps) + 1 if ws_callback.collected_steps else 2

                # Create completion step showing character count only
                # Full response is saved separately in ChatMessage, not displayed in workflow
                completion_step_data = {
                    "step_type": "step",
                    "title": "Multi-Agent Processing Complete",
                    "description": f"Generated response of {len(output_content)} characters",
                    "step_number": step_number,
                    "timestamp": datetime.now().isoformat()
                }

                # Emit to WebSocket
                workflow_event_queue.put(WorkflowEvent(
                    workflow_id=workflow_id,
                    event_type="step",
                    timestamp=datetime.now(),
                    step_number=step_number,
                    title="Multi-Agent Processing Complete",
                    description=f"Generated response of {len(output_content)} characters"
                ))

                # Add to callback's collected_steps for database persistence
                if ws_callback and hasattr(ws_callback, 'collected_steps'):
                    ws_callback.collected_steps.append(completion_step_data)
                    logger.info(f"[V2] Added completion step to collected_steps")

                logger.info(f"[V2] Emitted completion workflow step with {len(output_content)} chars")

                # Save AI response and workflow execution to database
                # NOTE: WorkflowDatabase.save_response_to_project() handles both:
                # 1. Creating ChatMessage (ASSISTANT role)
                # 2. Creating WorkflowExecution record
                # Format response for save_response_to_project (expects dict with 'content' key)
                response_dict = {
                    "content": result.get("output", ""),
                    "metadata": {
                        "success": result.get("success", True),
                        "steps_count": len(ws_callback.collected_steps) if ws_callback.collected_steps else 0
                    }
                }
                execution_id = await WorkflowDatabase.save_response_to_project(
                    project_id,
                    response_dict,
                    workflow_id
                )
                logger.info(f"[V2] Workflow execution saved, ID: {execution_id}")

                # Save workflow steps if available
                if ws_callback.collected_steps:
                    # Create simple objects from dict steps for database persistence
                    class StepObject:
                        def __init__(self, step_dict):
                            self.type = step_dict.get("step_type", "unknown")
                            self.title = step_dict.get("title", "Untitled")
                            self.description = step_dict.get("description", "")
                            self.status = "completed"
                            self.tool_name = step_dict.get("tool_name")
                            self.tool_result = step_dict.get("tool_result")
                            self.step_metadata = step_dict.get("step_metadata")

                    # Save each step individually
                    saved_count = 0
                    for i, step_dict in enumerate(ws_callback.collected_steps):
                        step_obj = StepObject(step_dict)
                        success = await WorkflowDatabase.save_workflow_step(
                            project_id=project_id,
                            workflow_id=workflow_id,
                            step=step_obj,
                            step_index=i + 1
                        )
                        if success:
                            saved_count += 1

                    logger.info(f"[V2] Saved {saved_count}/{len(ws_callback.collected_steps)} workflow steps")

                # Await follow-up questions (started earlier, running in parallel with DB saves)
                follow_up_questions = []
                if follow_up_future:
                    try:
                        follow_up_questions = await follow_up_future
                        logger.info(f"[V2] Generated {len(follow_up_questions)} follow-up questions")
                    except Exception as e:
                        logger.warning(f"[V2] Failed to generate follow-up questions: {e}")
                    finally:
                        if followup_executor:
                            followup_executor.shutdown(wait=False)

                # Send completion notification via WebSocket
                # Answer + follow-up questions delivered together for seamless UX
                from app.services.websocket_broadcast import websocket_broadcaster

                completion_message = {
                    "type": "chat_completed",
                    "workflow_id": workflow_id,
                    "project_id": project_id,
                    "response": {
                        "id": f"msg_{int(datetime.utcnow().timestamp() * 1000)}",
                        "type": "assistant",
                        "content": result.get("output", ""),
                        "timestamp": datetime.utcnow().isoformat(),
                        "metadata": {
                            "execution_time": 0,
                            "agent_id": "langchain_agent",
                            "using_langchain": True,
                            "workflow_id": workflow_id
                        }
                    },
                    "follow_up_questions": follow_up_questions,
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "project_updated"
                }

                await websocket_broadcaster.broadcast(completion_message)
                logger.info(f"[V2] ✅ Answer + {len(follow_up_questions)} follow-up questions delivered together")

                logger.info(f"[V2] Background processing completed for workflow: {workflow_id}")

            except Exception as e:
                logger.error(f"[V2] Error in background processing: {str(e)}")
                import traceback
                traceback.print_exc()

                # Send error notification
                from app.services.websocket_broadcast import websocket_broadcaster
                await websocket_broadcaster.broadcast({
                    "type": "workflow_error",
                    "workflow_id": workflow_id,
                    "project_id": project_id,
                    "error": str(e)
                })

            finally:
                # Stop event listener
                logger.info(f"[V2] Stopping event listener for workflow: {workflow_id}")
                await stop_workflow_listener(listener_task)
                workflow_event_queue.unregister_workflow(workflow_id)

        # Start background task (fire and forget like V1)
        asyncio.create_task(process_in_background())

        # Return immediately (like V1)
        return {
            "success": True,
            "data": {
                "message": "Processing started",
                "workflow_id": workflow_id,
                "status": "processing",
                "project_id": project_id,
                "user_message_id": str(user_message.id),
                "note": "AI response and workflow will be sent via WebSocket"
            }
        }

    except Exception as e:
        logger.error(f"[V2] Error initializing workflow: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/messages/with-files")
async def send_message_with_files_v2(
    http_request: Request,
    project_id: str,
    message: str = Form(...),
    file_ids: Optional[str] = Form(None),  # Comma-separated file IDs (sandbox filenames)
    files: List[UploadFile] = File(default=[]),  # Multiple files for direct upload
    use_multi_agent: bool = Form(True),
    mode: str = Form("deep"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Send a message with multiple attached files to a project using LangChain V2

    All files are stored in user's sandbox directory: /data/sandboxes/{user_id}/{project_id}/

    Two upload methods:
    1. Direct upload (small files <32MB each): Pass files via multipart form data
    2. Pre-uploaded files: Pass comma-separated file_ids (sandbox filenames)

    Supports up to 5 files per message.
    """
    # Get user ID
    user_id = await get_current_user_id(http_request)
    set_log_context(user_id=user_id, project_id=project_id)

    # Verify project ownership
    project_query = select(ChatProject).where(
        ChatProject.id == uuid.UUID(project_id),
        ChatProject.user_id == user_id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Initialize sandbox for this user/project
    sandbox = get_sandbox_manager()
    sandbox_root = sandbox.ensure_project_sandbox(user_id, project_id)

    # Collect all file info
    attached_files_info = []

    # Handle pre-uploaded files (via file_ids - these are sandbox filenames)
    if file_ids:
        file_id_list = [fid.strip() for fid in file_ids.split(",") if fid.strip()]
        logger.info(f"[V2] Processing {len(file_id_list)} pre-uploaded files from sandbox")

        for filename in file_id_list:
            file_path = sandbox_root / filename
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=f"File {filename} not found in sandbox")

            # Get file info
            file_size = file_path.stat().st_size
            content_type = _guess_content_type(filename)

            attached_files_info.append({
                "file_id": filename,  # Use filename as ID for sandbox files
                "filename": filename,
                "size": file_size,
                "content_type": content_type,
                "storage": "sandbox"
            })

    # Handle direct uploaded files - save to sandbox
    if files:
        logger.info(f"[V2] Processing {len(files)} direct-uploaded files")

        for file in files:
            if not file.filename:
                continue

            # Read and validate file
            file_data = await file.read()
            file_size = len(file_data)

            if file_size == 0:
                continue

            # Size limits: 32MB for direct upload
            max_size = 32 * 1024 * 1024
            if file_size > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} too large (>{max_size // (1024*1024)}MB). Use GCS upload for large files."
                )

            # Save file to sandbox uploads directory with unique name
            safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
            uploads_dir = sandbox_root / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            file_path = uploads_dir / safe_filename

            # Write file to sandbox
            file_path.write_bytes(file_data)
            logger.info(f"[V2] Saved file to sandbox uploads: {file_path}")

            attached_files_info.append({
                "file_id": safe_filename,  # Use filename as ID for sandbox files
                "filename": file.filename,  # Original filename
                "size": file_size,
                "content_type": file.content_type or _guess_content_type(file.filename),
                "storage": "sandbox"
            })

    if not attached_files_info:
        raise HTTPException(status_code=400, detail="At least one file must be provided")

    if len(attached_files_info) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files per message")

    logger.info(f"[V2] Total {len(attached_files_info)} files attached (sandbox storage)")

    # Create chat message with all file attachments
    chat_message = ChatMessage(
        project_id=uuid.UUID(project_id),
        role=MessageRole.USER,
        content=message,
        message_metadata={
            "attached_files": attached_files_info,
            "langchain_v2": True,
            "multi_file": True,
            "storage": "sandbox"
        }
    )

    db.add(chat_message)
    project.updated_at = datetime.now()

    await db.commit()
    await db.refresh(chat_message)

    logger.info(f"[V2] Multi-file message created with {len(attached_files_info)} files (sandbox)")

    # Process message with all attached files
    result = await process_message_with_agent(
        user_id=user_id,
        project_id=project_id,
        message_content=message,
        use_multi_agent=use_multi_agent,
        mode=mode,
        db=db,
        user_message_id=chat_message.id,
        attached_files=attached_files_info
    )

    # Return files info and workflow ID
    return {
        "success": True,
        "message": f"Message with {len(attached_files_info)} files uploaded and processing started",
        "data": {
            "workflow_id": result["workflow_id"],
            "files_info": attached_files_info,
            "message_id": str(chat_message.id)
        }
    }


def _guess_content_type(filename: str) -> str:
    """Guess content type from filename extension"""
    import mimetypes
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or "application/octet-stream"


@router.get("/status")
async def langchain_v2_status():
    """Get LangChain V2 agent status"""
    return {
        "engine": "langchain-v2",
        "initialized": _initialized,
        "features": {
            "chat_history": True,
            "workflow_persistence": True,
            "message_persistence": True,
            "websocket_streaming": True,
            "file_upload": True,
            "multimodal": True  # Gemini supports images and video
        }
    }
