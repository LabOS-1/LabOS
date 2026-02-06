"""
Authentication Utilities - Shared auth functions for API endpoints
"""

import base64
import json
import logging
from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User, UserStatus

logger = logging.getLogger(__name__)


async def require_approved_user(request: Request, db: AsyncSession) -> User:
    """
    Require that the current user is approved.

    This dependency should be used on all protected endpoints that require
    an approved user (not waitlist, rejected, or suspended).

    Returns:
        User: The approved user object

    Raises:
        HTTPException: 401 if not authenticated, 403 if not approved
    """
    # Get user ID from auth
    user_id = await get_current_user_id(request)

    # Look up user in database
    query = select(User).where(User.auth0_id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User not found in database: {user_id}")
        raise HTTPException(status_code=401, detail="User not found")

    # Check if user is approved
    if user.status != UserStatus.APPROVED:
        logger.warning(f"Access denied for non-approved user: {user.email} (status: {user.status.value})")
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Your account status is: {user.status.value}"
        )

    return user


async def get_current_user_id(request: Request) -> str:
    """
    Get current user ID from authentication context.

    Tries multiple authentication methods in order:
    1. Authorization header (Bearer token)
    2. Token query parameter
    3. Cookie (auth-user)

    Returns:
        str: The auth0_id of the authenticated user

    Raises:
        HTTPException: 401 if no valid authentication found
    """
    try:
        # Try Authorization header first (for cross-domain)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            user_id = _parse_token(token)
            if user_id:
                return user_id

        # Try token query parameter (for URL-based auth)
        token_param = request.query_params.get('token')
        if token_param:
            user_id = _parse_token(token_param)
            if user_id:
                return user_id

        # Fallback to cookie (for same-domain)
        auth_cookie = request.cookies.get('auth-user')
        if auth_cookie:
            try:
                user_data = json.loads(auth_cookie)
                user_id = user_data.get('sub') or user_data.get('id')
                if user_id:
                    return user_id
            except (json.JSONDecodeError, ValueError):
                pass

        # No valid authentication found
        raise HTTPException(status_code=401, detail="Authentication required")

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication")


def _parse_token(token: str) -> str | None:
    """
    Parse a token string to extract user ID.

    Tries base64 decode first, then direct JSON parse.

    Args:
        token: The token string to parse

    Returns:
        User ID if found, None otherwise
    """
    # Try base64 decode first
    try:
        decoded_data = base64.b64decode(token).decode()
        user_data = json.loads(decoded_data)
        user_id = user_data.get('sub') or user_data.get('id')
        if user_id:
            return user_id
    except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError, ValueError):
        pass

    # Fallback to direct JSON
    try:
        user_data = json.loads(token)
        user_id = user_data.get('sub') or user_data.get('id')
        if user_id:
            return user_id
    except (json.JSONDecodeError, ValueError):
        pass

    return None


async def get_or_create_user(db: AsyncSession, auth0_id: str) -> User:
    """
    Get user by auth0_id or create if not exists.

    Args:
        db: Database session
        auth0_id: The Auth0 user identifier

    Returns:
        User: The user object (existing or newly created)
    """
    query = select(User).where(User.auth0_id == auth0_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        user = User(auth0_id=auth0_id, email=f"{auth0_id}@placeholder.com")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
