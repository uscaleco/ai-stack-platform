# backend/auth.py
import logging
from typing import Dict, Optional

import jwt
from config import config
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

logger = logging.getLogger(__name__)

# Initialize Supabase client


supabase: Client = create_client(config.supabase_url, config.supabase_service_key)

# Security scheme
security = HTTPBearer()


class AuthenticationError(Exception):
    pass


def verify_jwt_token(token: str) -> Dict:
    """Verify Supabase JWT token and return user info"""
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            config.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},  # Supabase uses custom audience
        )

        # Extract user information
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role", "authenticated")

        if not user_id:
            raise AuthenticationError("Invalid token: missing user ID")

        return {
            "user_id": user_id,
            "email": email,
            "role": role,
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
        }

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise AuthenticationError("Token verification failed")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict:
    """
    FastAPI dependency to get current authenticated user
    Raises HTTPException if authentication fails
    """
    try:
        token = credentials.credentials
        user_info = verify_jwt_token(token)
        return user_info

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(current_user: Dict = Depends(get_current_user)) -> str:
    """FastAPI dependency to get current user ID"""
    return current_user["user_id"]


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict]:
    """
    FastAPI dependency to get current user if authenticated, None otherwise
    Does not raise exceptions for unauthenticated requests
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        user_info = verify_jwt_token(token)
        return user_info
    except:
        return None


def require_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    """FastAPI dependency to require admin role"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


def get_user_from_supabase(user_id: str) -> Optional[Dict]:
    """Get user details from Supabase Auth"""
    try:
        response = supabase.auth.admin.get_user_by_id(user_id)
        if response.user:
            return {
                "id": response.user.id,
                "email": response.user.email,
                "created_at": response.user.created_at,
                "last_sign_in_at": response.user.last_sign_in_at,
                "user_metadata": response.user.user_metadata,
                "app_metadata": response.user.app_metadata,
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching user from Supabase: {str(e)}")
        return None


def create_user_profile(
    user_id: str, email: str, full_name: Optional[str] = None
) -> bool:
    """Create user profile in database"""
    try:
        supabase.table("user_profiles").insert(
            {
                "id": user_id,
                "email": email,
                "full_name": full_name or email.split("@")[0],
                "created_at": "now()",
            }
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Error creating user profile: {str(e)}")
        return False


def update_user_profile(user_id: str, updates: Dict) -> bool:
    """Update user profile in database"""
    try:
        supabase.table("user_profiles").update(updates).eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        return False


def delete_user_data(user_id: str) -> bool:
    """Delete all user data (GDPR compliance)"""
    try:
        # Delete in order of dependencies
        supabase.table("update_history").delete().eq(
            "deployment_id",
            supabase.table("deployments").select("id").eq("user_id", user_id),
        ).execute()

        supabase.table("deployments").delete().eq("user_id", user_id).execute()
        supabase.table("subscriptions").delete().eq("user_id", user_id).execute()
        supabase.table("user_profiles").delete().eq("id", user_id).execute()

        return True
    except Exception as e:
        logger.error(f"Error deleting user data: {str(e)}")
        return False


import asyncio
import time
from collections import defaultdict

# Rate limiting decorator
from functools import wraps


class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)

    def is_allowed(
        self, user_id: str, max_requests: int = 100, window_seconds: int = 3600
    ) -> bool:
        """Simple in-memory rate limiting"""
        now = time.time()
        window_start = now - window_seconds

        # Clean old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id] if req_time > window_start
        ]

        # Check if under limit
        if len(self.requests[user_id]) >= max_requests:
            return False

        # Add current request
        self.requests[user_id].append(now)
        return True


rate_limiter = RateLimiter()


def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """Rate limiting decorator"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs
            current_user = kwargs.get("current_user")
            if current_user and not rate_limiter.is_allowed(
                current_user["user_id"], max_requests, window_seconds
            ):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
