"""
Custom middleware for API service.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Log request timing."""
    
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        
        logger.info(
            f"{request.method} {request.url.path} "
            f"completed in {duration:.3f}s with status {response.status_code}"
        )
        
        response.headers["X-Process-Time"] = str(duration)
        return response


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    Extract user context from headers.
    In production, integrate with JWT/OAuth.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Extract user ID from header (or JWT token in production)
        user_id = request.headers.get("X-User-ID")
        ip = request.client.host if request.client else "unknown"
        
        # Attach to request state
        request.state.user_id = user_id
        request.state.ip = ip
        
        response = await call_next(request)
        return response
