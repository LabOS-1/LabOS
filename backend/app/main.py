"""
LabOS AI Backend - FastAPI Application
Main entry point for the LabOS AI backend API server.
"""

import os
import sys
import asyncio
import logging
import logging.handlers
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

# Add the parent directory to Python path to import labos modules
sys.path.append(str(Path(__file__).parent.parent))
# Add current directory to path for relative imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import unified configuration
from app.config import (
    SERVER_CONFIG, DATABASE_CONFIG, LOGGING_CONFIG, 
    STORAGE_CONFIG, ENVIRONMENT, DEBUG
)

# Import and setup logging systems
from app.core.infrastructure.cloud_logging import setup_cloud_logging
from app.core.infrastructure.logging_config import setup_logging

# Setup file logging first (captures all output including setup messages)
try:
    setup_logging()
except Exception as e:
    print(f"❌ File logging setup failed: {e}")
    import traceback
    traceback.print_exc()

# Initialize Cloud Logging system
try:
    setup_cloud_logging()
    print("✅ Cloud Logging initialized")
except Exception as e:
    print(f"❌ Cloud Logging setup failed: {e}")
    import traceback
    traceback.print_exc()

# V1 API - Smolagents + OpenRouter
from app.api.v1.chat_projects import router as chat_projects_router
from app.api.v1.agents import router as agents_router
from app.api.v1.tools import router as tools_router
from app.api.v1.files import router as files_router
from app.api.v1.memory import router as memory_router
from app.api.v1.system import router as system_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.gcs import router as gcs_router

# V2 API - LangChain + Direct API
from app.api.v2.chat import router as v2_chat_router
from app.api.v2.chat_projects import router as v2_chat_projects_router
from app.api.v2.agent_config import router as v2_agent_config_router
# from app.services.labos_service import LabOSService  # V1 only - disabled
from app.services.websocket_broadcast import websocket_broadcaster

# Initialize services
# labos_service = LabOSService()  # V1 only - disabled

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""

    from app.core.infrastructure.database import init_database, close_database
    # Startup
    print("🚀 Starting LabOS AI Backend...")
    
    # Logging already setup in module import, just get logger
    logger = logging.getLogger(__name__)
    logger.info("LabOS AI Backend startup initiated")
    
    # Initialize database
    try:
        await init_database()
        logger.info("Database initialized successfully")
        print("✅ Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"❌ Database initialization failed: {e}")
    
    # Initialize LabOS service (V1 only - disabled)
    # try:
    #     await labos_service.initialize()
    #     logger.info("LABOS AI service initialized successfully")
    #     print("✅ LABOS AI service initialized")
    # except Exception as e:
    #     logger.error(f"LABOS AI initialization failed: {e}")
    #     print(f"❌ LABOS AI initialization failed: {e}")

    # WebSocket broadcaster is already initialized and ready to use
    logger.info("LabOS AI Backend startup completed successfully")
    print("✅ LabOS AI Backend started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Starting LabOS AI Backend shutdown")
    print("🛑 Shutting down LabOS AI Backend...")
    try:
        # await labos_service.cleanup()  # V1 only - disabled
        pass  # V2 cleanup handled elsewhere
        await close_database()
        logger.info("LabOS AI Backend shutdown completed successfully")
        print("✅ LabOS AI Backend shutdown complete!")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
        print(f"❌ Shutdown error: {e}")

# Create FastAPI app
app = FastAPI(
    title="LabOS AI Backend",
    description="Backend API for LabOS AI - Intelligent Research Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
# All origins should come from CORS_ORIGINS env var, no hardcoded URLs
app.add_middleware(
    CORSMiddleware,
    allow_origins=SERVER_CONFIG["cors_origins"] + ["file://"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# ==========================================
# API V1 Routers - Smolagents + OpenRouter
# ==========================================
app.include_router(auth_router, prefix="/api/v1/auth", tags=["v1-auth"])
app.include_router(chat_projects_router, prefix="/api/v1/chat", tags=["v1-chat"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["v1-agents"])
app.include_router(tools_router, prefix="/api/v1/tools", tags=["v1-tools"])
app.include_router(files_router, prefix="/api/v1/files", tags=["v1-files"])
app.include_router(memory_router, prefix="/api/v1/memory", tags=["v1-memory"])
app.include_router(system_router, prefix="/api/v1/system", tags=["v1-system"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["v1-admin"])
app.include_router(gcs_router, prefix="/api/v1/gcs", tags=["v1-gcs"])
app.include_router(websocket_router, prefix="", tags=["v1-websocket"])  # No prefix for /ws

# ==========================================
# API V2 Routers - LangChain + Direct API
# ==========================================
app.include_router(v2_chat_router, prefix="/api/v2/chat", tags=["v2-chat"])
app.include_router(v2_chat_projects_router, prefix="/api/v2/chat", tags=["v2-chat-projects"])
app.include_router(v2_agent_config_router, prefix="/api/v2", tags=["v2-agent-config"])

# Serve static files (data/outputs)
if os.path.exists("data/outputs"):
    app.mount("/static", StaticFiles(directory="data/outputs"), name="static")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LabOS AI Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "labos_initialized": True,  # V2 always initialized (no global service)
        "websocket_connections": websocket_broadcaster.get_connection_count()
    }



@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    print(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": str(exc) if os.getenv("DEBUG") else "An unexpected error occurred"
        }
    )

if __name__ == "__main__":
    import uvicorn

    # Get configuration from unified settings
    host = SERVER_CONFIG["host"]
    port = SERVER_CONFIG["port"]
    debug = SERVER_CONFIG["debug"]
    reload = SERVER_CONFIG["reload"]
    reload_dirs = SERVER_CONFIG.get("reload_dirs")
    reload_excludes = SERVER_CONFIG.get("reload_excludes")

    print(f"🚀 Starting LabOS AI Backend on {host}:{port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"🌍 Environment: {ENVIRONMENT}")

    # Build uvicorn config
    uvicorn_config = {
        "app": "main:app",
        "host": host,
        "port": port,
        "reload": reload,
        "log_level": LOGGING_CONFIG["level"].lower(),
        "timeout_keep_alive": 300,  # 5 minutes keep-alive timeout (for long-running LLM requests)
        "timeout_graceful_shutdown": 30  # 30 seconds for graceful shutdown
    }
    
    # Add reload configuration if in debug mode
    if reload and reload_dirs:
        uvicorn_config["reload_dirs"] = reload_dirs
        print(f"📁 Watching directories: {reload_dirs}")
    
    if reload and reload_excludes:
        uvicorn_config["reload_excludes"] = reload_excludes
        print(f"🚫 Excluding from watch: {reload_excludes}")
    
    uvicorn.run(**uvicorn_config)
