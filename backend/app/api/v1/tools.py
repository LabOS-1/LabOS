"""
Tools API - Endpoints for tool management
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID

# from app.services.labos_service import LabOSService  # V1 DEPRECATED
from app.services.tools_service import tools_service
from app.services.tool_storage_service import tool_storage_service

router = APIRouter()

# V1 Smolagents service disabled
# async def get_labos_service() -> LabOSService:
#     if not hasattr(get_labos_service, "_instance"):
#         get_labos_service._instance = LabOSService()
#         await get_labos_service._instance.initialize()
#         tools_service.set_labos_service(get_labos_service._instance)
#     return get_labos_service._instance

class CreateToolRequest(BaseModel):
    name: str
    description: str
    category: str
    code: str

@router.get("")
async def get_tools(
    user_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
    # labos_service removed - V1 DEPRECATED
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

        # Get public database tools
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
            print(f"Error fetching public tools: {e}")

        # Get user's tools (all projects) if user_id provided
        my_tools_formatted = []
        if user_id:
            try:
                # Get all tools created by this user, regardless of project
                my_tools = await tool_storage_service.get_tools_by_user(
                    user_id=user_id,
                    status="active"
                )
                for tool in my_tools:
                    my_tools_formatted.append({
                        "id": str(tool.id),
                        "name": tool.name,
                        "description": tool.description,
                        "type": "database",
                        "category": tool.category or "custom",
                        "ownership": "personal",
                        "source": "database",
                        "project_id": str(tool.project_id) if tool.project_id else None,
                        "usage_count": tool.usage_count,
                        "last_used": tool.last_used_at.isoformat() if tool.last_used_at else None,
                        "created_at": tool.created_at.isoformat() if tool.created_at else None
                    })
            except Exception as e:
                print(f"Error fetching user tools: {e}")
                import traceback
                traceback.print_exc()

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

# Original implementation commented out:
# async def get_dynamic_tools_OLD(
#     
# ):
    """#Get dynamically created tools"""
    try:
        tools = await tools_service.get_dynamic_tools()
        
        return {
            "success": True,
            "data": tools
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/dynamic")
async def create_dynamic_tool(
    request: CreateToolRequest,
    
):
    """Create a new dynamic tool"""
    try:
        # TODO: Implement dynamic tool creation
        tool = {
            "id": f"dynamic_{request.name.lower().replace(' ', '_')}",
            "name": request.name,
            "description": request.description,
            "category": request.category,
            "parameters": [],  # TODO: Parse from code
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
        # Get tool from database
        tool = await tool_storage_service.get_tool_by_id(UUID(tool_id))

        if not tool:
            return {
                "success": False,
                "error": "Tool not found"
            }

        # Check access permissions
        if tool.user_id != user_id and not tool.is_public:
            return {
                "success": False,
                "error": "Access denied"
            }

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
    """Delete a tool (soft delete)"""
    try:
        # Get tool from database
        tool = await tool_storage_service.get_tool_by_id(UUID(tool_id))

        if not tool:
            return {
                "success": False,
                "error": "Tool not found"
            }

        # Check if user owns this tool
        if tool.user_id != user_id:
            return {
                "success": False,
                "error": "You can only delete your own tools"
            }

        # Soft delete - update status to 'deleted'
        success = await tool_storage_service.delete_tool(UUID(tool_id), user_id)

        if success:
            return {
                "success": True,
                "message": f"Tool '{tool.name}' deleted successfully"
            }
        else:
            return {
                "success": False,
                "error": "Failed to delete tool"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/stats")
async def get_tool_usage_stats(
    
):
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

        # Category breakdown
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
