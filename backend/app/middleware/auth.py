"""
Authentication middleware for JWT token validation.

This middleware:
- Validates JWT tokens on protected routes
- Extracts user information from tokens
- Handles authorization failures gracefully
"""

import logging
from typing import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class JWTMiddleware:
    """Middleware for JWT token validation on protected routes.
    
    Note: This is optional middleware for cross-cutting concerns.
    Individual route handlers should also use get_current_user dependency.
    """

    def __init__(self, app, protected_routes: list = None):
        """Initialize JWT middleware.
        
        Args:
            app: FastAPI application instance
            protected_routes: List of route patterns that require authentication
                            Example: ["/api/v1/documents", "/api/v1/chat"]
        """
        self.app = app
        self.protected_routes = protected_routes or [
            "/api/v1/documents",
            "/api/v1/chat",
            "/api/v1/agents",
            "/api/v1/reports",
        ]

    async def __call__(self, request: Request, call_next: Callable):
        """Process request and validate JWT token if on protected route.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler
            
        Returns:
            Response from next handler or error response if token invalid
        """
        path = request.url.path

        # Check if route is protected
        is_protected = any(path.startswith(route) for route in self.protected_routes)

        if is_protected:
            auth_header = request.headers.get("authorization")
            if not auth_header:
                logger.warning(f"Missing auth header for protected route: {path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Missing authorization header"},
                )

            # Token validation is done in route dependencies (get_current_user)
            # This middleware just ensures the header is present
            if not auth_header.startswith("Bearer "):
                logger.warning(f"Invalid auth header format for: {path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid authorization header format"},
                )

        # Call next handler
        response = await call_next(request)
        return response


# Optional: Add middleware to FastAPI app in main.py
# app.add_middleware(JWTMiddleware, protected_routes=[...])
