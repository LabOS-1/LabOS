"""
Agents Module

This module provides agent creation and management functionality:
- Agent Factory: Create all agent types (dev, tool_creation, critic, manager)
- Agent Configuration: Load and manage agent settings
- Memory Wrapper: Enable automatic memory recording for agents
- Prompt Loader: Load and render agent prompt templates

Exported Components:
- Agent Factory: create_all_agents, create_dev_agent, create_manager_agent, etc.
- Agent Config: get_authorized_imports, agent configuration functions
- Memory Wrapper: create_memory_enabled_agent
- Prompt Loader: load_agent_prompts, load_custom_prompts, render_prompt_templates
"""

from .agent_factory import (
    create_dev_agent,
    create_tool_creation_agent,
    create_critic_agent,
    create_manager_agent,
    create_all_agents
)
from .agent_config import (
    get_dev_agent_config,
    get_tool_creation_agent_config,
    get_critic_agent_config,
    get_manager_agent_config,
    get_authorized_imports,
    VERBOSE_AGENT_LOGS
)
from .memory_wrapper import create_memory_enabled_agent
from .prompt_loader import (
    load_agent_prompts,
    load_custom_prompts,
    render_prompt_templates,
    get_template_variables
)

__all__ = [
    # Agent Factory
    'create_all_agents',
    'create_dev_agent',
    'create_tool_creation_agent',
    'create_critic_agent',
    'create_manager_agent',

    # Agent Config
    'get_dev_agent_config',
    'get_tool_creation_agent_config',
    'get_critic_agent_config',
    'get_manager_agent_config',
    'get_authorized_imports',
    'VERBOSE_AGENT_LOGS',

    # Memory Wrapper
    'create_memory_enabled_agent',

    # Prompt Loader
    'load_agent_prompts',
    'load_custom_prompts',
    'render_prompt_templates',
    'get_template_variables',
]
