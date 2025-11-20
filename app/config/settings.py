"""
LabOS AI Unified Configuration Settings

Centralized configuration management for the entire application.
All modules should import configurations from this file.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
APP_DIR = BASE_DIR / "app"
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = Path(__file__).parent / "prompts"

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# API Configuration
API_VERSION = "v1"
API_PREFIX = f"/api"

# === API Keys Management ===
def get_api_key(key_name: str, required: bool = True, fallback: Optional[str] = None) -> str:
    """Get API key from environment variables with proper error handling."""
    api_key = os.getenv(key_name)
    
    if required and not api_key:
        print(f"❌ Missing required API key: {key_name}")
        print(f"💡 Please set {key_name} in your .env file")
        if fallback:
            print(f"🔄 Using fallback value")
            return fallback
        return ""
    elif not api_key:
        print(f"⚠️ Optional API key not set: {key_name}")
        return ""
    
    return api_key

# === AI Model Configuration ===
AI_MODELS = {
    # OpenRouter API Configuration
    "openrouter": {
        "api_key": get_api_key(
            "OPENROUTER_API_KEY_STRING", 
            required=True,
            fallback=" "
        ),
        "base_url": "https://openrouter.ai/api/v1",
        "models": {
            "dev_agent": os.getenv("LabOS_DEV_MODEL", "anthropic/claude-sonnet-4"),
            "manager_agent": os.getenv("LabOS_MANAGER_MODEL", "anthropic/claude-sonnet-4"),
            "critic_agent": os.getenv("LabOS_CRITIC_MODEL", "anthropic/claude-sonnet-4"),
            "tool_creation_agent": os.getenv("LabOS_TOOL_CREATION_MODEL", "anthropic/claude-sonnet-4"),
        }
    },
    # Model Parameters
    "parameters": {
        "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.1")),
        "max_tokens": int(os.getenv("MODEL_MAX_TOKENS", "4096")),
        "max_steps": {
            "dev_agent": int(os.getenv("DEV_AGENT_MAX_STEPS", "20")),
            "manager_agent": int(os.getenv("MANAGER_AGENT_MAX_STEPS", "30")),  # Reduced from 50 to 30
            "critic_agent": int(os.getenv("CRITIC_AGENT_MAX_STEPS", "10")),
            "tool_creation_agent": int(os.getenv("TOOL_CREATION_AGENT_MAX_STEPS", "8")),  # Reduced from 15 to 8 (no research needed)
        }
    }
}

# === LabOS Core Configuration ===
LabOS_CONFIG = {
    "use_mem0": os.getenv("LabOS_USE_MEM0", "true").lower() == "true",
    "use_template": os.getenv("LabOS_USE_TEMPLATE", "true").lower() == "true",
    "enable_tool_creation": os.getenv("LabOS_ENABLE_TOOL_CREATION", "false").lower() == "true",
    "use_default_prompts": os.getenv("LabOS_USE_DEFAULT_PROMPTS", "false").lower() == "true",
    "max_parallel_workers": int(os.getenv("LabOS_MAX_PARALLEL_WORKERS", "3")),
    "tool_timeout": int(os.getenv("LabOS_TOOL_TIMEOUT", "30")),
    "cache_ttl": int(os.getenv("LabOS_CACHE_TTL", "300")),  # 5 minutes
}

# === Server Configuration ===
SERVER_CONFIG = {
    "host": os.getenv("HOST", "0.0.0.0"),
    "port": int(os.getenv("PORT", "18800")),
    "debug": DEBUG,
    "reload": False,  # Disabled to prevent LabOS output files from triggering restarts
    "reload_dirs": ["app"] if DEBUG else None,  # Only watch app directory, ignore data/outputs
    "reload_excludes": ["data/**", "*.log", "*.tmp"] if DEBUG else None,
    "cors_origins": os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
}

# === Database Configuration ===
DATABASE_CONFIG = {
    "url": os.getenv("DATABASE_URL", "sqlite:///./stella.db"),
    "echo": DEBUG,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# === WebSocket Configuration ===
WEBSOCKET_CONFIG = {
    "url": os.getenv("WEBSOCKET_URL", "ws://localhost:8000/ws"),
    "reconnect_attempts": int(os.getenv("WEBSOCKET_RECONNECT_ATTEMPTS", "5")),
    "reconnect_delay": int(os.getenv("WEBSOCKET_RECONNECT_DELAY", "5")),
    "ping_interval": int(os.getenv("WS_HEARTBEAT_INTERVAL", "30")),
    "ping_timeout": int(os.getenv("WS_PING_TIMEOUT", "180")),
    "max_connections": int(os.getenv("WS_MAX_CONNECTIONS", "100")),
    "receive_timeout": int(os.getenv("WS_RECEIVE_TIMEOUT", "120")),
}

# === Security Configuration ===
SECURITY_CONFIG = {
    "secret_key": os.getenv("SECRET_KEY", "stella-ai-secret-key-change-in-production"),
    "algorithm": "HS256",
    "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
}

# === Auth0 Configuration ===
AUTH0_CONFIG = {
    "secret": os.getenv("AUTH0_SECRET", ""),
    "base_url": os.getenv("AUTH0_BASE_URL", "http://localhost:3000"),
    "issuer_base_url": os.getenv("AUTH0_ISSUER_BASE_URL", ""),
    "client_id": os.getenv("AUTH0_CLIENT_ID", ""),
    "client_secret": os.getenv("AUTH0_CLIENT_SECRET", ""),
}

# === File Storage Configuration ===
# Note: All files are now stored in Cloud SQL database via save_agent_file() tool
STORAGE_CONFIG = {
    "max_file_size": int(os.getenv("MAX_FILE_SIZE", "10485760")),  # 10MB
    "allowed_extensions": [".txt", ".csv", ".json", ".yaml", ".yml", ".py", ".md", ".png", ".jpg", ".pdf"],
}

# === Logging Configuration ===
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
    "file": DATA_DIR / "logs" / "stella.log",
    "max_size": int(os.getenv("LOG_MAX_SIZE", "10485760")),  # 10MB
    "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
}

# === External API Configuration ===
EXTERNAL_APIS = {
    "pubmed": {
        "base_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
        "email": os.getenv("PUBMED_EMAIL", ""),
        "api_key": os.getenv("PUBMED_API_KEY", ""),
        "tool_name": os.getenv("PUBMED_TOOL_NAME", "pubmedmcp@0.1.3"),
    },
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "organization": os.getenv("OPENAI_ORGANIZATION", ""),
    },
    "mem0": {
        "api_key": os.getenv("MEM0_API_KEY", ""),
        "platform": os.getenv("MEM0_PLATFORM", "mem0"),
    },
    "serpapi": {
        "api_key": os.getenv("SERPAPI_API_KEY", ""),
    },
    "github": {
        "token": os.getenv("GITHUB_TOKEN", ""),
    }
}

# === Environment URLs ===
ENVIRONMENT_URLS = {
    "development": {
        "frontend_url": os.getenv("DEV_FRONTEND_URL", "http://localhost:3000"),
        "backend_url": os.getenv("DEV_BACKEND_URL", "http://localhost:18800"),
    },
    "production": {
        "frontend_url": os.getenv("PRODUCTION_FRONTEND_URL", "https://stella-agent.com"),
        "backend_url": os.getenv("PRODUCTION_BACKEND_URL", "https://stella-backend-843173980594.us-central1.run.app"),
    }
}

# === Tool Configuration ===
TOOLS_CONFIG = {
    "tools_directory": APP_DIR / "tools",
    "dynamic_tools_directory": APP_DIR / "tools" / "dynamic",
    "predefined_tools_file": APP_DIR / "tools" / "predefined.py",
    "auto_load_tools": os.getenv("AUTO_LOAD_TOOLS", "true").lower() == "true",
    "max_tools_per_query": int(os.getenv("MAX_TOOLS_PER_QUERY", "10")),
}

# === Memory System Configuration ===
MEMORY_CONFIG = {
    "enable_memory": os.getenv("ENABLE_MEMORY", "true").lower() == "true",
    "knowledge_base_file": DATA_DIR / "outputs" / "agent_knowledge_base.json",
    "auto_memory_max_tasks": int(os.getenv("AUTO_MEMORY_MAX_TASKS", "50")),
    "auto_memory_max_errors": int(os.getenv("AUTO_MEMORY_MAX_ERRORS", "20")),
    "template_cache_size": int(os.getenv("TEMPLATE_CACHE_SIZE", "16")),
}

# === Performance Configuration ===
PERFORMANCE_CONFIG = {
    "retry_max_attempts": int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),
    "retry_delay": float(os.getenv("RETRY_DELAY", "1.0")),
    "tool_loading_cache_size": int(os.getenv("TOOL_LOADING_CACHE_SIZE", "100")),
    "parallel_execution_timeout": int(os.getenv("PARALLEL_EXECUTION_TIMEOUT", "30")),
}

# === Phoenix Tracing Configuration ===
PHOENIX_CONFIG = {
    "collector_endpoint": os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006"),
    "enable_tracing": os.getenv("ENABLE_PHOENIX_TRACING", "false").lower() == "true",
}

# === Utility Functions ===
def get_prompt_path(prompt_name: str) -> Path:
    """Get the path to a specific prompt file."""
    return PROMPTS_DIR / f"{prompt_name}.yaml"

def get_current_urls() -> Dict[str, str]:
    """Get URLs for current environment."""
    return ENVIRONMENT_URLS.get(ENVIRONMENT, ENVIRONMENT_URLS["development"])

def get_api_key_safe(service: str, key_name: str) -> str:
    """Safely get API key for external service."""
    if service in EXTERNAL_APIS and key_name in EXTERNAL_APIS[service]:
        return EXTERNAL_APIS[service][key_name]
    return ""

def ensure_directories():
    """Ensure all required directories exist."""
    # Only create necessary directories, file storage uses Cloud SQL database
    directories = [
        DATA_DIR / "logs",  # Logs directory (development only)
        TOOLS_CONFIG["dynamic_tools_directory"],  # Dynamic tools directory
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

def validate_config() -> Dict[str, Any]:
    """Validate configuration and return status."""
    issues = []
    
    # Check required API keys
    if not AI_MODELS["openrouter"]["api_key"]:
        issues.append("Missing OPENROUTER_API_KEY_STRING")
    
    # Check Auth0 configuration
    required_auth0 = ["client_id", "client_secret", "issuer_base_url"]
    for key in required_auth0:
        if not AUTH0_CONFIG[key]:
            issues.append(f"Missing AUTH0_{key.upper()}")
    
    # Check directories
    if not PROMPTS_DIR.exists():
        issues.append(f"Prompts directory not found: {PROMPTS_DIR}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "environment": ENVIRONMENT,
        "debug": DEBUG,
    }

# Initialize directories on import
ensure_directories()

# Set Phoenix environment if enabled
if PHOENIX_CONFIG["enable_tracing"]:
    os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = PHOENIX_CONFIG["collector_endpoint"]

# Configuration validation on import
config_status = validate_config()
if not config_status["valid"]:
    print("⚠️ Configuration issues found:")
    for issue in config_status["issues"]:
        print(f"   - {issue}")
else:
    print("✅ Configuration validation passed")