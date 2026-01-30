"""
LABOS AI Unified Configuration Settings

Centralized configuration management for the entire application.
All modules should import configurations from this file.

Configuration sources (in priority order):
1. Environment variables (.env and cloudbuild.yaml) - for secrets and env-specific settings
2. YAML configuration (config/app_config.yaml) - for non-secret application settings
3. Defaults in this file
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from app.config.yaml_config import get_yaml_config, load_yaml_config

# Load environment variables
load_dotenv()

# Load YAML configuration
yaml_config = load_yaml_config()

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
APP_DIR = BASE_DIR / "app"
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = Path(__file__).parent / "prompts"

# Environment (always from .env, not YAML - environment-specific)
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
# DEPRECATED: V1 Smolagents AI_MODELS configuration removed
# V2 uses config/llm_models.yaml for per-agent LLM configuration
# Keeping minimal config for backward compatibility with legacy code

AI_MODELS = {
    # V1 DEPRECATED - OpenRouter API (Smolagents engine disabled)
    # V2 uses llm_models.yaml instead
    "parameters": {
        "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.1")),
        "max_tokens": int(os.getenv("MODEL_MAX_TOKENS", "4096")),
    }
}

# === LABOS Core Configuration ===
# Load from YAML first, fallback to env vars
LABOS_CONFIG = {
    "use_template": get_yaml_config("labos.use_template", os.getenv("LABOS_USE_TEMPLATE", "true").lower() == "true"),
    "enable_tool_creation": get_yaml_config("labos.enable_tool_creation", os.getenv("LABOS_ENABLE_TOOL_CREATION", "true").lower() == "true"),
    "use_default_prompts": get_yaml_config("labos.use_default_prompts", os.getenv("LABOS_USE_DEFAULT_PROMPTS", "false").lower() == "true"),
    "max_parallel_workers": get_yaml_config("labos.max_parallel_workers", int(os.getenv("LABOS_MAX_PARALLEL_WORKERS", "3"))),
    "tool_timeout": get_yaml_config("labos.tool_timeout", int(os.getenv("LABOS_TOOL_TIMEOUT", "30"))),
    "cache_ttl": get_yaml_config("labos.cache_ttl", int(os.getenv("LABOS_CACHE_TTL", "300"))),
}

# === Server Configuration ===
# CORS: Priority is env var > yaml > default
_cors_env = os.getenv("CORS_ORIGINS")
_cors_origins = _cors_env.split(",") if _cors_env else get_yaml_config("server.cors_origins", ["http://localhost:3000", "http://127.0.0.1:3000"])

SERVER_CONFIG = {
    "host": get_yaml_config("server.host", os.getenv("HOST", "0.0.0.0")),
    "port": int(os.getenv("PORT", get_yaml_config("server.port", 18800))),
    "debug": DEBUG,
    "reload": False,  # Disabled to prevent LABOS output files from triggering restarts
    "reload_dirs": ["app"] if DEBUG else None,  # Only watch app directory, ignore data/outputs
    "reload_excludes": ["data/**", "*.log", "*.tmp"] if DEBUG else None,
    "cors_origins": _cors_origins,
}

# === Database Configuration ===
DATABASE_CONFIG = {
    "url": os.getenv("DATABASE_URL", "sqlite:///./labos.db"),
    "echo": DEBUG,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# === WebSocket Configuration ===
WEBSOCKET_CONFIG = {
    "url": get_yaml_config("websocket.url", os.getenv("WEBSOCKET_URL", "ws://localhost:8000/ws")),
    "reconnect_attempts": get_yaml_config("websocket.reconnect_attempts", int(os.getenv("WEBSOCKET_RECONNECT_ATTEMPTS", "5"))),
    "reconnect_delay": get_yaml_config("websocket.reconnect_delay", int(os.getenv("WEBSOCKET_RECONNECT_DELAY", "5"))),
    "ping_interval": get_yaml_config("websocket.ping_interval", int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))),
    "ping_timeout": get_yaml_config("websocket.ping_timeout", int(os.getenv("WS_PING_TIMEOUT", "180"))),
    "max_connections": get_yaml_config("websocket.max_connections", int(os.getenv("WS_MAX_CONNECTIONS", "100"))),
    "receive_timeout": get_yaml_config("websocket.receive_timeout", int(os.getenv("WS_RECEIVE_TIMEOUT", "120"))),
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
    "max_file_size": get_yaml_config("file_storage.max_file_size", int(os.getenv("MAX_FILE_SIZE", "10485760"))),
    "allowed_extensions": get_yaml_config("file_storage.allowed_extensions", [".txt", ".csv", ".json", ".yaml", ".yml", ".py", ".md", ".png", ".jpg", ".pdf"]),
}

# === Logging Configuration ===
LOGGING_CONFIG = {
    "level": get_yaml_config("logging.level", os.getenv("LOG_LEVEL", "INFO")),
    "format": get_yaml_config("logging.format", "json"),
    "file": DATA_DIR / "logs" / "labos.log",
    "max_size": get_yaml_config("logging.max_size", int(os.getenv("LOG_MAX_SIZE", "10485760"))),
    "backup_count": get_yaml_config("logging.backup_count", int(os.getenv("LOG_BACKUP_COUNT", "5"))),
}

# === Gmail OAuth2 Configuration ===
GMAIL_CONFIG = {
    "user": os.getenv("GMAIL_USER", "labos.agent2026@gmail.com"),
    "client_id": os.getenv("GMAIL_CLIENT_ID", ""),  # Secret
    "client_secret": os.getenv("GMAIL_CLIENT_SECRET", ""),  # Secret
    "refresh_token": os.getenv("GMAIL_REFRESH_TOKEN", ""),  # Secret
    "access_token": os.getenv("GMAIL_ACCESS_TOKEN", ""),  # Secret
    "from_name": os.getenv("FROM_NAME", "LABOS AI Team"),
}

# === External API Configuration ===
EXTERNAL_APIS = {
    "pubmed": {
        "base_url": get_yaml_config("external_apis.pubmed.base_url", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"),
        "email": os.getenv("PUBMED_EMAIL", ""),  # Secret
        "api_key": os.getenv("PUBMED_API_KEY", ""),  # Secret
        "tool_name": get_yaml_config("external_apis.pubmed.tool_name", "pubmedmcp@0.1.3"),
    },
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY", ""),  # Secret (from .env)
        "base_url": get_yaml_config("external_apis.openai.base_url", "https://api.openai.com/v1"),
        "organization": os.getenv("OPENAI_ORGANIZATION", ""),  # Secret
    },
    "serpapi": {
        "api_key": os.getenv("SERPAPI_API_KEY", ""),  # Secret
    },
    "github": {
        "token": os.getenv("GITHUB_TOKEN", ""),  # Secret
    }
}

# === Environment URLs ===
# Priority: Environment variables > YAML defaults
FRONTEND_URL = os.getenv("FRONTEND_URL", get_yaml_config("urls.default.frontend", "http://localhost:3000"))
BACKEND_URL = os.getenv("BACKEND_URL", get_yaml_config("urls.default.backend", "http://localhost:18800"))

ENVIRONMENT_URLS = {
    "frontend_url": FRONTEND_URL,
    "backend_url": BACKEND_URL,
}

# === Tool Configuration ===
TOOLS_CONFIG = {
    "tools_directory": APP_DIR / "tools",
    "dynamic_tools_directory": APP_DIR / "tools" / "dynamic",
    "predefined_tools_file": APP_DIR / "tools" / "predefined.py",
    "auto_load_tools": get_yaml_config("tools.auto_load", os.getenv("AUTO_LOAD_TOOLS", "true").lower() == "true"),
    "max_tools_per_query": get_yaml_config("tools.max_tools_per_query", int(os.getenv("MAX_TOOLS_PER_QUERY", "20"))),
    "loading_cache_size": get_yaml_config("tools.loading_cache_size", 100),
    "template_cache_size": get_yaml_config("tools.template_cache_size", 50),
    "retry_max_attempts": get_yaml_config("tools.retry.max_attempts", 3),
    "retry_delay": get_yaml_config("tools.retry.delay", 1),
}

# === Memory System Configuration ===
MEMORY_CONFIG = {
    "enable_memory": os.getenv("ENABLE_MEMORY", "false").lower() == "true",  # From .env (env-specific)
    "knowledge_base_file": DATA_DIR / "outputs" / "agent_knowledge_base.json",
    "auto_memory_max_tasks": get_yaml_config("memory.auto_memory.max_tasks", 100),
    "auto_memory_max_errors": get_yaml_config("memory.auto_memory.max_errors", 50),
    "template_cache_size": get_yaml_config("tools.template_cache_size", 50),
}

# === Performance Configuration ===
PERFORMANCE_CONFIG = {
    "retry_max_attempts": get_yaml_config("tools.retry.max_attempts", 3),
    "retry_delay": get_yaml_config("tools.retry.delay", 1),
    "tool_loading_cache_size": get_yaml_config("tools.loading_cache_size", 100),
    "parallel_execution_timeout": get_yaml_config("performance.parallel_execution_timeout", 300),
}

# === Phoenix Tracing Configuration ===
PHOENIX_CONFIG = {
    "collector_endpoint": get_yaml_config("phoenix.collector_endpoint", "http://localhost:6006"),
    "enable_tracing": get_yaml_config("phoenix.enabled", False),
}

# === Utility Functions ===
def get_prompt_path(prompt_name: str) -> Path:
    """Get the path to a specific prompt file."""
    return PROMPTS_DIR / f"{prompt_name}.yaml"

def get_current_urls() -> Dict[str, str]:
    """Get URLs for current environment."""
    return ENVIRONMENT_URLS

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

    # V1 DEPRECATED - OpenRouter API key check removed
    # V2 uses GOOGLE_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY instead

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