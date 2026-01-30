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

            # List of all tool modules to scan
            tool_modules = [
                'predefined',
                'analysis',
                'database',
                'screening',
                'python_interpreter',
                'workflow',
                'pubmed',
            ]

            # Also scan tools in core and visualization subdirectories
            core_modules = [
                'core.files',
                'core.memory',
                'core.evaluation',
                'core.collaboration',
                'core.knowledge',
            ]

            visualization_modules = [
                'visualization.plotting',
            ]

            all_modules = tool_modules + core_modules + visualization_modules

            # Scan each module for tools
            for module_name in all_modules:
                try:
                    module = __import__(f'app.tools.{module_name}', fromlist=[''])

                    for name, obj in inspect.getmembers(module):
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
                            tools.append(tool_info)

                except Exception as e:
                    print(f"Error loading tools from {module_name}: {e}")

            # Note: Default tools like web_search, visit_webpage, enhanced_google_search,
            # query_pubmed are already defined in predefined.py, so no need to add duplicates

            return tools

        except Exception as e:
            print(f"Error getting tools: {e}")
            return []
    
    async def get_dynamic_tools(self) -> List[Dict]:
        """Get dynamically created tools"""
        try:
            tools = []
            
            # Get tools from LABOS manager agent if available
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
