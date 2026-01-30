"""
Integrations Module

This module provides external service integrations:
- MCP Server Setup: Connect to Model Context Protocol servers
- Future: Additional external service integrations
"""

from .mcp_setup import setup_mcp_tools

__all__ = [
    "setup_mcp_tools",
]
