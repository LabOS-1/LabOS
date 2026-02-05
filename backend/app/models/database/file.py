"""
File database model - DISABLED due to schema mismatch

The project_files table in the database doesn't have the columns defined here.
This model is disabled until a proper database migration is run.

To re-enable:
1. Run database migration to create/update project_files table with all columns
2. Uncomment the ProjectFile class below
3. Restart the backend
"""

# Keeping imports for future use
# import uuid
# from datetime import datetime
# from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, LargeBinary, BigInteger, Enum
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.types import JSON
# from sqlalchemy.orm import relationship

# from app.core.infrastructure.database import Base
# from app.models.enums import FileType, FileStatus


# DISABLED: ProjectFile model - database schema doesn't match
# class ProjectFile(Base):
#     """Project file model - follows same pattern as ChatMessage"""
#     __tablename__ = "project_files"
#
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     project_id = Column(UUID(as_uuid=True), ForeignKey('chat_projects.id'), nullable=True)
#     filename = Column(String(255), nullable=False)
#     original_filename = Column(String(255), nullable=False)
#     file_size = Column(BigInteger, nullable=False)
#     content_type = Column(String(100))
#     file_hash = Column(String(64))
#     file_data = Column(LargeBinary)
#     storage_path = Column(Text)
#     storage_provider = Column(String(20), default='database')
#     file_type = Column(Enum(FileType), nullable=False)
#     category = Column(String(50))
#     tags = Column(JSON, default=list)
#     file_metadata = Column(JSON, default=dict)
#     created_by_agent = Column(String(100))
#     workflow_id = Column(String(255))
#     message_id = Column(UUID(as_uuid=True), ForeignKey('chat_messages.id'), nullable=True)
#     status = Column(Enum(FileStatus), default=FileStatus.ACTIVE, nullable=False)
#     is_public = Column(Boolean, default=False, nullable=False)
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
#     last_accessed = Column(DateTime, default=datetime.utcnow)
#
#     # Relationship to ChatMessage
#     # message = relationship("ChatMessage", backref="attached_files")


# Placeholder class for import compatibility (not a SQLAlchemy model)
class ProjectFile:
    """Placeholder - actual model disabled due to schema mismatch"""
    pass
