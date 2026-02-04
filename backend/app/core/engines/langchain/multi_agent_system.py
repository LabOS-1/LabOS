"""
LangChain Multi-Agent System for LABOS V2

This module implements a multi-agent architecture matching Smolagents V1 design:
- dev_agent: Code execution and tool calling
- tool_creation_agent: Dynamic tool generation
- critic_agent: Quality evaluation
- manager_agent: Coordination and delegation

Key difference from Smolagents:
- Uses LangChain's tool calling instead of CodeAgent
- Agents communicate through explicit tool interface
- Manager agent has access to delegate tasks to sub-agents
"""

from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import yaml
import base64
import threading
import contextvars

# Context variable to track the active MultiAgentSystem during execution
# This allows tools (e.g., save_tool_to_sandbox) to access the running system
_active_system: contextvars.ContextVar[Optional['MultiAgentSystem']] = contextvars.ContextVar(
    '_active_system', default=None
)

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.callbacks import BaseCallbackHandler

from .langchain_engine import LangChainAgent, create_model

# Import new LLM configuration layer
from app.core.llm.factory import LLMFactory
from app.core.llm.config import LLMConfig, get_default_agent_configs


@dataclass(frozen=True)
class MultiAgentConfig:
    """
    Immutable configuration for multi-agent system

    Thread Safety:
    - Frozen dataclass = immutable after creation
    - Safe to share across workflows without locks
    - Tools stored as tuples (immutable) instead of lists

    Usage:
        # Create config once at startup
        config = MultiAgentConfig(
            base_tools=tuple(base_tools),
            manager_tools=tuple(manager_tools),
            mode="deep",
            verbose=False
        )

        # Share config across all workflows (thread-safe)
        system = MultiAgentSystem.from_config(config)
    """
    base_tools: Tuple[Any, ...] = field(default_factory=tuple)
    manager_tools: Tuple[Any, ...] = field(default_factory=tuple)
    mode: str = "deep"
    verbose: bool = False

    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.mode not in ("deep", "fast"):
            raise ValueError(f"Invalid mode: {self.mode}. Must be 'deep' or 'fast'")

        # Ensure tools are tuples (immutable)
        if not isinstance(self.base_tools, tuple):
            object.__setattr__(self, 'base_tools', tuple(self.base_tools))
        if not isinstance(self.manager_tools, tuple):
            object.__setattr__(self, 'manager_tools', tuple(self.manager_tools))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "base_tools_count": len(self.base_tools),
            "manager_tools_count": len(self.manager_tools),
            "mode": self.mode,
            "verbose": self.verbose
        }


def load_agent_prompts() -> Dict[str, Any]:
    """
    Load agent prompts from agent_prompts.yaml (V1 configuration)

    Returns:
        Dictionary with prompts for each agent
    """
    try:
        app_dir = Path(__file__).resolve().parents[3]
        prompts_path = app_dir / "config" / "prompts" / "agent_prompts.yaml"

        with open(prompts_path, 'r', encoding='utf-8') as f:
            prompts = yaml.safe_load(f)

        print(f"✅ Loaded agent prompts from: {prompts_path}")
        return prompts
    except Exception as e:
        print(f"⚠️  Could not load agent prompts: {e}")
        return {}


def load_langchain_agent_prompt(agent_name: str) -> str:
    """
    Load LangChain-specific agent prompt from langchain/ folder

    Args:
        agent_name: Name of the agent (e.g., "dev_agent", "manager_agent")

    Returns:
        System prompt string for the agent
    """
    try:
        app_dir = Path(__file__).resolve().parents[3]
        prompt_path = app_dir / "config" / "prompts" / "langchain" / f"{agent_name}.yaml"

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_config = yaml.safe_load(f)

        system_prompt = prompt_config.get('system_prompt', '')
        print(f"✅ Loaded {agent_name} prompt from: langchain/{agent_name}.yaml")
        return system_prompt
    except Exception as e:
        print(f"⚠️  Could not load {agent_name} prompt: {e}")
        return f"You are the {agent_name.replace('_', ' ').title()} in LABOS."


def load_manager_prompt(mode: str = "deep") -> str:
    """
    Load manager agent prompt from LangChain-specific prompt files

    Args:
        mode: "deep" for full workflow, "fast" for quick responses

    Returns:
        System prompt string for manager agent
    """
    if mode == "fast":
        # Load Fast Mode prompt (smolagents format but works for LangChain too)
        import yaml
        from pathlib import Path

        try:
            app_dir = Path(__file__).resolve().parents[3]
            fast_prompt_path = app_dir / "config" / "prompts" / "LabOS_prompt_fast_mode.yaml"

            with open(fast_prompt_path, 'r', encoding='utf-8') as f:
                fast_prompt_config = yaml.safe_load(f)

            system_prompt = fast_prompt_config.get('system_prompt', '')
            print(f"⚡ Fast Mode prompt loaded from: {fast_prompt_path}")
            return system_prompt
        except Exception as e:
            print(f"⚠️  Could not load Fast Mode prompt: {e}")
            # Fallback to basic fast mode prompt
            return """You are LABOS in Fast Mode ⚡. You can only answer from your knowledge (up to January 2025).
You have NO tools, NO web search, NO code execution. For advanced features, tell users to switch to Deep Mode 🧠."""
    else:
        # Deep Mode: use standard manager prompt
        return load_langchain_agent_prompt("manager_agent")


@dataclass
class AgentMetadata:
    """Metadata about a registered agent"""
    name: str
    role: str
    description: str
    tools_count: int


class MultiAgentConversation:
    """Tracks conversation between agents for context sharing"""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []

    def add_message(self, agent_name: str, content: str, metadata: Optional[Dict] = None):
        """Add a message from an agent to the conversation"""
        self.messages.append({
            "agent": agent_name,
            "content": content,
            "metadata": metadata or {}
        })

    def get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """Get recent messages for context"""
        return self.messages[-limit:]

    def format_for_display(self) -> str:
        """Format conversation for display in prompts"""
        if not self.messages:
            return "No agent conversation history."

        lines = []
        for msg in self.messages[-5:]:  # Last 5 for brevity
            lines.append(f"[{msg['agent']}]: {msg['content'][:150]}...")
        return "\n".join(lines)


class MultiAgentSystem:
    """
    Multi-Agent System matching Smolagents V1 architecture

    Agents:
    - dev_agent: Handles code execution, data analysis, tool calling
    - tool_creation_agent: Creates new tools dynamically
    - critic_agent: Evaluates quality and provides feedback
    - manager_agent: Coordinates and delegates to sub-agents

    The manager_agent can delegate tasks to other agents using special tools.

    Thread Safety:
    - Each instance is independent (no shared state)
    - Safe to create multiple instances concurrently
    - Use from_config() class method for config-based creation
    """

    def __init__(self, verbose: bool = False):
        self.agents: Dict[str, LangChainAgent] = {}
        self.agent_metadata: Dict[str, AgentMetadata] = {}
        self.manager_agent: Optional[LangChainAgent] = None
        self.conversation = MultiAgentConversation()
        self.verbose = verbose

    @classmethod
    def from_config(cls, config: MultiAgentConfig, verbose: Optional[bool] = None) -> 'MultiAgentSystem':
        """
        Create MultiAgentSystem from immutable configuration (thread-safe)

        This is the recommended way to create systems from config objects.

        Args:
            config: Immutable MultiAgentConfig instance
            verbose: Optional verbose override (if None, uses config.verbose)

        Returns:
            Configured MultiAgentSystem instance

        Example:
            config = MultiAgentConfig(base_tools=(...), manager_tools=(...))
            system = MultiAgentSystem.from_config(config)
        """
        system = cls(verbose=verbose if verbose is not None else config.verbose)

        # Register agents using config tools
        _register_agents_to_system(
            system,
            list(config.base_tools),  # Convert immutable tuple to list
            list(config.manager_tools),
            config.mode,
            verbose if verbose is not None else config.verbose
        )

        return system

    def _create_strategic_planning_tool(self, agent_name: str = "manager_agent") -> Callable:
        """
        Create a tool for outputting strategic planning/thinking.

        This allows agents to CHOOSE when to show thinking to the user.

        Args:
            agent_name: Name of the agent using this tool (for display purposes)

        Returns:
            Tool function for broadcasting thinking
        """
        # Map agent names to display info
        agent_display = {
            "manager_agent": {"emoji": "📋", "title": "Manager Planning", "max_chars": 1500},
            "dev_agent": {"emoji": "🔬", "title": "Dev Agent Analysis", "max_chars": 500},
            "critic_agent": {"emoji": "🔍", "title": "Critic Agent Review", "max_chars": 500},
            "tool_creation_agent": {"emoji": "🔧", "title": "Tool Creation Planning", "max_chars": 500},
        }
        display_info = agent_display.get(agent_name, {"emoji": "💭", "title": f"{agent_name} Thinking", "max_chars": 500})
        max_chars = display_info["max_chars"]

        @tool
        def output_thinking(reasoning: str) -> str:
            """Output your thinking, analysis, or reasoning process to the user. Use this to show your thought process before executing tasks.

            Args:
                reasoning: Your analysis and reasoning (plain text, concise)

            Returns:
                Confirmation message
            """
            # Emit as a workflow step
            from app.services.workflows import get_workflow_context, workflow_event_queue
            from app.services.workflows.workflow_events import WorkflowEvent
            from datetime import datetime

            step_title = f"{display_info['emoji']} {display_info['title']}"
            reasoning_text = reasoning[:max_chars]

            context = get_workflow_context()
            if context:
                workflow_id = context.workflow_id
                step_counter = context.step_counter
                step_counter['count'] += 1

                planning_step_data = {
                    "step_type": "step",
                    "title": step_title,
                    "description": reasoning_text,
                    "step_number": step_counter['count'],
                    "timestamp": datetime.now().isoformat(),
                    "agent": agent_name
                }

                workflow_event_queue.put(WorkflowEvent(
                    workflow_id=workflow_id,
                    event_type="step",
                    timestamp=datetime.now(),
                    step_number=step_counter['count'],
                    title=step_title,
                    description=reasoning_text
                ))

                if context.ws_callback and hasattr(context.ws_callback, 'collected_steps'):
                    context.ws_callback.collected_steps.append(planning_step_data)

            print(f"\n{display_info['emoji']} {agent_name} Thinking:\n{reasoning_text}\n")
            return "Your thinking has been displayed. Proceed with execution."

        output_thinking.name = "output_thinking"
        return output_thinking

    def _create_delegation_tool(self, agent_name: str, agent_description: str) -> Callable:
        """
        Create a delegation tool for a specific agent

        Args:
            agent_name: Name of the agent (e.g., 'dev_agent')
            agent_description: Description of the agent's capabilities

        Returns:
            Tool function that delegates to the agent
        """
        # Create tool with proper docstring (langchain-core 0.3.39+ requires docstring)
        # We cannot use f-string in docstring directly with @tool, so create function first
        def create_delegate_func(agent_name: str, description: str):
            def delegate_task(task: str) -> str:
                """Placeholder - will be replaced"""
                return self._execute_on_agent(agent_name, task)

            # Set docstring before applying @tool decorator
            delegate_task.__doc__ = f"Delegate a task to {agent_name}. {description[:200]}"
            return delegate_task

        # Create function with docstring
        func = create_delegate_func(agent_name, agent_description)

        # Apply @tool decorator
        delegate_tool = tool(func)

        # Set tool name
        delegate_tool.name = f"ask_{agent_name}"

        return delegate_tool

    def _execute_on_agent(self, agent_name: str, task: str) -> str:
        """
        Execute a task on a specific agent

        Args:
            agent_name: Name of the agent
            task: Task to execute

        Returns:
            Agent's response
        """
        if agent_name not in self.agents:
            return f"Error: Agent {agent_name} not found"

        agent = self.agents[agent_name]

        # Log delegation
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🎯 Delegating to {agent_name}")
            print(f"Task: {task[:100]}...")
            print(f"{'='*60}\n")

        # Add to conversation history
        self.conversation.add_message(
            agent_name="manager_agent",
            content=f"Delegated to {agent_name}: {task}",
            metadata={"type": "delegation"}
        )

        # Get conversation context
        recent_messages = self.conversation.get_recent_messages(limit=5)
        history_context = []

        # Format recent agent conversations as context
        for msg in recent_messages:
            if msg["agent"] == agent_name:
                history_context.append(AIMessage(content=msg["content"]))
            else:
                history_context.append(HumanMessage(content=f"[{msg['agent']}]: {msg['content']}"))

        # Execute task
        try:
            result = agent.run(
                query=task,
                conversation_history=history_context
            )

            response = result.get("output", "")

            # If max iterations was reached, extract useful info from completed steps
            # so the manager knows what was actually accomplished
            if result.get("error") == "max_iterations_reached":
                steps = result.get("steps", [])
                successful_tools = []
                for step in steps:
                    for tc in step.get("tool_calls", []):
                        if tc.get("success") and tc.get("tool"):
                            tool_result_str = str(tc.get("result", ""))[:300]
                            successful_tools.append(f"- {tc['tool']}: {tool_result_str}")

                if successful_tools:
                    response = (
                        f"Task partially completed ({len(successful_tools)} tool calls executed "
                        f"but agent ran out of iterations before producing a final summary).\n\n"
                        f"Completed actions:\n" + "\n".join(successful_tools)
                    )

                if self.verbose:
                    print(f"⚠️ {agent_name} hit max_iterations, extracted {len(successful_tools)} tool results")

            # Add response to conversation
            self.conversation.add_message(
                agent_name=agent_name,
                content=response,
                metadata={
                    "success": result.get("success", True),
                    "steps": len(result.get("steps", []))
                }
            )

            if self.verbose:
                print(f"✅ {agent_name} completed task")
                print(f"Response length: {len(response)} chars\n")

            return response

        except Exception as e:
            error_msg = f"Error in {agent_name}: {str(e)}"
            self.conversation.add_message(
                agent_name=agent_name,
                content=error_msg,
                metadata={"type": "error"}
            )
            return error_msg

    def register_dev_agent(
        self,
        tools: List[Any],
        model: Any = None,
        model_type: str = "gemini",
        temperature: float = 0.1,
        llm_config: Optional['LLMConfig'] = None
    ) -> LangChainAgent:
        """
        Register dev_agent - handles visualization, research, and tool-based operations

        Args:
            tools: List of tools available to dev_agent
            model: Optional pre-created LangChain model instance (takes precedence over all)
            model_type: Model type (gemini, claude, gpt) - DEPRECATED, use llm_config instead
            temperature: Model temperature - DEPRECATED, use llm_config instead
            llm_config: Optional LLMConfig for flexible model configuration (recommended)

        Returns:
            Created dev_agent

        Note:
            Priority: model > llm_config > (model_type, temperature)
        """
        # Load LangChain-specific prompt from YAML
        system_prompt = load_langchain_agent_prompt("dev_agent")

        # Create thinking tool for dev_agent
        thinking_tool = self._create_strategic_planning_tool("dev_agent")
        all_tools = list(tools) + [thinking_tool]

        # Use provided model or create one
        if model is None:
            if llm_config is not None:
                # Use LLMConfig (recommended way)
                from app.core.llm.factory import LLMFactory
                model = LLMFactory.create(llm_config)
            else:
                # Fallback to old model_type/temperature API (backward compatibility)
                model = create_model(
                    model_type=model_type,
                    temperature=temperature,
                )

        agent = LangChainAgent(
            model=model,
            tools=all_tools,
            system_prompt=system_prompt,
            max_iterations=10,
            verbose=self.verbose
        )

        self.agents["dev_agent"] = agent
        self.agent_metadata["dev_agent"] = AgentMetadata(
            name="dev_agent",
            role="execution",
            description="Handles code execution, data analysis, and tool calling",
            tools_count=len(all_tools)
        )

        if self.verbose:
            print(f"✅ Registered dev_agent with {len(all_tools)} tools (including output_thinking)")

        return agent

    def register_tool_creation_agent(
        self,
        tools: List[Any],
        model: Any = None,
        model_type: str = "gemini",
        temperature: float = 0.1,
        llm_config: Optional['LLMConfig'] = None
    ) -> LangChainAgent:
        """
        Register tool_creation_agent - creates new tools dynamically

        Args:
            tools: List of tools available (should include tool creation tools)
            model: Optional pre-created LangChain model instance (takes precedence over all)
            model_type: Model type - DEPRECATED, use llm_config instead
            temperature: Model temperature - DEPRECATED, use llm_config instead
            llm_config: Optional LLMConfig for flexible model configuration (recommended)

        Returns:
            Created tool_creation_agent

        Note:
            Priority: model > llm_config > (model_type, temperature)
        """
        # Load LangChain-specific prompt from YAML
        system_prompt = load_langchain_agent_prompt("tool_creation_agent")

        # Create thinking tool for tool_creation_agent
        thinking_tool = self._create_strategic_planning_tool("tool_creation_agent")
        all_tools = list(tools) + [thinking_tool]

        # Use provided model or create one
        if model is None:
            if llm_config is not None:
                from app.core.llm.factory import LLMFactory
                model = LLMFactory.create(llm_config)
            else:
                model = create_model(
                    model_type=model_type,
                    temperature=temperature,
                )

        agent = LangChainAgent(
            model=model,
            tools=all_tools,
            system_prompt=system_prompt,
            max_iterations=8,
            verbose=self.verbose
        )

        self.agents["tool_creation_agent"] = agent
        self.agent_metadata["tool_creation_agent"] = AgentMetadata(
            name="tool_creation_agent",
            role="tool_creation",
            description="Creates and tests new tools dynamically",
            tools_count=len(all_tools)
        )

        if self.verbose:
            print(f"✅ Registered tool_creation_agent with {len(all_tools)} tools (including output_thinking)")

        return agent

    def register_critic_agent(
        self,
        tools: List[Any],
        model: Any = None,
        model_type: str = "gemini",
        temperature: float = 0.2,
        llm_config: Optional['LLMConfig'] = None
    ) -> LangChainAgent:
        """
        Register critic_agent - evaluates quality and provides feedback

        Args:
            tools: List of tools available
            model: Optional pre-created LangChain model instance (takes precedence over all)
            model_type: Model type - DEPRECATED, use llm_config instead
            temperature: Model temperature (slightly higher for creative evaluation) - DEPRECATED
            llm_config: Optional LLMConfig for flexible model configuration (recommended)

        Returns:
            Created critic_agent

        Note:
            Priority: model > llm_config > (model_type, temperature)
        """
        # Load LangChain-specific prompt from YAML
        system_prompt = load_langchain_agent_prompt("critic_agent")

        # Use provided model or create one
        if model is None:
            if llm_config is not None:
                from app.core.llm.factory import LLMFactory
                model = LLMFactory.create(llm_config)
            else:
                model = create_model(
                    model_type=model_type,
                    temperature=temperature,
                )

        agent = LangChainAgent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            max_iterations=6,
            verbose=self.verbose
        )

        self.agents["critic_agent"] = agent
        self.agent_metadata["critic_agent"] = AgentMetadata(
            name="critic_agent",
            role="evaluation",
            description="Evaluates quality and provides feedback",
            tools_count=len(tools)
        )

        if self.verbose:
            print(f"✅ Registered critic_agent with {len(tools)} tools")

        return agent

    def register_follow_up_agent(
        self,
        model: Any = None,
        temperature: float = 0.3,
        llm_config: Optional['LLMConfig'] = None
    ) -> LangChainAgent:
        """
        Register follow_up_agent - generates follow-up questions after responses

        This agent is called after the main workflow completes to generate
        insightful follow-up questions for the user.

        Args:
            model: Optional pre-created LangChain model instance
            temperature: Model temperature (slightly higher for variety)
            llm_config: Optional LLMConfig for flexible model configuration

        Returns:
            Created follow_up_agent

        Note:
            - Uses no tools (pure LLM generation)
            - Uses lightweight model for fast response (gemini-1.5-flash)
            - Not registered in agent_metadata (not delegatable)
        """
        # Load LangChain-specific prompt from YAML
        system_prompt = load_langchain_agent_prompt("follow_up_agent")

        # Use provided model or create one (prefer lightweight/fast model for quick generation)
        if model is None:
            if llm_config is not None:
                from app.core.llm.factory import LLMFactory
                model = LLMFactory.create(llm_config)
            else:
                # Use lightweight flash model for fast follow-up generation
                import os
                from app.core.llm.factory import LLMFactory
                from app.core.llm.config import LLMConfig
                # Use GEMINI_FLASH_MODEL for speed, fallback to gemini-3-flash-preview
                flash_model = os.getenv("GEMINI_FLASH_MODEL", "gemini-3-flash-preview")
                config = LLMConfig(
                    provider="gemini",
                    model=flash_model,
                    temperature=temperature,
                    max_tokens=512  # Small output for follow-up questions
                )
                model = LLMFactory.create(config)
                print(f"⚡ Follow-up agent using fast model: {flash_model}")

        # No tools needed - pure LLM generation
        agent = LangChainAgent(
            model=model,
            tools=[],  # No tools
            system_prompt=system_prompt,
            max_iterations=1,  # Single pass
            verbose=self.verbose
        )

        self.agents["follow_up_agent"] = agent
        # Note: Not adding to agent_metadata as it's not delegatable

        if self.verbose:
            print(f"✅ Registered follow_up_agent (no tools, single-pass)")

        return agent

    def register_manager_agent(
        self,
        tools: List[Any],
        model: Any = None,
        model_type: str = "gemini",
        temperature: float = 0.1,
        mode: str = "deep",
        system_prompt_override: Optional[str] = None,
        llm_config: Optional['LLMConfig'] = None
    ) -> LangChainAgent:
        """
        Register manager_agent - coordinates and delegates to sub-agents

        The manager agent gets special delegation tools to communicate with other agents.

        Args:
            tools: Base tools for manager
            model: Optional pre-created LangChain model instance (takes precedence over all)
            model_type: Model type - DEPRECATED, use llm_config instead
            temperature: Model temperature - DEPRECATED, use llm_config instead
            mode: "deep" for full workflow, "fast" for quick responses
            system_prompt_override: Optional custom system prompt
            llm_config: Optional LLMConfig for flexible model configuration (recommended)

        Returns:
            Created manager_agent

        Note:
            Priority: model > llm_config > (model_type, temperature)
        """
        # In Fast Mode, no delegation tools or planning (pure LLM response)
        if mode == "fast":
            print(f"⚡ Fast Mode: Manager agent with NO tools (pure LLM)")
            all_tools = []  # No tools at all in Fast Mode
        else:
            # Deep Mode: Create delegation tools for each registered agent
            delegation_tools = []
            for agent_name, metadata in self.agent_metadata.items():
                tool_func = self._create_delegation_tool(agent_name, metadata.description)
                delegation_tools.append(tool_func)

            # Create strategic planning tool for manager
            planning_tool = self._create_strategic_planning_tool("manager_agent")

            # Combine base tools with delegation tools and planning tool
            all_tools = tools + delegation_tools + [planning_tool]
            print(f"🧠 Deep Mode: Manager agent with {len(all_tools)} tools (delegation + planning)")

        # Build system prompt with agent information
        if system_prompt_override:
            system_prompt = system_prompt_override
        else:
            # Load manager prompt from YAML file
            system_prompt = load_manager_prompt(mode=mode)

        # Use provided model or create one
        if model is None:
            if llm_config is not None:
                from app.core.llm.factory import LLMFactory
                model = LLMFactory.create(llm_config)
            else:
                model = create_model(
                    model_type=model_type,
                    temperature=temperature,
                )

        agent = LangChainAgent(
            model=model,
            tools=all_tools,
            system_prompt=system_prompt,
            max_iterations=15,  # More iterations for coordination
            verbose=self.verbose
        )

        self.manager_agent = agent
        self.agents["manager_agent"] = agent
        self.agent_metadata["manager_agent"] = AgentMetadata(
            name="manager_agent",
            role="coordinator",
            description="Coordinates and delegates to specialized agents",
            tools_count=len(all_tools)
        )

        if self.verbose:
            print(f"✅ Registered manager_agent with {len(all_tools)} tools")
            print(f"   - Base tools: {len(tools)}")
            print(f"   - Delegation tools: {len(delegation_tools)}")

        return agent

    def run(
        self,
        query: Union[str, List],
        conversation_history: Optional[List] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None
    ) -> Dict[str, Any]:
        """
        Run the multi-agent system with a user query

        The manager_agent receives the query and coordinates other agents as needed.

        Args:
            query: User's input query (string or list for multimodal content)
                  - String: "Describe this image"
                  - List: [{"type": "text", "text": "..."}, {"type": "media", "data": "...", "mime_type": "..."}]
            conversation_history: Optional conversation history from database
            callbacks: Optional callback handlers

        Returns:
            Dict with 'output', 'steps', 'agents_involved'
        """
        if not self.manager_agent:
            raise RuntimeError("Manager agent not initialized. Call register_manager_agent() first.")

        # Get workflow context for event emission
        from app.services.workflows import get_workflow_context, workflow_event_queue
        from app.services.workflows.workflow_events import WorkflowEvent
        from datetime import datetime

        context = get_workflow_context()
        workflow_id = context.workflow_id if context else None

        # Emit start workflow step (like V1)
        if workflow_id and context:
            step_counter = context.step_counter
            step_counter['count'] += 1

            # Extract query text for description (handle both string and multimodal list)
            if isinstance(query, str):
                query_text = query[:100]
            else:
                # Extract text from multimodal content
                text_parts = [item.get("text", "") for item in query if item.get("type") == "text"]
                query_text = " ".join(text_parts)[:100] if text_parts else "Multimodal query"

            # Create start step data
            start_step_data = {
                "step_type": "step",
                "title": "Start Multi-Agent Processing",
                "description": f"Manager coordinating task: {query_text}...",
                "step_number": step_counter['count'],
                "timestamp": datetime.now().isoformat()
            }

            # Emit to WebSocket via queue
            workflow_event_queue.put(WorkflowEvent(
                workflow_id=workflow_id,
                event_type="step",
                timestamp=datetime.now(),
                step_number=step_counter['count'],
                title="Start Multi-Agent Processing",
                description=f"Manager coordinating task: {query_text}..."
            ))

            # CRITICAL: Also add to callback's collected_steps for database persistence
            if context.ws_callback and hasattr(context.ws_callback, 'collected_steps'):
                context.ws_callback.collected_steps.append(start_step_data)
                print(f"✅ Added start step to collected_steps (will be saved to DB)")

            print(f"✅ Emitted start workflow step for: {workflow_id}")

        # Add user query to conversation
        self.conversation.add_message(
            agent_name="user",
            content=query,
            metadata={"type": "user_query"}
        )

        # Prepare conversation history
        full_history = conversation_history or []

        # Set this system as the active one so tools can access it
        token = _active_system.set(self)
        try:
            # Run manager agent
            result = self.manager_agent.run(
                query=query,
                conversation_history=full_history,
                callbacks=callbacks
            )
        finally:
            _active_system.reset(token)

        # Add manager's response to conversation
        self.conversation.add_message(
            agent_name="manager_agent",
            content=result.get("output", ""),
            metadata={
                "type": "final_answer",
                "success": result.get("success", True)
            }
        )

        # NOTE: Complete step is emitted in chat_projects.py after executor completes
        # This ensures all callback events are processed before the Complete step

        # Add metadata about agent involvement
        result["agents_involved"] = list(self.agents.keys())
        result["conversation_messages"] = len(self.conversation.messages)

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get status of the multi-agent system"""
        return {
            "total_agents": len(self.agents),
            "manager_initialized": self.manager_agent is not None,
            "agents": {
                name: {
                    "role": meta.role,
                    "description": meta.description,
                    "tools": meta.tools_count
                }
                for name, meta in self.agent_metadata.items()
            },
            "conversation_length": len(self.conversation.messages)
        }

    def generate_follow_up_questions(
        self,
        user_query: str,
        ai_response: str
    ) -> List[str]:
        """
        Generate follow-up questions using Google Gemini SDK directly.

        Uses native JSON structured output (response_mime_type + response_schema)
        which is more reliable than LangChain's with_structured_output wrapper.

        Args:
            user_query: The original user question
            ai_response: The AI's response

        Returns:
            List of follow-up question strings (3-5 questions)
        """
        from google import genai
        from google.genai import types
        import os
        import json

        try:
            # Load system prompt from YAML
            system_prompt = load_langchain_agent_prompt("follow_up_agent")

            flash_model = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")
            api_key = os.getenv("GOOGLE_API_KEY")

            if not api_key:
                print("⚠️ GOOGLE_API_KEY not set, skipping follow-up questions")
                return []

            # Create client
            client = genai.Client(api_key=api_key)

            # Define JSON schema for structured output
            response_schema = {
                "type": "object",
                "properties": {
                    "follow_up_questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of 3-5 follow-up questions"
                    }
                },
                "required": ["follow_up_questions"]
            }

            print(f"⚡ Generating follow-up questions via Gemini SDK ({flash_model})...")

            # Build prompt with system instruction
            prompt = f"""{system_prompt}

User Query: {user_query}

AI Response: {ai_response[:1500]}"""

            # Generate with native JSON mode
            response = client.models.generate_content(
                model=flash_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.5,
                    max_output_tokens=1024,
                )
            )

            # Parse response
            result = json.loads(response.text)
            questions = result.get("follow_up_questions", [])

            # Filter out incomplete questions
            questions = [q for q in questions if q.strip().endswith('?')]

            if not questions:
                print(f"⚠️ No valid questions in response")
                print(f"📝 Raw response: {response.text[:300]}...")
                return []

            print(f"✅ Generated {len(questions)} follow-up questions via Gemini SDK")
            print(f"📝 Questions: {questions}")

            return questions[:5]

        except Exception as e:
            import traceback
            print(f"⚠️ Failed to generate follow-up questions: {e}")
            traceback.print_exc()
            return []


# ==========================================
# Global Configuration Singleton (Thread-Safe)
# ==========================================
# Replaces mutable global variables with immutable config pattern
# Thread-safe: Uses lock for config updates, immutable config for reads
#
# Migration from V1 global variables:
# - OLD: _global_base_tools, _global_manager_tools, _global_mode, _global_verbose
# - NEW: _global_config (MultiAgentConfig - immutable and thread-safe)
# ==========================================

class _ConfigManager:
    """
    Thread-safe singleton for managing global multi-agent configuration

    Design Pattern:
    - Singleton with double-check locking
    - Stores immutable MultiAgentConfig instance
    - Safe for concurrent workflow creation
    """
    _instance = None
    _lock = threading.RLock()
    _config: Optional[MultiAgentConfig] = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def set_config(self, config: MultiAgentConfig):
        """Thread-safe config update"""
        with self._lock:
            self._config = config

    def get_config(self) -> Optional[MultiAgentConfig]:
        """Thread-safe config read (no lock needed for immutable object)"""
        return self._config

    def is_configured(self) -> bool:
        """Check if config has been set"""
        return self._config is not None


# Global config manager instance
_config_manager = _ConfigManager()


def initialize_multi_agent_system(
    base_tools: List[Any],
    manager_tools: List[Any],
    mode: str = "deep",
    verbose: bool = False
) -> MultiAgentSystem:
    """
    Initialize the multi-agent system configuration (thread-safe).

    IMPORTANT: This does NOT create agent instances - it only stores the immutable configuration.
    Actual agent instances are created per-workflow via create_workflow_multi_agent_system()
    to ensure complete user isolation.

    Thread Safety:
    - Creates immutable MultiAgentConfig
    - Stored in thread-safe _ConfigManager
    - Safe to call from multiple threads

    Args:
        base_tools: Tools for dev_agent and other specialized agents
        manager_tools: Tools for manager_agent
        mode: "deep" for full workflow, "fast" for quick responses
        verbose: Enable verbose logging

    Returns:
        A temporary MultiAgentSystem instance (for compatibility)
    """
    # Create immutable config (thread-safe)
    config = MultiAgentConfig(
        base_tools=tuple(base_tools),  # Convert to tuple for immutability
        manager_tools=tuple(manager_tools),
        mode=mode,
        verbose=verbose
    )

    # Store config in thread-safe manager
    _config_manager.set_config(config)

    if verbose:
        print(f"\n🚀 Multi-Agent System Configuration Initialized (mode: {mode}, thread-safe)")
        print(f"   Base tools: {len(base_tools)}, Manager tools: {len(manager_tools)}")
        print(f"   ⚠️  NOTE: Agent instances will be created per-workflow for user isolation")

    # Return a temporary instance for compatibility (will not be used)
    system = MultiAgentSystem(verbose=verbose)
    _register_agents_to_system(system, list(config.base_tools), list(config.manager_tools), mode, verbose)
    return system


def create_workflow_multi_agent_system(verbose: bool = False, mode: Optional[str] = None) -> MultiAgentSystem:
    """
    Create a new MultiAgentSystem instance for a specific workflow (thread-safe).

    This ensures complete isolation between concurrent workflows:
    - Each workflow gets its own agent instances
    - No shared mutable state between users/projects
    - Thread-safe by design (immutable config, no locks needed for read)

    Thread Safety:
    - Reads immutable MultiAgentConfig from _ConfigManager
    - Creates fresh agent instances (no state sharing)
    - Safe to call concurrently from multiple workflows

    Args:
        verbose: Enable verbose logging
        mode: Override mode ("fast" or "deep"). If None, uses config mode.

    Returns:
        New MultiAgentSystem instance with fresh agents

    Raises:
        RuntimeError: If system not configured (call initialize_multi_agent_system first)
    """
    # Get immutable config (thread-safe read)
    config = _config_manager.get_config()

    if config is None:
        raise RuntimeError(
            "Multi-agent system not configured. "
            "Call initialize_multi_agent_system() first to set up tools."
        )

    # Use override mode if provided, otherwise use config mode
    effective_mode = mode if mode is not None else config.mode

    # Create a fresh system instance (mode is handled by _register_agents_to_system)
    system = MultiAgentSystem(verbose=verbose or config.verbose)

    # Register fresh agents with the configured tools
    # Convert tuples back to lists for compatibility with existing code
    _register_agents_to_system(
        system,
        list(config.base_tools),  # Convert immutable tuple to list
        list(config.manager_tools),
        effective_mode,  # Use effective mode (override or config)
        verbose or config.verbose
    )

    if verbose or config.verbose:
        print(f"✅ Created fresh Multi-Agent System instance for workflow (mode={effective_mode})")

    return system


def _register_agents_to_system(
    system: MultiAgentSystem,
    base_tools: List[Any],
    manager_tools: List[Any],
    mode: str,
    verbose: bool,
    agent_llm_configs: Optional[Dict[str, LLMConfig]] = None
):
    """
    Register all agents to a MultiAgentSystem instance.

    Args:
        system: MultiAgentSystem instance to register agents to
        base_tools: Tools for specialized agents
        manager_tools: Tools for manager agent
        mode: Execution mode
        verbose: Enable verbose logging
        agent_llm_configs: Optional LLM configs for each agent (from get_default_agent_configs or user override)
    """
    # Load default configs if not provided
    if agent_llm_configs is None:
        agent_llm_configs = get_default_agent_configs()

    # Create LLM instances for each agent
    dev_config = agent_llm_configs.get("dev_agent")
    dev_model = LLMFactory.create(dev_config) if dev_config else None

    tool_config = agent_llm_configs.get("tool_creation_agent")
    tool_model = LLMFactory.create(tool_config) if tool_config else None

    critic_config = agent_llm_configs.get("critic_agent")
    critic_model = LLMFactory.create(critic_config) if critic_config else None

    manager_config = agent_llm_configs.get("manager")

    # In Fast Mode with Gemini: Enable Google Search grounding
    if mode == "fast" and manager_config and manager_config.provider.lower() == "gemini":
        print(f"⚡ Fast Mode: Enabling Google Search grounding for Gemini")
        # Add google_search to extra_params
        manager_config.extra_params["google_search"] = True

    manager_model = LLMFactory.create(manager_config) if manager_config else None

    # In Fast Mode: Only register manager agent (no specialized agents)
    if mode == "fast":
        print(f"⚡ Fast Mode: Registering ONLY manager agent (no specialized agents)")
        if manager_model:
            system.register_manager_agent(tools=manager_tools, mode=mode, model=manager_model)
        else:
            system.register_manager_agent(tools=manager_tools, mode=mode)
    else:
        # Deep Mode: Register all agents in order
        # 1. Dev agent (visualization, research, tool-based operations)
        if dev_model:
            system.register_dev_agent(tools=base_tools, model=dev_model)
        else:
            system.register_dev_agent(tools=base_tools)

        # 2. Tool creation agent (dynamic tool generation)
        if tool_model:
            system.register_tool_creation_agent(tools=base_tools, model=tool_model)
        else:
            system.register_tool_creation_agent(tools=base_tools)

        # 3. Critic agent (quality evaluation)
        if critic_model:
            system.register_critic_agent(tools=base_tools, model=critic_model)
        else:
            system.register_critic_agent(tools=base_tools)

        # 4. Manager agent (must be last to get delegation tools)
        if manager_model:
            system.register_manager_agent(tools=manager_tools, mode=mode, model=manager_model)
        else:
            system.register_manager_agent(tools=manager_tools, mode=mode)

    if verbose:
        print("\n" + "="*80)
        print("🤖 LABOS Multi-Agent System V2 Initialized")
        print("="*80)
        status = system.get_status()
        print(f"Total agents: {status['total_agents']}")
        for name, info in status['agents'].items():
            print(f"  - {name}: {info['role']} ({info['tools']} tools)")
        print("="*80 + "\n")


def get_active_multi_agent_system() -> Optional[MultiAgentSystem]:
    """
    Get the currently active MultiAgentSystem from the execution context.

    This returns the actual running system instance (set via context variable
    in MultiAgentSystem.run()), allowing tools like save_tool_to_sandbox
    to load new tools into the live agents.

    Returns:
        The active MultiAgentSystem, or None if no system is currently running.
    """
    return _active_system.get(None)


def get_multi_agent_system() -> Optional[MultiAgentSystem]:
    """
    DEPRECATED: Use get_active_multi_agent_system() instead.

    Falls back to the active system context variable. If no active system,
    returns a fresh instance (legacy behavior).
    """
    # First try the active system (preferred)
    active = get_active_multi_agent_system()
    if active is not None:
        return active

    # Legacy fallback: create a fresh instance
    if not _config_manager.is_configured():
        return None
    return create_workflow_multi_agent_system()


def run_multi_agent_query(
    query: str,
    conversation_history: Optional[List] = None,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run a query through the multi-agent system.

    IMPORTANT: This creates a fresh MultiAgentSystem instance for each query
    to ensure complete user/workflow isolation. No state is shared between calls.

    Args:
        query: User query
        conversation_history: Optional chat history
        callbacks: Optional callbacks
        mode: Override mode ("fast" or "deep"). If None, uses config mode.

    Returns:
        Dict with output and metadata
    """
    # Create a fresh system instance for this query (user isolation)
    # Pass mode to override the config mode if specified
    system = create_workflow_multi_agent_system(verbose=False, mode=mode)

    if not system:
        raise RuntimeError("Multi-agent system not configured. Call initialize_multi_agent_system() first.")

    # Run query on the fresh instance
    return system.run(query, conversation_history, callbacks)


def generate_follow_up_questions(
    user_query: str,
    ai_response: str,
    max_questions: int = 5
) -> List[str]:
    """
    Generate follow-up questions based on the conversation.

    This creates a lightweight agent specifically for follow-up generation.

    Args:
        user_query: The original user question
        ai_response: The AI's response
        max_questions: Maximum number of questions to generate (default: 5)

    Returns:
        List of follow-up question strings
    """
    try:
        # Create a minimal system just for follow-up generation
        system = MultiAgentSystem(verbose=False)

        # Register only the follow-up agent (lightweight)
        system.register_follow_up_agent()

        # Generate questions
        questions = system.generate_follow_up_questions(user_query, ai_response)

        return questions[:max_questions]

    except Exception as e:
        print(f"⚠️ Failed to generate follow-up questions: {e}")
        return []
