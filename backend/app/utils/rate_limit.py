"""
Rate limiting utilities for protecting sensitive endpoints.
Uses slowapi for request rate limiting with Redis backend support.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

# Initialize limiter with IP-based rate limiting
# In production with a load balancer, you may need to customize get_remote_address
# to extract the real client IP from X-Forwarded-For header
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please try again later.",
            "retry_after": exc.detail
        }
    )


# Rate limit decorators for different endpoints
# Usage: @limiter.limit("5/minute")
# Common limits:
# - "5/minute" for login endpoints
# - "3/minute" for registration
# - "10/minute" for password reset
# - "100/minute" for general API endpoints
