"""
User database model
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Enum
from sqlalchemy.types import JSON

from app.core.infrastructure.database import Base
from app.models.enums import UserStatus


class User(Base):
    """User model for waitlist and approval management"""
    __tablename__ = "users"
    
    # Primary key is Auth0 user_id (sub claim)
    id = Column(String(255), primary_key=True)  # Auth0 sub
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    picture = Column(String(500))
    
    # Status management
    status = Column(Enum(UserStatus), default=UserStatus.WAITLIST, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(255), nullable=True)  # Admin user_id who approved
    rejection_reason = Column(Text, nullable=True)
    
    # Waitlist application info (optional, can be collected on first login)
    institution = Column(String(255))
    research_field = Column(String(255))
    application_reason = Column(Text)
    
    # Enhanced waitlist fields (matching Google Form structure)
    first_name = Column(String(100))
    last_name = Column(String(100))
    job_title = Column(String(255))
    organization = Column(String(255))  # Affiliation/Organization
    country = Column(String(100))
    experience_level = Column(String(50))  # 'beginner', 'intermediate', 'advanced'
    use_case = Column(Text)  # Interest and planned usage
    
    # Auth0 metadata
    email_verified = Column(Boolean, default=False)
    auth0_metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Admin flag
    is_admin = Column(Boolean, default=False, nullable=False)

