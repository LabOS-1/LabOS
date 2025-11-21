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

# Add the parent directory to Python path to import stella modules
sys.path.append(str(Path(__file__).parent.parent))
# Add current directory to path for relative imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import unified configuration
from app.config import (
    SERVER_CONFIG, DATABASE_CONFIG, LOGGING_CONFIG, 
    STORAGE_CONFIG, ENVIRONMENT, DEBUG
)

# Import and setup logging systems
from app.core.cloud_logging import setup_cloud_logging
from app.core.logging_config import setup_logging

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

from app.api.chat_projects import router as chat_projects_router
from app.api.agents import router as agents_router
from app.api.tools import router as tools_router
from app.api.files import router as files_router
from app.api.memory import router as memory_router
from app.api.system import router as system_router
from app.api.websocket import router as websocket_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.gcs import router as gcs_router
from app.services.labos_service import LabOSService
from app.services.websocket_broadcast import websocket_broadcaster

# Initialize services
labos_service = LabOSService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""

    from app.core.database import init_database, close_database
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
    
    # Initialize LabOS service
    try:
        await labos_service.initialize()
        logger.info("LabOS AI service initialized successfully")
        print("✅ LabOS AI service initialized")
    except Exception as e:
        logger.error(f"LabOS AI initialization failed: {e}")
        print(f"❌ LabOS AI initialization failed: {e}")

    # WebSocket broadcaster is already initialized and ready to use
    logger.info("LabOS AI Backend startup completed successfully")
    print("✅ LabOS AI Backend started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Starting LabOS AI Backend shutdown")
    print("🛑 Shutting down LabOS AI Backend...")
    try:
        await labos_service.cleanup()
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=SERVER_CONFIG["cors_origins"] + [
        "https://stella-frontend-843173980594.us-central1.run.app",
        "https://stella-agent.com",
        "https://www.stella-agent.com",
        "file://"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(chat_projects_router, prefix="/api/chat", tags=["chat-projects"])
app.include_router(agents_router, prefix="/api/agents", tags=["agents"])
app.include_router(tools_router, prefix="/api/tools", tags=["tools"])
app.include_router(files_router, prefix="/api/files", tags=["files"])
app.include_router(memory_router, prefix="/api/memory", tags=["export"])
app.include_router(system_router, prefix="/api/system", tags=["system"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(gcs_router, prefix="/api/gcs", tags=["gcs"])  # GCS upload for large files
app.include_router(websocket_router, prefix="", tags=["websocket"])  # No prefix for /ws

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
        "stella_initialized": labos_service.is_initialized(),
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
        "log_level": LOGGING_CONFIG["level"].lower()
    }
    
    # Add reload configuration if in debug mode
    if reload and reload_dirs:
        uvicorn_config["reload_dirs"] = reload_dirs
        print(f"📁 Watching directories: {reload_dirs}")
    
    if reload and reload_excludes:
        uvicorn_config["reload_excludes"] = reload_excludes
        print(f"🚫 Excluding from watch: {reload_excludes}")
    
    uvicorn.run(**uvicorn_config)
