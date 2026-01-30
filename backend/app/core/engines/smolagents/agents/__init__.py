"""
Smolagents Agents Module

LEGACY: Most V1 Smolagents agent files have been removed.
Only prompt_loader.py is kept as it's used by V2 LangChain engine.
"""

# V2 still uses prompt loader
from .prompt_loader import load_custom_prompts

__all__ = ['load_custom_prompts']
