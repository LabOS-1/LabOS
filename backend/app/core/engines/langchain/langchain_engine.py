"""
LangChain-based Agent Engine for LabOS
Replacement for Smolagents-based labos_engine.py
Uses direct API calls to Gemini, Claude, and GPT without OpenRouter
"""

import os
import sys
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool as langchain_tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.callbacks.base import BaseCallbackHandler

# Import unified configuration
from app.config import (
    AI_MODELS, LABOS_CONFIG, EXTERNAL_APIS, PHOENIX_CONFIG,
    PERFORMANCE_CONFIG, MEMORY_CONFIG, TOOLS_CONFIG
)

# Import tool adapter for converting Smolagents tools
from app.core.engines.smolagents.tool_adapter import batch_convert_tools

# Import prompt loader
from app.core.engines.smolagents.agents.prompt_loader import load_custom_prompts

# Import existing tools (will be converted to LangChain format)
from app.tools.core import (
    # Memory tools
    auto_recall_experience,
    check_agent_performance,
    quick_tool_stats,
    # Evaluation tools
    evaluate_with_critic,
    # File access tools
    read_project_file,
    save_agent_file,
    get_file_bytes,
    analyze_media_file,
    analyze_gcs_media,
)

# Import visualization tools
from app.tools.visualization import (
    create_line_plot,
    create_bar_chart,
    create_scatter_plot,
    create_heatmap,
    create_distribution_plot
)

# Import python interpreter
from app.tools.python_interpreter import python_interpreter

# Import predefined tools
from app.tools.predefined import (
    # Enhanced search tools
    enhanced_google_search, search_google_basic, multi_source_search,
    smart_search_router, search_with_serpapi, enhanced_knowledge_search, search_google,
    # Web and content tools
    visit_webpage, extract_url_content, extract_pdf_content,
    # GitHub tools
    search_github_repositories, search_github_code, get_github_repository_info,
    # Academic research tools
    fetch_supplementary_info_from_doi, query_arxiv, query_scholar, query_pubmed,
    # Development and system tools
    run_shell_command, create_conda_environment, install_packages_conda,
    install_packages_pip, check_gpu_status, create_script, create_and_run_script,
    run_script, create_requirements_file, monitor_training_logs
)

# Import Gemini-powered search tools (uses separate Gemini instance with google_search grounding)
from app.tools.search import gemini_google_search, gemini_realtime_search

# ==========================================
# Configuration
# ==========================================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Model configurations from unified config
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")  # Read from env
CLAUDE_MODEL = "claude-sonnet-4"  # Claude Sonnet 4
GPT_MODEL = "gpt-4o"  # GPT-4o

# Performance settings
DEFAULT_MAX_STEPS = AI_MODELS.get("parameters", {}).get("max_steps", {}).get("manager_agent", 10)
DEFAULT_TEMPERATURE = AI_MODELS.get("parameters", {}).get("temperature", 0.1)

# ==========================================
# Global agent instances (V1 Compatibility Only)
# ==========================================
# IMPORTANT: These global variables are ONLY for V1 single-agent API compatibility.
#
# V1 API Context:
# - V1 uses a single global agent instance shared across all requests
# - Initialized via initialize_langchain_labos() and accessed via get_agent()
# - Used by /api/v2/chat endpoint (simple single-agent mode)
#
# V2 Multi-Agent System:
# - V2 creates per-workflow agent instances for user isolation
# - Each workflow gets fresh agents via create_workflow_multi_agent_system()
# - See app/core/engines/langchain/multi_agent_system.py
#
# Migration Path:
# - New features should use V2 multi-agent system (per-workflow instances)
# - V1 global agents maintained for backward compatibility only
# - Eventually, V1 API should be fully deprecated
#
langchain_agent = None  # Global LangChainAgent instance (V1 only - use multi_agent_system for V2)
current_model = None    # Global LLM model instance (V1 only - V2 creates per-agent models)


class LangChainAgent:
    """
    LangChain-based agent with native tool calling and manual callback triggers
    Replaces Smolagents CodeAgent
    """

    def __init__(
        self,
        model,
        tools: List,
        system_prompt: str = "You are LabOS, a helpful AI assistant specialized in bioinformatics and computational biology.",
        max_iterations: int = 10,
        verbose: bool = True
    ):
        self.model = model
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.verbose = verbose

        # Bind tools to model
        # Note: Gemini's google_search grounding is INCOMPATIBLE with function calling
        # So we can only use google_search when there are NO other tools (Fast Mode)
        if len(self.tools) == 0:
            # Fast Mode: Only google_search for grounding (no function calling)
            self.model_with_tools = self.model.bind_tools([{"google_search": {}}])
            print(f"⚡ Fast Mode: Agent with Google Search grounding only")
        else:
            # Deep Mode: Use custom tools only (google_search not compatible with function calling)
            self.model_with_tools = self.model.bind_tools(self.tools)
            print(f"🧠 Deep Mode: Agent with {len(self.tools)} tools")

        # Create tool name -> tool object mapping
        self.tool_map = {tool.name: tool for tool in self.tools}

    def add_tool(self, tool):
        """
        Dynamically add a new tool to the agent

        Args:
            tool: A LangChain tool (created with @tool decorator)
        """
        # Add to tools list
        self.tools.append(tool)

        # Update tool map
        self.tool_map[tool.name] = tool

        # Re-bind tools to model (no google_search - incompatible with function calling)
        self.model_with_tools = self.model.bind_tools(self.tools)

        if self.verbose:
            print(f"✅ Added tool: {tool.name}")

    def add_tools(self, tools: List):
        """
        Dynamically add multiple tools to the agent

        Args:
            tools: List of LangChain tools
        """
        for tool in tools:
            self.add_tool(tool)

    def think(self, query: str, conversation_history: Optional[List] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> str:
        """
        Let the agent think/plan WITHOUT tool calling - outputs pure text content.

        This uses the raw model (not model_with_tools) so it will output text instead of function calls.
        Useful for strategic planning, reasoning steps, or multi-step workflows.

        Args:
            query: User's input query or planning request
            conversation_history: Optional list of previous messages
            callbacks: Optional list of callback handlers

        Returns:
            String containing the agent's thinking/planning output
        """
        # Build message list (same logic as run())
        messages = []

        model_name = getattr(self.model, 'model', getattr(self.model, 'model_name', ''))
        is_gemini = 'gemini' in model_name.lower() if model_name else False

        if not is_gemini:
            messages.append(SystemMessage(content=self.system_prompt))

        if conversation_history:
            messages.extend(conversation_history)

        messages.append(HumanMessage(content=query))

        # Prepare callback config
        config = {"callbacks": callbacks} if callbacks else {}

        # Use RAW model (no tools) - this will output text content
        response = self.model.invoke(messages, config=config)

        # Extract text content
        if hasattr(response, 'content'):
            return response.content
        else:
            return str(response)

    def run(self, query: Union[str, List], conversation_history: Optional[List] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
        """
        Run the agent with a user query - manually triggers callbacks for tool execution

        Args:
            query: User's input query (string or list for multimodal content)
                  - String: "Describe this image"
                  - List: [{"type": "text", "text": "..."}, {"type": "media", "data": "...", "mime_type": "..."}]
            conversation_history: Optional list of previous messages (user/assistant ONLY, no SystemMessage)
            callbacks: Optional list of callback handlers for streaming/monitoring

        Returns:
            Dict with 'output' (final answer) and 'steps' (execution trace)
        """
        # Build message list with proper structure:
        # All models (including Gemini) use SystemMessage in the message list
        messages = []

        # Add SystemMessage for all models
        model_name = getattr(self.model, 'model', getattr(self.model, 'model_name', ''))
        is_gemini = 'gemini' in model_name.lower() if model_name else False

        # Always add SystemMessage (Gemini 3.0 supports it in message history)
        messages.append(SystemMessage(content=self.system_prompt))

        if conversation_history:
            messages.extend(conversation_history)

        messages.append(HumanMessage(content=query))

        # Debug logging
        print(f"\n{'='*80}")
        print(f"📨 Message structure (model: {model_name}):")
        print(f"   🔧 System: 1 (via SystemMessage)")
        print(f"   💬 History: {len(conversation_history) if conversation_history else 0} (from DB)")
        print(f"   👤 Current: 1 (user query)")
        print(f"   📊 Total messages: {len(messages)}")
        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__

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
                            content_parts.append(f"{{'type': 'media', 'mime_type': '{mime_type}', 'data': '{data_preview}'}}")
                        else:
                            content_parts.append(str(item)[:80])
                    content_preview = f"[{', '.join(content_parts)}]"
                else:
                    content_preview = msg.content[:80]
            else:
                content_preview = str(msg)[:80]

            marker = "🔧" if isinstance(msg, SystemMessage) else ("👤" if isinstance(msg, HumanMessage) else "🤖")
            print(f"  [{i}] {marker} {msg_type}: {content_preview}...")
        print(f"{'='*80}\n")

        steps = []
        iteration = 0

        # Prepare callback config
        config = {"callbacks": callbacks} if callbacks else {}

        try:
            while iteration < self.max_iterations:
                iteration += 1

                if self.verbose:
                    print(f"\n{'='*80}")
                    print(f"Iteration {iteration}/{self.max_iterations}")
                    print(f"{'='*80}")

                # Get model response with callbacks
                response = self.model_with_tools.invoke(messages, config=config)

                # Check for MALFORMED_FUNCTION_CALL error
                if hasattr(response, 'response_metadata'):
                    finish_reason = response.response_metadata.get('finish_reason', '')
                    if finish_reason == 'MALFORMED_FUNCTION_CALL':
                        error_msg = (
                            f"⚠️ Gemini returned MALFORMED_FUNCTION_CALL error. "
                            f"This usually means the model tried to call a tool but the format was invalid. "
                            f"Iteration: {iteration}/{self.max_iterations}"
                        )
                        print(error_msg)

                        # Check if this is the first iteration
                        if iteration == 1:
                            # Try without chat history if available
                            if conversation_history and len(conversation_history) > 0:
                                print("🔄 Retrying without chat history...")
                                # Rebuild messages without history
                                messages_no_history = []
                                if not is_gemini:
                                    messages_no_history.append(messages[0])  # SystemMessage for non-Gemini
                                messages_no_history.append(messages[-1])  # Current query (last message)

                                response = self.model_with_tools.invoke(messages_no_history, config=config)
                                if hasattr(response, 'response_metadata'):
                                    if response.response_metadata.get('finish_reason') == 'MALFORMED_FUNCTION_CALL':
                                        return {
                                            "output": "I encountered a technical error while processing your request. This appears to be a model configuration issue. Please try again or rephrase your question.",
                                            "steps": steps,
                                            "success": False,
                                            "error": "MALFORMED_FUNCTION_CALL after retry"
                                        }
                                # Success after retry - update messages to use no-history version
                                print("✅ Retry succeeded! Continuing without chat history for this session.")
                                messages = messages_no_history  # Use the version that worked
                            else:
                                return {
                                    "output": "I encountered a technical error (MALFORMED_FUNCTION_CALL). Please try rephrasing your question.",
                                    "steps": steps,
                                    "success": False,
                                    "error": "MALFORMED_FUNCTION_CALL on first iteration"
                                }

                messages.append(response)

                # Log the step
                step = {
                    "iteration": iteration,
                    "response": response.content if hasattr(response, 'content') else str(response)
                }

                # Check if there are tool calls
                if not hasattr(response, 'tool_calls') or not response.tool_calls:
                    # No tool calls - this is the final answer
                    # Use content_blocks for Gemini 3's structured content format
                    if hasattr(response, 'content_blocks') and response.content_blocks:
                        # Extract text from content blocks (Gemini 3 format)
                        text_blocks = [
                            block.get('text', '')
                            for block in response.content_blocks
                            if isinstance(block, dict) and block.get('type') == 'text'
                        ]
                        final_answer = ' '.join(text_blocks) if text_blocks else str(response.content)
                    else:
                        # Fallback to content for other models
                        final_answer = response.content if hasattr(response, 'content') else str(response)

                    # Ensure final_answer is a string
                    if not isinstance(final_answer, str):
                        final_answer = str(final_answer)

                    if self.verbose:
                        print(f"\n✅ Final answer: {final_answer}")

                    # Debug: Check if content is empty
                    if not final_answer or final_answer.strip() == "":
                        print(f"⚠️ WARNING: Final answer is empty!")
                        print(f"⚠️ Response object: {response}")
                        print(f"⚠️ Response type: {type(response)}")
                        print(f"⚠️ Response dir: {dir(response)}")

                        # Return error instead of empty response
                        return {
                            "output": "I apologize, but I was unable to generate a response. Please try rephrasing your question or try again.",
                            "steps": steps,
                            "success": False,
                            "error": "Empty response from model"
                        }

                    step["final_answer"] = True
                    steps.append(step)

                    return {
                        "output": final_answer,
                        "steps": steps,
                        "success": True
                    }

                # Execute tool calls
                if self.verbose:
                    print(f"\n🔧 Tool calls detected: {len(response.tool_calls)}")

                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    tool_call_id = tool_call['id']

                    if self.verbose:
                        print(f"  - Calling {tool_name} with args: {tool_args}")

                    # Find and execute the tool
                    if tool_name in self.tool_map:
                        try:
                            tool_obj = self.tool_map[tool_name]

                            # MANUALLY TRIGGER on_tool_start callback
                            if callbacks:
                                for callback in callbacks:
                                    try:
                                        callback.on_tool_start(
                                            serialized={"name": tool_name},
                                            input_str=str(tool_args)
                                        )
                                    except Exception as cb_err:
                                        print(f"⚠️  Callback error in on_tool_start: {cb_err}")

                            # Execute tool
                            result = tool_obj.invoke(tool_args)

                            if self.verbose:
                                print(f"    ✅ Result: {str(result)[:200]}...")

                            # MANUALLY TRIGGER on_tool_end callback
                            if callbacks:
                                for callback in callbacks:
                                    try:
                                        callback.on_tool_end(output=str(result))
                                    except Exception as cb_err:
                                        print(f"⚠️  Callback error in on_tool_end: {cb_err}")

                            tool_results.append({
                                "tool": tool_name,
                                "args": tool_args,
                                "result": result,
                                "success": True
                            })

                            # Add tool result to messages
                            messages.append(ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call_id
                            ))

                        except Exception as e:
                            error_msg = f"Error executing {tool_name}: {str(e)}"
                            if self.verbose:
                                print(f"    ❌ {error_msg}")

                            # MANUALLY TRIGGER on_tool_error callback
                            if callbacks:
                                for callback in callbacks:
                                    try:
                                        callback.on_tool_error(error=e)
                                    except Exception as cb_err:
                                        print(f"⚠️  Callback error in on_tool_error: {cb_err}")

                            tool_results.append({
                                "tool": tool_name,
                                "args": tool_args,
                                "error": str(e),
                                "success": False
                            })

                            # Add error message
                            messages.append(ToolMessage(
                                content=error_msg,
                                tool_call_id=tool_call_id
                            ))
                    else:
                        error_msg = f"Tool {tool_name} not found"
                        if self.verbose:
                            print(f"    ❌ {error_msg}")

                        tool_results.append({
                            "tool": tool_name,
                            "error": "Tool not found",
                            "success": False
                        })

                        messages.append(ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_call_id
                        ))

                step["tool_calls"] = tool_results
                steps.append(step)

            # Max iterations reached
            return {
                "output": "Max iterations reached without final answer",
                "steps": steps,
                "success": False,
                "error": "max_iterations_reached"
            }

        except Exception as e:
            if self.verbose:
                print(f"\n❌ Agent error: {str(e)}")

            return {
                "output": f"Error: {str(e)}",
                "steps": steps,
                "success": False,
                "error": str(e)
            }


def create_model(model_type: str = "gemini", temperature: float = DEFAULT_TEMPERATURE, system_instruction: str = None):
    """
    DEPRECATED: Use LLMFactory.create() instead for new code.

    This function is kept for backward compatibility with existing code.
    It wraps LLMFactory.create() with the old API.

    Args:
        model_type: Type of model ("gemini", "claude", or "gpt")
        temperature: Model temperature
        system_instruction: Optional system instruction (IGNORED - use SystemMessage instead)

    Returns:
        LangChain chat model instance
    """
    from app.core.llm.factory import LLMFactory
    from app.core.llm.config import LLMConfig

    if system_instruction:
        print(f"ℹ️  system_instruction parameter is deprecated and ignored. Pass SystemMessage in chat history instead.")

    # Map old model_type to provider/model format
    model_map = {
        "gemini": ("gemini", GEMINI_MODEL),
        "claude": ("anthropic", CLAUDE_MODEL),
        "gpt": ("openai", GPT_MODEL)
    }

    if model_type not in model_map:
        raise ValueError(f"Unknown model type: {model_type}. Use 'gemini', 'claude', or 'gpt'")

    provider, model = model_map[model_type]

    # Create config and use LLMFactory
    config = LLMConfig(
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=4096
    )

    return LLMFactory.create(config)


def initialize_langchain_labos(
    model_type: str = "gemini",
    use_template: bool = True,
    verbose: bool = True
) -> bool:
    """
    Initialize LabOS with LangChain

    Args:
        model_type: Type of model to use ("gemini", "claude", or "gpt")
        use_template: Whether to use custom prompt templates
        verbose: Whether to print verbose output

    Returns:
        Boolean indicating success
    """
    global langchain_agent, current_model

    print("🚀 Initializing LabOS with LangChain...")
    print(f"📋 Model type: {model_type}")
    print(f"📋 Using custom templates: {use_template}")

    try:
        # Load system prompt first (will be used as system_instruction for Gemini)
        import yaml
        from pathlib import Path

        try:
            app_dir = Path(__file__).resolve().parents[3]
            langchain_prompt_path = app_dir / "config" / "prompts" / "langchain" / "LabOS_prompt_langchain.yaml"

            with open(langchain_prompt_path, 'r', encoding='utf-8') as f:
                prompt_config = yaml.safe_load(f)

            print(f"✅ Loaded LangChain-specific prompt from: {langchain_prompt_path}")
        except Exception as e:
            print(f"⚠️  Could not load LangChain-specific prompt: {e}")
            # Fallback to original prompt
            prompt_config = load_custom_prompts(mode='deep')

        if prompt_config and 'system_prompt' in prompt_config:
            # Use prompt directly (already cleaned for LangChain)
            system_prompt = prompt_config['system_prompt']
            print("✅ LABOS system prompt loaded successfully")
        else:
            # Fallback to basic prompt
            system_prompt = """You are LabOS, an advanced AI assistant specialized in bioinformatics and computational biology.

You have access to various tools to help answer questions, search for information, create visualizations, and execute code.

When using tools:
1. Choose the most appropriate tool for the task
2. Provide clear and accurate arguments
3. Interpret tool results carefully
4. Provide helpful and accurate answers based on the results

Always be helpful, accurate, and professional."""
            print("⚠️  Using fallback system prompt (YAML not loaded)")

        # Create model (system prompt will be passed as SystemMessage in agent)
        current_model = create_model(model_type=model_type)
        print(f"✅ Model created: {model_type}")

        # Use ToolRegistry for automatic tool discovery
        print("🔧 Discovering tools via ToolRegistry...")
        from app.core.tools.tool_manager.tool_registry import get_predefined_tools

        # Get predefined tools (user-specific custom tools loaded per-workflow)
        smolagent_tools = get_predefined_tools()
        print(f"✅ Discovered {len(smolagent_tools)} predefined tools")

        # Convert tools using adapter
        all_tools = batch_convert_tools(smolagent_tools)

        # Note: system_prompt was already passed to Gemini via system_instruction parameter
        # We still pass it to LangChainAgent for non-Gemini models and for consistency
        langchain_agent = LangChainAgent(
            model=current_model,
            tools=all_tools,
            system_prompt=system_prompt,  # For non-Gemini models; Gemini uses system_instruction
            max_iterations=DEFAULT_MAX_STEPS,
            verbose=verbose
        )

        print(f"✅ Agent created successfully")
        print(f"🔧 Total tools available: {len(all_tools)}")
        print(f"✅ LabOS LangChain initialization complete")

        return True

    except Exception as e:
        print(f"❌ Error initializing LabOS with LangChain: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==========================================
# Helper functions for backward compatibility
# ==========================================

def run_query(query: str, conversation_history: Optional[List] = None, callbacks: Optional[List[BaseCallbackHandler]] = None) -> Dict[str, Any]:
    """
    Run a query through the LangChain agent
    Backward compatible with existing API

    Args:
        query: User's input query
        conversation_history: Optional list of previous messages
        callbacks: Optional list of callback handlers for streaming/monitoring

    Returns:
        Dict with 'output' (final answer) and 'steps' (execution trace)
    """
    if langchain_agent is None:
        raise RuntimeError("LangChain agent not initialized. Call initialize_langchain_labos() first.")

    return langchain_agent.run(query, conversation_history=conversation_history, callbacks=callbacks)


def get_agent() -> Optional[LangChainAgent]:
    """
    Get the current agent instance

    Returns:
        The current LangChainAgent instance, or None if not initialized
    """
    global langchain_agent
    return langchain_agent


def get_agent_info() -> Dict[str, Any]:
    """Get information about the current agent"""
    if langchain_agent is None:
        return {"initialized": False}

    return {
        "initialized": True,
        "model_type": type(current_model).__name__,
        "tools_count": len(langchain_agent.tools),
        "max_iterations": langchain_agent.max_iterations,
    }
