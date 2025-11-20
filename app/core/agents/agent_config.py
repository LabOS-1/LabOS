"""
Agent Configuration Management

This module provides configuration for all agents:
- Agent-specific parameters (max_steps, temperature, etc.)
- Authorized imports for CodeAgent
- Agent descriptions and settings
"""

from smolagents.monitoring import LogLevel
from ...config import AI_MODELS


# Global verbosity setting
VERBOSE_AGENT_LOGS = True  # Set to False to hide detailed logs


def get_dev_agent_config(agent_prompts=None):
    """Get dev_agent configuration.

    Args:
        agent_prompts: Optional agent prompts configuration

    Returns:
        Dictionary of dev_agent configuration
    """
    description = "A specialist agent for code execution and environment management."
    if agent_prompts and 'dev_agent' in agent_prompts:
        description = agent_prompts['dev_agent']['description']

    return {
        'max_steps': AI_MODELS["parameters"]["max_steps"]["dev_agent"],
        'name': "dev_agent",
        'description': description,
        'verbosity_level': LogLevel.INFO if VERBOSE_AGENT_LOGS else LogLevel.ERROR,
    }


def get_tool_creation_agent_config(agent_prompts=None):
    """Get tool_creation_agent configuration.

    Args:
        agent_prompts: Optional agent prompts configuration

    Returns:
        Dictionary of tool_creation_agent configuration
    """
    description = "A specialized agent for creating new Python tools and utilities."
    if agent_prompts and 'tool_creation_agent' in agent_prompts:
        description = agent_prompts['tool_creation_agent']['description']

    return {
        'max_steps': AI_MODELS["parameters"]["max_steps"]["tool_creation_agent"],
        'name': "tool_creation_agent",
        'description': description,
        'verbosity_level': LogLevel.INFO if VERBOSE_AGENT_LOGS else LogLevel.ERROR,
    }


def get_critic_agent_config(agent_prompts=None):
    """Get critic_agent configuration.

    Args:
        agent_prompts: Optional agent prompts configuration

    Returns:
        Dictionary of critic_agent configuration
    """
    description = "Expert critic agent that evaluates task completion quality."
    if agent_prompts and 'critic_agent' in agent_prompts:
        description = agent_prompts['critic_agent']['description']

    return {
        'max_steps': AI_MODELS["parameters"]["max_steps"]["critic_agent"],
        'name': "critic_agent",
        'description': description,
        'verbosity_level': LogLevel.INFO if VERBOSE_AGENT_LOGS else LogLevel.ERROR,
    }


def get_manager_agent_config(agent_prompts=None, use_template=True):
    """Get manager_agent configuration.

    Args:
        agent_prompts: Optional agent prompts configuration
        use_template: Whether custom templates are being used

    Returns:
        Dictionary of manager_agent configuration
    """
    if use_template and agent_prompts and 'manager_agent' in agent_prompts:
        description = agent_prompts['manager_agent']['description_with_template']
    elif agent_prompts and 'manager_agent' in agent_prompts:
        description = agent_prompts['manager_agent']['description_simple']
    else:
        description = "The main coordinator agent with self-evolution capabilities and tool management."

    return {
        'name': "manager_agent",
        'description': description,
        'verbosity_level': LogLevel.INFO if VERBOSE_AGENT_LOGS else LogLevel.ERROR,
        'planning_interval': None,  # Disabled - planning handled in system_prompt
    }


def get_authorized_imports():
    """Get list of authorized imports for CodeAgent.

    Returns:
        List of authorized import strings
    """
    return [
        "time", "datetime", "os", "sys", "json", "csv", "pickle", "pathlib",
        "math", "statistics", "random",
        "numpy", "pandas",
        "collections", "itertools", "functools", "operator",
        "typing", "dataclasses", "enum",
        "xml", "xml.etree", "xml.etree.ElementTree",
        "requests", "urllib", "urllib.parse", "http",
        "re", "unicodedata", "string", "io"  # For StringIO, BytesIO
    ]
