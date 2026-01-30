"""
Smolagents Engine Module (LEGACY)

V1 Smolagents engine has been deprecated and removed.
Only tool adapter and prompt loader are kept for V2 LangChain compatibility.
"""

# V2 LangChain utilities (still used)
from .tool_adapter import smolagent_to_langchain, batch_convert_tools
from .agents.prompt_loader import load_custom_prompts

__all__ = [
    'smolagent_to_langchain',
    'batch_convert_tools',
    'load_custom_prompts',
]
