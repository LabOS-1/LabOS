"""
Agent Factory - Create and Configure Agents

This module provides factory functions for creating all agents:
- create_dev_agent: Code execution specialist
- create_tool_creation_agent: Tool creation specialist
- create_critic_agent: Quality evaluation specialist
- create_manager_agent: Main coordinator with custom prompts
- create_all_agents: Unified function to create all agents
"""

from smolagents import ToolCallingAgent, CodeAgent
from .memory_wrapper import create_memory_enabled_agent
from .agent_config import (
    get_dev_agent_config,
    get_tool_creation_agent_config,
    get_critic_agent_config,
    get_manager_agent_config,
    get_authorized_imports
)
from .prompt_loader import (
    load_agent_prompts,
    load_custom_prompts,
    render_prompt_templates,
    get_template_variables
)


def create_dev_agent(model, tools, agent_prompts=None):
    """Create dev_agent with tools and callbacks.

    Args:
        model: LLM model to use
        tools: List of tools available to the agent
        agent_prompts: Optional agent prompts configuration

    Returns:
        Configured dev_agent with memory recording enabled
    """
    config = get_dev_agent_config(agent_prompts)

    agent = ToolCallingAgent(
        tools=tools,
        model=model,
        **config
    )

    # Add task instructions if available
    if agent_prompts and 'dev_agent' in agent_prompts:
        agent.prompt_templates["managed_agent"]["task"] += agent_prompts['dev_agent']['task_instructions']

    # Register workflow callback for tool call tracking
    from ...services.workflows import agent_aware_callback
    agent._setup_step_callbacks([agent_aware_callback])
    print("✅ Registered workflow callback for dev_agent")

    # Enable automatic memory recording
    agent = create_memory_enabled_agent(agent, "dev_agent")

    return agent


def create_tool_creation_agent(model, tools, agent_prompts=None):
    """Create tool_creation_agent for writing new tools.

    Args:
        model: LLM model to use
        tools: List of tools available to the agent
        agent_prompts: Optional agent prompts configuration

    Returns:
        Configured tool_creation_agent with memory recording enabled
    """
    config = get_tool_creation_agent_config(agent_prompts)

    agent = ToolCallingAgent(
        tools=tools,
        model=model,
        **config
    )

    # Add task instructions if available
    if agent_prompts and 'tool_creation_agent' in agent_prompts:
        agent.prompt_templates["managed_agent"]["task"] += agent_prompts['tool_creation_agent']['task_instructions']

    # Register workflow callback for tool call tracking
    from ...services.workflows import agent_aware_callback
    agent._setup_step_callbacks([agent_aware_callback])
    print("✅ Registered workflow callback for tool_creation_agent")

    # Enable automatic memory recording
    agent = create_memory_enabled_agent(agent, "tool_creation_agent")

    return agent


def create_critic_agent(model, tools, agent_prompts=None):
    """Create critic_agent for intelligent evaluation.

    Args:
        model: LLM model to use
        tools: List of tools available to the agent
        agent_prompts: Optional agent prompts configuration

    Returns:
        Configured critic_agent with memory recording enabled
    """
    config = get_critic_agent_config(agent_prompts)

    agent = ToolCallingAgent(
        tools=tools,
        model=model,
        **config
    )

    # Add task instructions if available
    if agent_prompts and 'critic_agent' in agent_prompts:
        agent.prompt_templates["managed_agent"]["task"] += agent_prompts['critic_agent']['task_instructions']

    # Register workflow callback for tool call tracking
    from ...services.workflows import agent_aware_callback
    agent._setup_step_callbacks([agent_aware_callback])
    print("✅ Registered workflow callback for critic_agent")

    # Enable automatic memory recording
    agent = create_memory_enabled_agent(agent, "critic_agent")

    return agent


def create_manager_agent(model, tools, managed_agents, use_template=True, agent_prompts=None, mode='deep'):
    """Create manager_agent with custom prompts.

    Args:
        model: LLM model to use
        tools: List of tools available to the agent
        managed_agents: List of managed agent instances
        use_template: Whether to use custom prompt templates
        agent_prompts: Agent prompts configuration
        mode: Execution mode - 'deep' (full workflow) or 'fast' (quick responses). Default: 'deep'

    Returns:
        Configured manager_agent with memory recording enabled
    """
    config = get_manager_agent_config(agent_prompts, use_template)
    authorized_imports = get_authorized_imports()

    # Load custom prompts if requested
    if use_template:
        custom_prompts = load_custom_prompts(mode=mode)
        if custom_prompts:
            # Render templates with variables
            # In Fast Mode, managed_agents is empty, so skip agent references
            if mode == 'fast' or len(managed_agents) == 0:
                template_vars = get_template_variables(
                    managed_agents={},  # Empty dict for Fast Mode
                    tools=tools
                )
            else:
                template_vars = get_template_variables(
                    managed_agents={
                        'dev_agent': managed_agents[0],
                        'critic_agent': managed_agents[1],
                        'tool_creation_agent': managed_agents[2]
                    },
                    tools=tools
                )
            rendered_templates = render_prompt_templates(custom_prompts, template_vars)
            print("✅ Custom prompt templates rendered with Jinja variables")

            # Use simplified callback for workflow events
            from ...services.workflows import create_agent_with_simple_callbacks

            agent = create_agent_with_simple_callbacks(
                CodeAgent,
                tools=tools,
                model=model,
                managed_agents=managed_agents,
                additional_authorized_imports=authorized_imports,
                prompt_templates=rendered_templates,
                **config
            )
        else:
            # Fallback to default templates
            agent = CodeAgent(
                tools=tools,
                model=model,
                managed_agents=managed_agents,
                additional_authorized_imports=authorized_imports,
                **config
            )
    else:
        # Use default templates
        agent = CodeAgent(
            tools=tools,
            model=model,
            managed_agents=managed_agents,
            additional_authorized_imports=authorized_imports,
            **config
        )

    # Enable automatic memory recording
    agent = create_memory_enabled_agent(agent, "manager_agent")

    print(f"🔧 Manager agent has {len(agent.tools)} tools available")
    print(f"✅ Manager agent created: {type(agent).__name__}")

    return agent


def create_all_agents(models, base_tools, mcp_tools, manager_tools, use_template=True):
    """Create all 4 agents and return them.

    Args:
        models: Dictionary with model instances (claude_model, gpt_model, manager_model)
        base_tools: List of base tools for dev_agent
        mcp_tools: List of MCP tools to add
        manager_tools: List of tools for manager_agent
        use_template: Whether to use custom prompt templates

    Returns:
        Tuple of (dev_agent, tool_creation_agent, critic_agent, manager_agent)
    """
    # Load agent prompts
    agent_prompts = load_agent_prompts()

    # Import save_tool_to_database for tool creation agent
    from ..tool_manager import save_tool_to_database
    from ...tools.core import save_agent_file

    # Create tool creation agent
    # ⚡ OPTIMIZATION: Minimal toolset for faster tool creation
    # Removed search/research tools (WebSearch, GitHub tools) - they slow down creation significantly
    # Tool creation agent should focus on writing code, not researching
    tool_creation_tools = [
        # Tool storage functions (CORE - required for saving tools)
        save_tool_to_database,  # Save tools to database
        save_agent_file,  # Save files to database (for testing/demo)
    ]

    tool_creation_agent = create_tool_creation_agent(
        model=models['gpt_model'],
        tools=tool_creation_tools,
        agent_prompts=agent_prompts
    )

    # Create dev_agent
    all_dev_tools = base_tools + mcp_tools
    dev_agent = create_dev_agent(
        model=models['claude_model'],
        tools=all_dev_tools,
        agent_prompts=agent_prompts
    )

    # Create critic agent
    from ...tools.predefined import run_shell_command, visit_webpage
    from smolagents import WebSearchTool

    critic_tools = [
        WebSearchTool(),
        visit_webpage,
        run_shell_command,
    ]

    critic_agent = create_critic_agent(
        model=models['manager_model'],
        tools=critic_tools,
        agent_prompts=agent_prompts
    )

    # Create manager agent
    manager_agent = create_manager_agent(
        model=models['manager_model'],
        tools=manager_tools,
        managed_agents=[dev_agent, critic_agent, tool_creation_agent],
        use_template=use_template,
        agent_prompts=agent_prompts
    )

    return dev_agent, tool_creation_agent, critic_agent, manager_agent
