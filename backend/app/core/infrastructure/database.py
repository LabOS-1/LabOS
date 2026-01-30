"""
Database configuration and connection management
"""

import os
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Database configuration
def get_database_url() -> str:
    """Get database URL based on environment

    Supports multiple database backends:
    - SQLite: Local file-based database (USE_SQLITE=true)
    - PostgreSQL (Cloud SQL): Production/development with Cloud SQL
    """
    # Check if SQLite mode is enabled (fallback for when Cloud SQL is unavailable)
    use_sqlite = os.getenv('USE_SQLITE', 'false').lower() == 'true'

    if use_sqlite:
        # SQLite mode - local database file
        sqlite_path = os.getenv('SQLITE_PATH', './data/labos.db')
        logger.info(f"🗄️  Using SQLite database: {sqlite_path}")
        return f"sqlite+aiosqlite:///{sqlite_path}"

    # PostgreSQL (Cloud SQL) mode
    environment = os.getenv('ENVIRONMENT', 'development')

    # Common Cloud SQL configuration
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    cloud_sql_connection_name = os.getenv('CLOUD_SQL_CONNECTION_NAME', 'semiotic-sylph-470501-q5:us-central1:labos-db')

    # Validate required credentials
    if not db_user or not db_password:
        raise ValueError(
            "Database credentials not configured! "
            "Please set DB_USER and DB_PASSWORD environment variables in .env file, "
            "or set USE_SQLITE=true to use local SQLite database"
        )

    if environment == 'production':
        # Production: Direct Cloud SQL connection via unix socket
        db_name = os.getenv('DB_NAME', 'labos_chat')
        logger.info(f"🗄️  Using Cloud SQL (production): {db_name}")
        return f"postgresql+asyncpg://{db_user}:{db_password}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"
    else:
        # Development: Cloud SQL via proxy (TCP connection)
        db_name = os.getenv('DEV_DB_NAME', 'labos_chat_dev')
        db_host = os.getenv('DB_HOST', 'localhost')  # Use host.docker.internal in Docker
        db_port = os.getenv('DB_PORT', '5432')
        logger.info(f"🗄️  Using Cloud SQL (development): {db_name} @ {db_host}:{db_port}")
        return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Create async engine with connection pooling
DATABASE_URL = get_database_url()
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Disable SQL query logging (set to True for debugging SQL issues)
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Dependency to get database session
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Database initialization
async def init_database():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from app.models import ChatProject, ChatMessage, WorkflowExecution, WorkflowStep, ProjectFile, ProjectTool

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables created successfully")

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

# Health check
async def check_database_health() -> bool:
    """Check if database is accessible"""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

# Cleanup
async def close_database():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")
