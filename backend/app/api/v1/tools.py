"""
Tools API - Endpoints for tool management
"""

import json
import logging
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.services.tools_service import tools_service
from app.services.tool_storage_service import tool_storage_service
from app.services.sandbox import get_sandbox_manager

router = APIRouter()
logger = logging.getLogger(__name__)


class CreateToolRequest(BaseModel):
    name: str
    description: str
    category: str
    code: str


def _get_sandbox_my_tools(user_id: str) -> List[Dict[str, Any]]:
    """Read user's tools from sandbox tools_manifest.json files across all projects."""
    my_tools = []
    try:
        sandbox = get_sandbox_manager()
        user_sandbox = sandbox.get_user_sandbox(user_id)

        if not user_sandbox.exists():
            return []

        for project_dir in user_sandbox.iterdir():
            if not project_dir.is_dir():
                continue

            project_id = project_dir.name
            manifest_path = project_dir / sandbox.TOOLS_DIR / sandbox.TOOLS_MANIFEST

            if not manifest_path.exists():
                continue

            try:
                manifest = json.loads(manifest_path.read_text())
                for entry in manifest.get("tools", []):
                    if entry.get("status") != "active":
                        continue
                    my_tools.append({
                        "id": f"{project_id}:{entry['name']}",
                        "name": entry["name"],
                        "description": entry.get("description", ""),
                        "type": "sandbox",
                        "category": entry.get("category", "custom"),
                        "ownership": "personal",
                        "source": "sandbox",
                        "project_id": project_id,
                        "usage_count": 0,
                        "last_used": None,
                        "created_at": entry.get("created_at"),
                    })
            except Exception as e:
                logger.warning(f"Error reading tools manifest for project {project_id}: {e}")

    except Exception as e:
        logger.error(f"Error scanning sandbox for tools: {e}")

    return my_tools


def _parse_sandbox_tool_id(tool_id: str):
    """Parse composite tool_id 'project_id:tool_name' into parts.
    Returns (project_id, tool_name) or (None, None) if not a sandbox ID.
    """
    if ":" in tool_id:
        parts = tool_id.split(":", 1)
        return parts[0], parts[1]
    return None, None


@router.get("")
async def get_tools(
    user_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
):
    """Get all available tools with categorization by ownership"""
    try:
        # Get built-in tools
        tools = await tools_service.get_tools()
        dynamic_tools = await tools_service.get_dynamic_tools()

        # Convert built-in tools to frontend format
        base_tools = []
        for tool in tools:
            base_tools.append({
                "name": tool.get("name", tool.get("id", "Unknown")),
                "description": tool.get("description", "No description available"),
                "type": "base",
                "category": tool.get("category", "general"),
                "ownership": "system",
                "source": "builtin",
                "usage_count": tool.get("usage_count", 0),
                "last_used": tool.get("last_used")
            })

        # Convert dynamic tools to frontend format
        dynamic_tools_formatted = []
        for tool in dynamic_tools:
            dynamic_tools_formatted.append({
                "name": tool.get("name", tool.get("id", "Unknown")),
                "description": tool.get("description", "No description available"),
                "type": "dynamic",
                "category": tool.get("category", "custom"),
                "ownership": "system",
                "source": "builtin",
                "usage_count": tool.get("usage_count", 0),
                "last_used": tool.get("last_used")
            })

        # Get public database tools (still from DB — cross-user sharing)
        public_tools_formatted = []
        try:
            public_tools = await tool_storage_service.get_public_tools()
            for tool in public_tools:
                public_tools_formatted.append({
                    "id": str(tool.id),
                    "name": tool.name,
                    "description": tool.description,
                    "type": "database",
                    "category": tool.category or "custom",
                    "ownership": "public",
                    "source": "database",
                    "is_verified": tool.is_verified,
                    "usage_count": tool.usage_count,
                    "last_used": tool.last_used_at.isoformat() if tool.last_used_at else None,
                    "created_by": tool.user_id
                })
        except Exception as e:
            logger.warning(f"Error fetching public tools: {e}")

        # Get user's tools from sandbox
        my_tools_formatted = []
        if user_id:
            my_tools_formatted = _get_sandbox_my_tools(user_id)

        return {
            "success": True,
            "data": {
                "builtin_tools": base_tools + dynamic_tools_formatted,
                "public_tools": public_tools_formatted,
                "my_tools": my_tools_formatted,
                "mcp_tools": [],
                "total_count": len(base_tools) + len(dynamic_tools_formatted) + len(public_tools_formatted) + len(my_tools_formatted)
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# V1 DEPRECATED - Dynamic tools require Smolagents engine
@router.get("/dynamic")
async def get_dynamic_tools():
    """Get dynamically created tools - DEPRECATED"""
    return {
        "success": False,
        "error": "V1 dynamic tools API is deprecated. V1 Smolagents engine has been disabled."
    }


@router.post("/dynamic")
async def create_dynamic_tool(request: CreateToolRequest):
    """Create a new dynamic tool"""
    try:
        tool = {
            "id": f"dynamic_{request.name.lower().replace(' ', '_')}",
            "name": request.name,
            "description": request.description,
            "category": request.category,
            "parameters": [],
            "usage_count": 0,
            "success_rate": 0.0,
            "avg_execution_time": 0.0,
            "created_at": "2024-01-01T00:00:00Z",
            "is_dynamic": True
        }

        return {
            "success": True,
            "data": tool
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/{tool_id}")
async def get_tool_details(
    tool_id: str,
    user_id: Optional[str] = Query(None)
):
    """Get detailed information about a specific tool"""
    try:
        # Check if this is a sandbox tool (composite ID: project_id:tool_name)
        proj_id, tool_name = _parse_sandbox_tool_id(tool_id)

        if proj_id and tool_name and user_id:
            # Read from sandbox
            sandbox = get_sandbox_manager()
            try:
                tool_code = sandbox.read_tool_code(user_id, proj_id, tool_name)
                tool_entries = sandbox.list_tools(user_id, proj_id)
                entry = next((t for t in tool_entries if t["name"] == tool_name), {})

                return {
                    "success": True,
                    "data": {
                        "id": tool_id,
                        "name": tool_name,
                        "description": entry.get("description", ""),
                        "category": entry.get("category", "custom"),
                        "tool_code": tool_code,
                        "parameters": [],
                        "project_id": proj_id,
                        "usage_count": 0,
                        "is_public": False,
                        "is_verified": False,
                        "status": entry.get("status", "active"),
                        "created_at": entry.get("created_at"),
                        "updated_at": entry.get("created_at"),
                        "created_by": user_id,
                        "created_by_agent": entry.get("created_by_agent", "tool_creation_agent")
                    }
                }
            except FileNotFoundError:
                return {"success": False, "error": "Tool not found"}
        else:
            # Fallback: try DB for old UUID-format IDs
            tool = await tool_storage_service.get_tool_by_id(UUID(tool_id))

            if not tool:
                return {"success": False, "error": "Tool not found"}

            if tool.user_id != user_id and not tool.is_public:
                return {"success": False, "error": "Access denied"}

            return {
                "success": True,
                "data": {
                    "id": str(tool.id),
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category,
                    "tool_code": tool.tool_code,
                    "parameters": tool.parameters,
                    "project_id": str(tool.project_id) if tool.project_id else None,
                    "workflow_id": str(tool.workflow_id) if tool.workflow_id else None,
                    "usage_count": tool.usage_count,
                    "is_public": tool.is_public,
                    "is_verified": tool.is_verified,
                    "status": tool.status,
                    "created_at": tool.created_at.isoformat() if tool.created_at else None,
                    "updated_at": tool.updated_at.isoformat() if tool.updated_at else None,
                    "last_used_at": tool.last_used_at.isoformat() if tool.last_used_at else None,
                    "created_by": tool.user_id,
                    "created_by_agent": tool.created_by_agent
                }
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: str,
    user_id: str = Query(...)
):
    """Delete a tool"""
    try:
        # Check if this is a sandbox tool (composite ID: project_id:tool_name)
        proj_id, tool_name = _parse_sandbox_tool_id(tool_id)

        if proj_id and tool_name:
            sandbox = get_sandbox_manager()
            deleted = sandbox.delete_tool_file(user_id, proj_id, tool_name)

            if deleted:
                return {
                    "success": True,
                    "message": f"Tool '{tool_name}' deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Tool not found"
                }
        else:
            # Fallback: try DB for old UUID-format IDs
            tool = await tool_storage_service.get_tool_by_id(UUID(tool_id))

            if not tool:
                return {"success": False, "error": "Tool not found"}

            if tool.user_id != user_id:
                return {"success": False, "error": "You can only delete your own tools"}

            success = await tool_storage_service.delete_tool(UUID(tool_id), user_id)

            if success:
                return {
                    "success": True,
                    "message": f"Tool '{tool.name}' deleted successfully"
                }
            else:
                return {"success": False, "error": "Failed to delete tool"}

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/stats")
async def get_tool_usage_stats():
    """Get tool usage statistics"""
    try:
        tools = await tools_service.get_tools()
        dynamic_tools = await tools_service.get_dynamic_tools()
        all_tools = tools + dynamic_tools

        stats = {
            "total_tools": len(all_tools),
            "dynamic_tools": len(dynamic_tools),
            "total_usage": sum(tool.get("usage_count", 0) for tool in all_tools),
            "avg_success_rate": sum(tool.get("success_rate", 0) for tool in all_tools) / len(all_tools) if all_tools else 0,
            "categories": {}
        }

        for tool in all_tools:
            category = tool.get("category", "unknown")
            if category not in stats["categories"]:
                stats["categories"][category] = 0
            stats["categories"][category] += 1

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
