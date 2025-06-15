# This file will contain authentication-related functions for the backend
# Move get_current_user and rate_limit here from main.py (actual code to be moved/refactored in a later step) 

import logging
from typing import Dict, Optional

import jwt
from config import config
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client
from functools import wraps
import time
from collections import defaultdict

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
        payload = jwt.decode(
            token,
            config.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
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

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
    def is_allowed(self, user_id: str, max_requests: int = 100, window_seconds: int = 3600) -> bool:
        now = time.time()
        window_start = now - window_seconds
        self.requests[user_id] = [req_time for req_time in self.requests[user_id] if req_time > window_start]
        if len(self.requests[user_id]) >= max_requests:
            return False
        self.requests[user_id].append(now)
        return True

rate_limiter = RateLimiter()

def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
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