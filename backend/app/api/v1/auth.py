"""
Authentication API endpoints for Auth0 integration
Moved from frontend to backend for unified architecture
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlencode, quote
import asyncio

from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Import unified configuration
from app.config import AUTH0_CONFIG, ENVIRONMENT_URLS, ENVIRONMENT
from app.core.infrastructure.database import get_db_session
from app.models import User, UserStatus
from app.api.v1.chat_projects import get_current_user_id
from app.services.email_service import send_admin_notification

logger = logging.getLogger(__name__)

router = APIRouter()

# Auth0 Configuration from unified settings
def get_auth0_config():
    """Get Auth0 configuration from unified settings"""
    # URLs now come directly from environment variables via ENVIRONMENT_URLS
    config = {
        'domain': AUTH0_CONFIG["issuer_base_url"],
        'client_id': AUTH0_CONFIG["client_id"],
        'client_secret': AUTH0_CONFIG["client_secret"],
        'base_url': AUTH0_CONFIG["base_url"],  # Frontend URL (from AUTH0_BASE_URL env)
        'backend_url': ENVIRONMENT_URLS["backend_url"],  # Backend URL (from BACKEND_URL env)
        'environment': ENVIRONMENT
    }
    
    # Log configuration for debugging
    logger.info("🔍 Auth0 Configuration Check:")
    for key, value in config.items():
        if value:
            if 'secret' in key.lower():
                logger.info(f"  ✅ {key}: {'*' * 20} (hidden)")
            else:
                logger.info(f"  ✅ {key}: {value}")
        else:
            logger.error(f"  ❌ {key}: Not set")
    
    # Validate required config (excluding backend_url which has default)
    required_keys = ['domain', 'client_id', 'client_secret']
    missing = [key for key in required_keys if not config[key]]
    
    if missing:
        error_msg = f"Auth0 configuration missing: {', '.join(missing)}"
        logger.error(f"❌ {error_msg}")
        raise HTTPException(
            status_code=500, 
            detail=error_msg
        )
    
    logger.info("✅ Auth0 configuration validated successfully")
    return config


@router.get("/login")
async def login(request: Request):
    """Initiate Auth0 login flow"""
    try:
        config = get_auth0_config()
        
        # URLs are now fully controlled by environment variables
        # No need to override based on origin - just use what's in .env
        origin = request.headers.get('origin') or request.headers.get('referer')
        logger.info(f"🔄 Auth0: Using env-configured URLs for {config['environment']}, origin: {origin}")
        
        # Build callback URL pointing to backend (now using /api/v1/)
        callback_url = f"{config['backend_url']}/api/v1/auth/callback"
        
        # Build Auth0 authorization URL with base_url in state
        import base64
        state_data = {
            'random': 'random-state-string',
            'base_url': config['base_url']  # Include the detected base_url
        }
        state_encoded = base64.b64encode(json.dumps(state_data).encode()).decode()
        
        auth_params = {
            'response_type': 'code',
            'client_id': config['client_id'],
            'redirect_uri': callback_url,
            'scope': 'openid profile email',
            'state': state_encoded
        }
        
        # Support prompt parameter to force re-authentication (bypass Auth0 SSO session)
        prompt = request.query_params.get('prompt')
        if prompt:
            auth_params['prompt'] = prompt
        
        # Support screen_hint to show signup form instead of login
        screen_hint = request.query_params.get('screen_hint')
        if screen_hint:
            auth_params['screen_hint'] = screen_hint
        
        auth_url = f"{config['domain']}/authorize?{urlencode(auth_params)}"
        
        logger.info(f"Redirecting to Auth0 login: {auth_url}")
        return RedirectResponse(url=auth_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.get("/callback")
async def callback(request: Request):
    """Handle Auth0 callback and exchange code for tokens"""
    try:
        config = get_auth0_config()
        
        # Get query parameters
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')
        
        # Decode state to get original base_url
        original_base_url = config['base_url']  # fallback
        if state:
            try:
                import base64
                state_data = json.loads(base64.b64decode(state).decode())
                original_base_url = state_data.get('base_url', config['base_url'])
                logger.info(f"🔄 Auth0 callback: Using base_url from state: {original_base_url}")
            except:
                logger.warning("Could not decode state, using default base_url")
        
        # Handle errors
        if error:
            logger.error(f"Auth0 callback error: {error}")
            return RedirectResponse(
                url=f"{original_base_url}/?error={error}", 
                status_code=302
            )
        
        if not code:
            logger.error("No authorization code received")
            return RedirectResponse(
                url=f"{original_base_url}/?error=no_code", 
                status_code=302
            )
        
        # Exchange code for tokens
        callback_url = f"{config['backend_url']}/api/v1/auth/callback"
        
        async with httpx.AsyncClient() as client:
            # Ensure domain has https:// prefix
            domain = config['domain'] if config['domain'].startswith('http') else f"https://{config['domain']}"
            
            token_response = await client.post(
                f"{domain}/oauth/token",
                json={
                    'grant_type': 'authorization_code',
                    'client_id': config['client_id'],
                    'client_secret': config['client_secret'],
                    'code': code,
                    'redirect_uri': callback_url,
                }
            )
            
            logger.info(f"Token exchange response: {token_response.status_code}")
            
            if not token_response.is_success:
                logger.error(f"Token exchange failed: {token_response.text}")
                raise HTTPException(status_code=400, detail="Token exchange failed")
            
            tokens = token_response.json()
            
            # Get user info
            user_response = await client.get(
                f"{domain}/userinfo",
                headers={'Authorization': f"Bearer {tokens['access_token']}"}
            )
            
            if not user_response.is_success:
                logger.error(f"User info fetch failed: {user_response.text}")
                raise HTTPException(status_code=400, detail="User info fetch failed")
            
            user = user_response.json()
            
        # Prepare user data
        user_data = {
            'id': user.get('sub'),
            'email': user.get('email'),
            'name': user.get('name'),
            'picture': user.get('picture'),
            'email_verified': user.get('email_verified', False),
            'issued_at': int(datetime.utcnow().timestamp())  # Token expiration tracking
        }
        
        # Check email verification requirement
        if not user_data['email_verified']:
            logger.warning(f"User {user_data['email']} attempted login with unverified email")
            return RedirectResponse(
                url=f"{config['base_url']}/verify-email?email={user_data['email']}", 
                status_code=302
            )
        
        # Check user status in database (Waitlist system)
        from app.core.infrastructure.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            # Check if user exists in database (query by auth0_id, not id)
            stmt = select(User).where(User.auth0_id == user_data['id'])
            result = await db.execute(stmt)
            db_user = result.scalar_one_or_none()

            if not db_user:
                # First-time login: User not in database yet
                # DON'T create user here - they must fill out the waitlist form first
                # Just redirect to waitlist form with Auth0 user data
                logger.info(f"🆕 New user {user_data['email']} - redirecting to waitlist form")

                # Add status indicator (not in DB yet)
                user_data['status'] = 'new'
                user_data['is_admin'] = False

                # Create auth token with user data from Auth0
                import base64
                user_token = base64.b64encode(json.dumps(user_data).encode()).decode()

                # Redirect to waitlist-pending page with auth token
                return RedirectResponse(
                    url=f"{original_base_url}/waitlist-pending?email={user_data['email']}&auth_token={user_token}",
                    status_code=302
                )
            
            # Update last login timestamp and sync user info from Auth0
            db_user.last_login = datetime.utcnow()

            # Update user info if it's outdated (placeholder email or missing info)
            if db_user.email and '@placeholder.com' in db_user.email:
                logger.info(f"🔄 Updating user info from Auth0: {db_user.email} -> {user_data['email']}")
                db_user.email = user_data['email']
            if not db_user.name and user_data.get('name'):
                db_user.name = user_data['name']
            if not db_user.picture and user_data.get('picture'):
                db_user.picture = user_data['picture']
            if not db_user.email_verified and user_data.get('email_verified'):
                db_user.email_verified = user_data['email_verified']

            await db.commit()

            # Check user status
            if db_user.status == UserStatus.WAITLIST:
                logger.warning(f"⏳ User {user_data['email']} is still on waitlist")
                
                # Add status to user_data
                user_data['status'] = db_user.status.value
                user_data['is_admin'] = db_user.is_admin
                
                # Create auth token for waitlist user
                import base64
                user_token = base64.b64encode(json.dumps(user_data).encode()).decode()
                
                return RedirectResponse(
                    url=f"{original_base_url}/waitlist-pending?email={user_data['email']}&auth_token={user_token}", 
                    status_code=302
                )
            elif db_user.status == UserStatus.REJECTED:
                logger.warning(f"❌ User {user_data['email']} has been rejected")
                return RedirectResponse(
                    url=f"{original_base_url}/access-denied?reason=rejected", 
                    status_code=302
                )
            elif db_user.status == UserStatus.SUSPENDED:
                logger.warning(f"🚫 User {user_data['email']} is suspended")
                return RedirectResponse(
                    url=f"{original_base_url}/access-denied?reason=suspended", 
                    status_code=302
                )
            elif db_user.status != UserStatus.APPROVED:
                logger.error(f"⚠️ User {user_data['email']} has unknown status: {db_user.status}")
                return RedirectResponse(
                    url=f"{original_base_url}/access-denied?reason=unknown", 
                    status_code=302
                )
            
            # User is APPROVED - proceed with normal login
            logger.info(f"✅ User authenticated and approved: {user_data['email']}")
            
            # Add user status to user_data for frontend
            user_data['status'] = db_user.status.value
            user_data['is_admin'] = db_user.is_admin
        
        # Create response with cookie AND URL params for cross-domain support
        import urllib.parse
        import base64
        
        # Create a simple token (base64 encoded user data)
        user_token = base64.b64encode(json.dumps(user_data).encode()).decode()
        
        # Encode user data for URL parameter (use original base_url from state)
        redirect_url = f"{original_base_url}?auth_token={user_token}"
        
        response = RedirectResponse(url=redirect_url, status_code=302)
        
        # Set auth cookie (for same-domain scenarios like localhost)
        cookie_value = json.dumps(user_data)
        
        # Set cookie attributes based on environment
        is_production = 'localhost' not in config['base_url']
        cookie_attributes = {
            'key': 'auth-user',
            'value': cookie_value,
            'path': '/',
            'httponly': False,  # Allow frontend access
            'samesite': 'lax',  # Allow cross-site requests
            'max_age': 86400,  # 24 hours
        }
        
        if is_production:
            cookie_attributes['secure'] = True
            # Don't set domain - let browser handle it for cross-origin requests
        
        response.set_cookie(**cookie_attributes)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Callback processing error: {e}")
        config = get_auth0_config()
        return RedirectResponse(
            url=f"{config['base_url']}/?error=callback_error", 
            status_code=302
        )


@router.get("/me")
async def get_user(request: Request):
    """Get current user information from cookie, Authorization header, or token query param"""
    try:
        user_data = None

        # Try Authorization header first (for cross-domain)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            try:
                # Try base64 decode first
                import base64
                decoded_data = base64.b64decode(token).decode()
                user_data = json.loads(decoded_data)
                logger.info(f"User info requested via Bearer token: {user_data.get('email')}")
            except:
                try:
                    # Fallback to direct JSON
                    user_data = json.loads(token)
                    logger.info(f"User info requested via JSON Bearer: {user_data.get('email')}")
                except json.JSONDecodeError:
                    pass

        # Try token query parameter (for URL-based auth)
        if not user_data:
            token_param = request.query_params.get('token')
            if token_param:
                try:
                    import base64
                    decoded_data = base64.b64decode(token_param).decode()
                    user_data = json.loads(decoded_data)
                    logger.info(f"User info requested via token param: {user_data.get('email')}")
                except:
                    pass

        # Fallback to cookie (for same-domain)
        if not user_data:
            auth_cookie = request.cookies.get('auth-user')

            if not auth_cookie:
                logger.info("No auth cookie, header, or token found")
                raise HTTPException(status_code=401, detail="Not authenticated")

            # Parse user data
            user_data = json.loads(auth_cookie)
            logger.info(f"User info requested via cookie: {user_data.get('email')}")

        # Check token expiration (24 hours)
        issued_at = user_data.get('issued_at')
        if issued_at:
            token_age = int(datetime.utcnow().timestamp()) - issued_at
            if token_age > 86400:  # 24 hours
                logger.warning(f"⏰ Token expired for user {user_data.get('email')} (age: {token_age}s)")
                raise HTTPException(
                    status_code=401,
                    detail="Token expired. Please login again."
                )

        # CRITICAL: Query database to get latest user status
        # Token might be stale (created before admin approved the user)
        from app.core.infrastructure.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            stmt = select(User).where(User.auth0_id == user_data['id'])
            result = await db.execute(stmt)
            db_user = result.scalar_one_or_none()

            if db_user:
                # Update user_data with fresh status from database
                user_data['status'] = db_user.status.value
                user_data['is_admin'] = db_user.is_admin
                # Also update email from DB if token has placeholder
                if db_user.email and '@placeholder.com' not in db_user.email:
                    user_data['email'] = db_user.email
                logger.info(f"✅ Refreshed user status from DB: {user_data.get('email')} -> {db_user.status.value}")
            else:
                # New user not in database yet - return token data with status 'new'
                # This allows the waitlist-pending page to work properly
                user_data['status'] = 'new'
                user_data['is_admin'] = False
                logger.info(f"🆕 New user {user_data.get('email')} not in DB yet, returning status='new'")

        return JSONResponse(content=user_data)

    except json.JSONDecodeError:
        logger.error("Invalid auth data format")
        raise HTTPException(status_code=401, detail="Invalid authentication")
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=401, detail="Authentication error")


@router.get("/logout")
async def logout(request: Request):
    """Handle logout and redirect to Auth0 logout"""
    try:
        config = get_auth0_config()
        
        # URLs are now fully controlled by environment variables
        origin = request.headers.get('origin') or request.headers.get('referer')
        logger.info(f"🔄 Auth0 logout: Using env-configured URLs for {config['environment']}, origin: {origin}")
        
        # Build Auth0 logout URL
        logout_params = {
            'client_id': config['client_id'],
            'returnTo': config['base_url']
        }
        
        logout_url = f"{config['domain']}/v2/logout?{urlencode(logout_params)}"
        
        # Create response with cleared cookie
        response = RedirectResponse(url=logout_url, status_code=302)
        
        # Clear auth cookie
        response.delete_cookie(
            key='auth-user',
            path='/',
            httponly=True,
            samesite='strict'
        )
        
        logger.info("User logged out successfully")
        return response
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")


@router.post("/waitlist/submit")
async def submit_waitlist_application(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Submit waitlist application - creates user in database with form data"""
    try:
        # Get user data from authentication token
        # Token contains Auth0 user info (id, email, name, picture)
        user_data = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                import base64
                decoded_data = base64.b64decode(token).decode()
                user_data = json.loads(decoded_data)
            except:
                try:
                    user_data = json.loads(token)
                except:
                    pass

        if not user_data or not user_data.get('id'):
            raise HTTPException(status_code=401, detail="Authentication required")

        # Ensure email is present
        user_email = user_data.get('email')
        if not user_email:
            raise HTTPException(status_code=400, detail="Email is required. Please login with an email-enabled account.")

        auth0_id = user_data.get('id') or user_data.get('sub')

        # Parse request body
        body = await request.json()

        # Validate required fields
        required_fields = ['first_name', 'last_name', 'job_title', 'organization', 'country', 'experience_level', 'use_case']
        missing_fields = [field for field in required_fields if not body.get(field)]
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Check if user already exists in database
        stmt = select(User).where(User.auth0_id == auth0_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # User exists - just update their application data
            logger.info(f"📝 Updating existing user's waitlist application: {user.email}")
        else:
            # Create new user with Auth0 data + application data
            user = User(
                auth0_id=auth0_id,
                email=user_data.get('email'),
                name=user_data.get('name'),
                picture=user_data.get('picture'),
                email_verified=user_data.get('email_verified', False),
                status=UserStatus.WAITLIST
            )
            db.add(user)
            logger.info(f"✨ Creating new user from waitlist form: {user_data.get('email')}")

        # Update user with waitlist application data
        user.first_name = body.get('first_name')
        user.last_name = body.get('last_name')
        user.job_title = body.get('job_title')
        user.organization = body.get('organization')
        user.country = body.get('country')
        user.experience_level = body.get('experience_level')
        user.use_case = body.get('use_case')
        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        logger.info(f"✅ Waitlist application submitted for user: {user.email}")
        
        # Send notification email to admin (non-blocking)
        admin_email = os.getenv('ADMIN_EMAIL', 'stella.agent2026@gmail.com')
        user_name = f"{user.first_name} {user.last_name}".strip()
        asyncio.create_task(
            asyncio.to_thread(send_admin_notification, admin_email, user.email, user_name)
        )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Application submitted successfully",
                "user_id": auth0_id
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting waitlist application: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit application")


@router.get("/profile")
async def get_user_profile(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Get user profile information from database"""
    try:
        # Get user_id from authentication
        user_id = await get_current_user_id(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get user from database
        stmt = select(User).where(User.auth0_id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Return profile data
        return JSONResponse(
            content={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "job_title": user.job_title,
                "organization": user.organization,
                "country": user.country,
                "experience_level": user.experience_level,
                "use_case": user.use_case
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get profile")


@router.put("/profile/update")
async def update_user_profile(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Update user profile information"""
    try:
        # Get user_id from authentication
        user_id = await get_current_user_id(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Parse request body
        body = await request.json()
        
        # Get user from database
        stmt = select(User).where(User.auth0_id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user profile fields (only update if provided)
        if 'first_name' in body:
            user.first_name = body['first_name']
        if 'last_name' in body:
            user.last_name = body['last_name']
        if 'job_title' in body:
            user.job_title = body['job_title']
        if 'organization' in body:
            user.organization = body['organization']
        if 'country' in body:
            user.country = body['country']
        if 'experience_level' in body:
            user.experience_level = body['experience_level']
        if 'use_case' in body:
            user.use_case = body['use_case']
        
        user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"✅ Profile updated for user: {user.email}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Profile updated successfully",
                "user_id": user_id
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")
