"""
Security headers middleware for production deployments.
Adds essential security headers to protect against common web vulnerabilities.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.
    
    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking attacks
    - X-XSS-Protection: Legacy XSS filter (for older browsers)
    - Referrer-Policy: Controls referrer information
    - Strict-Transport-Security: Forces HTTPS (production only)
    - Content-Security-Policy: Controls resource loading (basic policy)
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking - deny embedding in frames
        response.headers["X-Frame-Options"] = "DENY"
        
        # Legacy XSS protection for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy - disable potentially dangerous features
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        
        # HSTS - Only add in production with HTTPS
        if settings.ENVIRONMENT == "production":
            # max-age=31536000 is 1 year
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        
        # Content Security Policy — strict in production
        # 'unsafe-inline' and 'unsafe-eval' are removed in production for XSS hardening.
        # If your Next.js frontend needs them, add through CSP_REPORT_ONLY or adjust per-app.
        if settings.ENVIRONMENT == "production":
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss:; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "base-uri 'self'"
            )
        else:
            # Development: relaxed policy for hot-reload, dev tools, and inline styles
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss:"
            )
        
        return response
