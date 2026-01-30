"""
MCP Server Integration

This module handles MCP (Model Context Protocol) server connections:
- PubMed MCP Server for medical literature search
- Future: Additional MCP servers for scientific research
"""

import os
from mcp import StdioServerParameters
from smolagents import MCPClient
from ...config import EXTERNAL_APIS


def setup_mcp_tools():
    """Setup MCP tools for biomedical and scientific research.

    Returns:
        List of MCP tool instances
    """
    mcp_tools = []

    # --- PubMed MCP Server (proven to work) ---
    try:
        pubmed_tool_name = EXTERNAL_APIS["pubmed"]["tool_name"]
        pubmed_server_params = StdioServerParameters(
            command="uvx",
            args=["--quiet", pubmed_tool_name],
            env={"UV_PYTHON": "3.12", **os.environ},
        )

        print("🔬 Connecting to PubMed MCP server...")
        pubmed_client = MCPClient(pubmed_server_params)
        pubmed_tools = pubmed_client.get_tools()
        mcp_tools.extend(pubmed_tools)
        print(f"✅ Successfully connected to PubMed MCP server, obtained {len(pubmed_tools)} tools")

    except Exception as e:
        print(f"⚠️ PubMed MCP server connection failed: {e}")

    return mcp_tools
