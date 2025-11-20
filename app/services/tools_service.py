"""
Tools Service - Separate service for tool management
Handles tool discovery, listing, and management independently from LabOSService
"""

from typing import List, Dict, Any
import inspect

class ToolsService:
    """Service for managing and discovering tools"""
    
    def __init__(self):
        self.labos_service = None
    
    def set_labos_service(self, labos_service):
        """Set reference to LabOSService"""
        self.labos_service = labos_service
    
    async def get_tools(self) -> List[Dict]:
        """Get list of available base tools"""
        try:
            tools = []
            
            # Get tools from predefined module
            try:
                from app.tools import predefined
                predefined_tools = []
                
                for name, obj in inspect.getmembers(predefined):
                    if hasattr(obj, '__class__') and 'SimpleTool' in str(type(obj)):
                        tool_info = {
                            "id": name,
                            "name": name.replace('_', ' ').title(),
                            "description": getattr(obj, 'description', 'No description available'),
                            "category": self._categorize_tool(name),
                            "parameters": self._extract_tool_parameters(obj),
                            "status": "available",
                            "usage_count": 0,
                            "last_used": None
                        }
                        predefined_tools.append(tool_info)
                
                tools.extend(predefined_tools)
                
            except Exception as e:
                print(f"Error loading predefined tools: {e}")
            
            # Add some default tools that are always available
            default_tools = [
                {
                    "id": "web_search",
                    "name": "Web Search",
                    "description": "Search the web for current information",
                    "category": "research",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query", "required": True}
                    ],
                    "status": "available",
                    "usage_count": 0,
                    "last_used": None
                },
                {
                    "id": "visit_webpage", 
                    "name": "Visit Webpage",
                    "description": "Visit and extract content from a webpage",
                    "category": "research",
                    "parameters": [
                        {"name": "url", "type": "string", "description": "URL to visit", "required": True}
                    ],
                    "status": "available",
                    "usage_count": 0,
                    "last_used": None
                },
                {
                    "id": "enhanced_google_search",
                    "name": "Enhanced Google Search", 
                    "description": "Enhanced Google search with reliable implementation",
                    "category": "research",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query", "required": True},
                        {"name": "num_results", "type": "integer", "description": "Number of results", "required": False}
                    ],
                    "status": "available",
                    "usage_count": 0,
                    "last_used": None
                },
                {
                    "id": "query_pubmed",
                    "name": "PubMed Search",
                    "description": "Search PubMed for biomedical literature",
                    "category": "academic",
                    "parameters": [
                        {"name": "query", "type": "string", "description": "Search query", "required": True},
                        {"name": "max_papers", "type": "integer", "description": "Maximum papers to retrieve", "required": False}
                    ],
                    "status": "available",
                    "usage_count": 0,
                    "last_used": None
                }
            ]
            
            tools.extend(default_tools)
            return tools

        except Exception as e:
            print(f"Error getting tools: {e}")
            return []
    
    async def get_dynamic_tools(self) -> List[Dict]:
        """Get dynamically created tools"""
        try:
            tools = []
            
            # Get tools from LabOS manager agent if available
            if (self.labos_service and 
                hasattr(self.labos_service, 'manager_agent') and 
                self.labos_service.manager_agent and 
                hasattr(self.labos_service.manager_agent, 'tools')):
                
                for tool_name, tool in getattr(self.labos_service.manager_agent, 'tools', {}).items():
                    tool_info = {
                        "id": getattr(tool, 'name', tool_name),
                        "name": getattr(tool, 'name', tool_name),
                        "description": getattr(tool, 'description', 'No description available'),
                        "category": "dynamic",
                        "parameters": self._extract_tool_parameters(tool),
                        "status": "available",
                        "usage_count": 0,
                        "last_used": None
                    }
                    tools.append(tool_info)
            
            return tools
            
        except Exception as e:
            print(f"Error getting dynamic tools: {e}")
            return []
    
    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize tool based on name"""
        name_lower = tool_name.lower()
        
        if any(keyword in name_lower for keyword in ['search', 'google', 'web', 'query']):
            return 'research'
        elif any(keyword in name_lower for keyword in ['pubmed', 'arxiv', 'scholar', 'doi']):
            return 'academic'
        elif any(keyword in name_lower for keyword in ['github', 'code', 'script', 'run']):
            return 'development'
        elif any(keyword in name_lower for keyword in ['conda', 'pip', 'install', 'env']):
            return 'environment'
        elif any(keyword in name_lower for keyword in ['extract', 'pdf', 'content', 'webpage']):
            return 'content'
        else:
            return 'general'
    
    def _extract_tool_parameters(self, tool) -> List[Dict]:
        """Extract tool parameters from tool object"""
        try:
            if hasattr(tool, 'inputs'):
                return [
                    {
                        "name": name,
                        "type": info.get("type", "string"),
                        "description": info.get("description", ""),
                        "required": info.get("required", False)
                    }
                    for name, info in tool.inputs.items()
                ]
            else:
                # Try to extract from function signature
                if hasattr(tool, '__call__'):
                    sig = inspect.signature(tool)
                    params = []
                    for param_name, param in sig.parameters.items():
                        params.append({
                            "name": param_name,
                            "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "string",
                            "description": f"Parameter: {param_name}",
                            "required": param.default == inspect.Parameter.empty
                        })
                    return params
        except Exception as e:
            print(f"Error extracting tool parameters: {e}")
        
        return []
    
# Global tools service instance
tools_service = ToolsService()
