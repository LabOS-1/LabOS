"""
Configuration module for LabOS AI

Provides centralized configuration management for the entire application.
All modules should import configurations from this module.
"""

from .settings import *

__all__ = [
    # Base paths
    'BASE_DIR',
    'APP_DIR', 
    'DATA_DIR',
    'PROMPTS_DIR',
    
    # Environment
    'ENVIRONMENT',
    'DEBUG',
    'API_VERSION',
    'API_PREFIX',
    
    # Core configurations
    'AI_MODELS',
    'LabOS_CONFIG',
    'SERVER_CONFIG',
    'DATABASE_CONFIG',
    'WEBSOCKET_CONFIG',
    'SECURITY_CONFIG',
    'AUTH0_CONFIG',
    'STORAGE_CONFIG',
    'LOGGING_CONFIG',
    'EXTERNAL_APIS',
    'ENVIRONMENT_URLS',
    'TOOLS_CONFIG',
    'MEMORY_CONFIG',
    'PERFORMANCE_CONFIG',
    'PHOENIX_CONFIG',
    
    # Utility functions
    'get_api_key',
    'get_prompt_path',
    'get_current_urls',
    'get_api_key_safe',
    'ensure_directories',
    'validate_config',
]