"""
LabOS AI Core Module

This module contains the core LabOS AI functionality:
- Knowledge Base management
- Memory management
- LabOS engine and wrapper
- Integration bridge
"""

from .knowledge_base import KnowledgeBase, Mem0EnhancedKnowledgeBase, MEM0_AVAILABLE
from .memory_manager import MemoryManager

__all__ = [
    'KnowledgeBase',
    'Mem0EnhancedKnowledgeBase', 
    'MEM0_AVAILABLE',
    'MemoryManager'
]
