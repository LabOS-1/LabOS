"""
Tool Storage Service - Handles saving and loading dynamically created tools
"""

import hashlib
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models.database.tool import ProjectTool, ToolStatus
from app.models.schemas.tool import ToolCreate, ToolUpdate, ToolResponse
from app.core.infrastructure.database import AsyncSessionLocal
import os


class ToolStorageService:
    """Service for storing and managing dynamically created tools"""

    # Lazy initialization of sync engine
    _sync_engine = None
    _SyncSession = None

    @staticmethod
    def _get_sync_database_url() -> str:
        """Get synchronous database URL

        Supports both SQLite and PostgreSQL (must match async database config)
        """
        # Check if SQLite mode is enabled (must match async config)
        use_sqlite = os.getenv('USE_SQLITE', 'false').lower() == 'true'

        if use_sqlite:
            # SQLite mode - synchronous driver
            sqlite_path = os.getenv('SQLITE_PATH', './data/labos.db')
            return f"sqlite:///{sqlite_path}"

        # PostgreSQL mode
        environment = os.getenv('ENVIRONMENT', 'development')
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        cloud_sql_connection_name = os.getenv('CLOUD_SQL_CONNECTION_NAME')

        if not db_user or not db_password:
            raise ValueError("DB_USER and DB_PASSWORD must be set in environment variables")

        if environment == 'production':
            db_name = os.getenv('DB_NAME', 'labos_chat')
            db_host = os.getenv('DB_HOST')
            if db_host:
                db_port = os.getenv('DB_PORT', '5432')
                return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            else:
                return f"postgresql+psycopg2://{db_user}:{db_password}@/{db_name}?host=/cloudsql/{cloud_sql_connection_name}"
        else:
            db_name = os.getenv('DEV_DB_NAME', 'labos_chat_dev')
            return f"postgresql+psycopg2://{db_user}:{db_password}@localhost:5432/{db_name}"

    @classmethod
    def _get_sync_session(cls):
        """Get or create sync database session"""
        if cls._sync_engine is None:
            try:
                cls._sync_engine = create_engine(
                    cls._get_sync_database_url(),
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                    echo=False
                )
                cls._SyncSession = sessionmaker(bind=cls._sync_engine, class_=Session)
            except Exception as e:
                print(f"Warning: Could not create sync database engine: {e}")
                raise
        return cls._SyncSession()

    @staticmethod
    def _compute_code_hash(code: str) -> str:
        """Compute SHA256 hash of tool code"""
        return hashlib.sha256(code.encode('utf-8')).hexdigest()

    @staticmethod
    def create_tool_sync(
        tool_data: ToolCreate,
        user_id: str,
        created_by_agent: str = "tool_creation_agent"
    ) -> ProjectTool:
        """
        SYNCHRONOUS version: Create a new tool and save to database
        Use this from sync tools to avoid event loop conflicts

        Args:
            tool_data: Tool creation data
            user_id: ID of the user who owns this tool
            created_by_agent: Name of the agent that created the tool

        Returns:
            Created ProjectTool instance
        """
        session = None
        try:
            session = ToolStorageService._get_sync_session()

            # Compute code hash for deduplication
            code_hash = ToolStorageService._compute_code_hash(tool_data.tool_code)

            # Check if tool with same code already exists for this project
            query = select(ProjectTool).where(
                ProjectTool.project_id == tool_data.project_id,
                ProjectTool.code_hash == code_hash,
                ProjectTool.status == ToolStatus.ACTIVE
            )
            result = session.execute(query)
            existing_tool = result.scalar_one_or_none()

            if existing_tool:
                print(f"🔧 Tool with same code already exists: {existing_tool.name}")
                return existing_tool

            # Create new tool
            new_tool = ProjectTool(
                user_id=user_id,
                project_id=tool_data.project_id,
                name=tool_data.name,
                display_name=tool_data.display_name or tool_data.name.replace('_', ' ').title(),
                description=tool_data.description,
                category=tool_data.category,
                tool_code=tool_data.tool_code,
                code_hash=code_hash,
                parameters=[p.dict() for p in tool_data.parameters] if tool_data.parameters else [],
                return_type=tool_data.return_type,
                examples=tool_data.examples,
                dependencies=tool_data.dependencies,
                tool_metadata=tool_data.tool_metadata,
                created_by_agent=created_by_agent,
                workflow_id=tool_data.workflow_id,
                message_id=tool_data.message_id,
                version="1.0.0",
                status=ToolStatus.ACTIVE
            )

            session.add(new_tool)
            session.commit()
            session.refresh(new_tool)

            print(f"✅ Saved tool to database: {new_tool.name} (ID: {new_tool.id})")
            return new_tool

        except Exception as e:
            if session:
                session.rollback()
            print(f"❌ Error saving tool to database: {e}")
            raise
        finally:
            if session:
                session.close()

    @staticmethod
    async def create_tool(
        tool_data: ToolCreate,
        user_id: str,
        created_by_agent: str = "tool_creation_agent"
    ) -> ProjectTool:
        """
        Create a new tool and save to database

        Args:
            tool_data: Tool creation data
            user_id: ID of the user who owns this tool
            created_by_agent: Name of the agent that created the tool

        Returns:
            Created ProjectTool instance
        """
        async with AsyncSessionLocal() as session:
            try:
                # Compute code hash for deduplication
                code_hash = ToolStorageService._compute_code_hash(tool_data.tool_code)

                # Check if tool with same code already exists for this project
                query = select(ProjectTool).where(
                    ProjectTool.project_id == tool_data.project_id,
                    ProjectTool.code_hash == code_hash,
                    ProjectTool.status == ToolStatus.ACTIVE
                )
                result = await session.execute(query)
                existing_tool = result.scalar_one_or_none()

                if existing_tool:
                    print(f"🔧 Tool with same code already exists: {existing_tool.name}")
                    return existing_tool

                # Create new tool
                new_tool = ProjectTool(
                    user_id=user_id,
                    project_id=tool_data.project_id,
                    name=tool_data.name,
                    display_name=tool_data.display_name or tool_data.name.replace('_', ' ').title(),
                    description=tool_data.description,
                    category=tool_data.category,
                    tool_code=tool_data.tool_code,
                    code_hash=code_hash,
                    parameters=[p.dict() for p in tool_data.parameters] if tool_data.parameters else [],
                    return_type=tool_data.return_type,
                    examples=tool_data.examples,
                    dependencies=tool_data.dependencies,
                    tool_metadata=tool_data.tool_metadata,
                    created_by_agent=created_by_agent,
                    workflow_id=tool_data.workflow_id,
                    message_id=tool_data.message_id,
                    version="1.0.0",
                    status=ToolStatus.ACTIVE
                )

                session.add(new_tool)
                await session.commit()
                await session.refresh(new_tool)

                print(f"✅ Saved tool to database: {new_tool.name} (ID: {new_tool.id})")
                return new_tool

            except Exception as e:
                await session.rollback()
                print(f"❌ Error saving tool to database: {e}")
                raise

    @staticmethod
    async def get_tool_by_id(tool_id: UUID) -> Optional[ProjectTool]:
        """Get tool by ID"""
        async with AsyncSessionLocal() as session:
            query = select(ProjectTool).where(ProjectTool.id == tool_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    @staticmethod
    async def get_tools_by_user(
        user_id: str,
        status: Optional[str] = ToolStatus.ACTIVE
    ) -> List[ProjectTool]:
        """Get all tools created by a user (across all projects)"""
        async with AsyncSessionLocal() as session:
            query = select(ProjectTool).where(
                ProjectTool.user_id == user_id
            )

            if status:
                query = query.where(ProjectTool.status == status)

            query = query.order_by(ProjectTool.created_at.desc())
            result = await session.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def get_tools_by_project(
        project_id: UUID,
        user_id: str,
        status: Optional[str] = ToolStatus.ACTIVE
    ) -> List[ProjectTool]:
        """Get all tools for a specific project"""
        async with AsyncSessionLocal() as session:
            query = select(ProjectTool).where(
                ProjectTool.project_id == project_id,
                ProjectTool.user_id == user_id
            )

            if status:
                query = query.where(ProjectTool.status == status)

            query = query.order_by(ProjectTool.created_at.desc())
            result = await session.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def update_tool_usage(
        tool_id: UUID,
        success: bool = True
    ) -> bool:
        """Update tool usage statistics"""
        async with AsyncSessionLocal() as session:
            try:
                query = select(ProjectTool).where(ProjectTool.id == tool_id)
                result = await session.execute(query)
                tool = result.scalar_one_or_none()

                if not tool:
                    return False

                tool.usage_count += 1
                tool.last_used_at = datetime.utcnow()

                if success:
                    tool.success_count += 1
                else:
                    tool.error_count += 1

                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                print(f"❌ Error updating tool usage: {e}")
                return False

    @staticmethod
    async def update_tool(
        tool_id: UUID,
        tool_update: ToolUpdate,
        user_id: str
    ) -> Optional[ProjectTool]:
        """Update tool information"""
        async with AsyncSessionLocal() as session:
            try:
                query = select(ProjectTool).where(
                    ProjectTool.id == tool_id,
                    ProjectTool.user_id == user_id
                )
                result = await session.execute(query)
                tool = result.scalar_one_or_none()

                if not tool:
                    return None

                # Update fields if provided
                update_data = tool_update.dict(exclude_unset=True)
                for field, value in update_data.items():
                    if field == "tool_code" and value:
                        # Recompute hash if code changed
                        tool.code_hash = ToolStorageService._compute_code_hash(value)
                    setattr(tool, field, value)

                tool.updated_at = datetime.utcnow()
                await session.commit()
                await session.refresh(tool)

                print(f"✅ Updated tool: {tool.name}")
                return tool
            except Exception as e:
                await session.rollback()
                print(f"❌ Error updating tool: {e}")
                raise

    @staticmethod
    async def delete_tool(
        tool_id: UUID,
        user_id: str,
        soft_delete: bool = True
    ) -> bool:
        """Delete a tool (soft delete by default)"""
        async with AsyncSessionLocal() as session:
            try:
                query = select(ProjectTool).where(
                    ProjectTool.id == tool_id,
                    ProjectTool.user_id == user_id
                )
                result = await session.execute(query)
                tool = result.scalar_one_or_none()

                if not tool:
                    return False

                if soft_delete:
                    tool.status = ToolStatus.DEPRECATED
                    tool.updated_at = datetime.utcnow()
                    await session.commit()
                else:
                    await session.delete(tool)
                    await session.commit()

                print(f"✅ Deleted tool: {tool.name}")
                return True
            except Exception as e:
                await session.rollback()
                print(f"❌ Error deleting tool: {e}")
                return False

    @staticmethod
    async def get_public_tools(
        status: Optional[str] = ToolStatus.ACTIVE
    ) -> List[ProjectTool]:
        """Get all public tools shared by users"""
        async with AsyncSessionLocal() as session:
            query = select(ProjectTool).where(
                ProjectTool.is_public == True
            )

            if status:
                query = query.where(ProjectTool.status == status)

            query = query.order_by(ProjectTool.usage_count.desc())
            result = await session.execute(query)
            return list(result.scalars().all())


# Global tool storage service instance
tool_storage_service = ToolStorageService()