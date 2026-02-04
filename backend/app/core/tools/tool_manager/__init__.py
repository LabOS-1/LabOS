"""
Tool Manager Module

This module provides comprehensive tool management functionality for LABOS:
- Dynamic tool loading from files and database
- Intelligent tool selection using LLM
- Parallel tool execution
- Tool creation and registration
- Tool metadata and signature inspection

Exported Components:
- Tool Loader: load_dynamic_tool, load_project_tools, refresh_agent_tools, add_tool_to_agents
- Tool Creator: create_new_tool
- Tool Registry: list_dynamic_tools, get_tool_signature, dynamic_tools_registry
- Parallel Executor: execute_tools_in_parallel
- Intelligent Selector: analyze_query_and_load_relevant_tools
"""

from .tool_loader import (
    load_dynamic_tool,
    load_project_tools,
    refresh_agent_tools,
    add_tool_to_agents
)
from .tool_creator import create_new_tool, save_tool_to_sandbox
from .tool_registry import tool_registry, get_predefined_tools
from .parallel_executor import execute_tools_in_parallel
from .intelligent_selector import analyze_query_and_load_relevant_tools

__all__ = [
    # Tool Loader
    'load_dynamic_tool',
    'load_project_tools',
    'refresh_agent_tools',
    'add_tool_to_agents',

    # Tool Creator
    'create_new_tool',
    'save_tool_to_sandbox',

    # Tool Registry
    'tool_registry',
    'get_predefined_tools',

    # Parallel Executor
    'execute_tools_in_parallel',

    # Intelligent Selector
    'analyze_query_and_load_relevant_tools',
]
