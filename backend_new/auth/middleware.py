"""Authentication middleware for Clerk integration."""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Optional
import logging

from app.core.config import settings
from .clerk_client import clerk_client
from .permissions import UserContext, UserRole

logger = logging.getLogger(__name__)

class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle Clerk authentication for all requests."""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/health",
            "/healthz",
            "/pipeline/health",
            "/api/health",
            "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request and add user context if authenticated."""
        
        # If neither Clerk nor dev auth is enabled, skip auth (tests/development)
        if not settings.clerk_enabled and not settings.dev_auth_enabled:
            return await call_next(request)
        
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Extract authorization header
        authorization = request.headers.get("Authorization")

        if authorization:
            try:
                # Remove 'Bearer ' prefix if present for comparisons
                raw_token = authorization[7:] if authorization.startswith("Bearer ") else authorization

                # Dev auth: if token matches configured dev token, short-circuit and inject a user
                if settings.dev_auth_enabled and settings.DEV_BEARER_TOKEN == raw_token:
                    user_context = self._create_dev_user_context()
                    request.state.user_context = user_context
                    logger.info(
                        f"Dev-authenticated user: {user_context.user_id} role={user_context.role} tenant={user_context.tenant_id}"
                    )
                # Otherwise, if Clerk is enabled, verify via Clerk
                elif settings.clerk_enabled and clerk_client.enabled:
                    user_data = await clerk_client.verify_token(authorization)
                    user_context = self._create_user_context(user_data)
                    request.state.user_context = user_context
                    logger.info(
                        f"Authenticated user: {user_context.user_id} with role: {user_context.role}"
                    )
            except HTTPException:
                # Token verification failed - let the endpoint handle it
                pass
            except Exception as e:
                logger.error(f"Authentication middleware error: {e}")
        
        response = await call_next(request)
        return response
    
    def _create_user_context(self, user_data: dict) -> UserContext:
        """Create UserContext from Clerk user data."""
        user_id = user_data.get("sub")
        email = user_data.get("email")
        role_str = clerk_client.extract_user_role(user_data)
        tenant_id = clerk_client.extract_tenant_id(user_data)
        
        # Convert role string to UserRole enum
        try:
            role = UserRole(role_str)
        except ValueError:
            logger.warning(f"Unknown role '{role_str}' for user {user_id}, defaulting to candidate")
            role = UserRole.CANDIDATE
        
        return UserContext(
            user_id=user_id,
            email=email,
            role=role,
            tenant_id=tenant_id,
            metadata=user_data.get("metadata", {})
        )

    def _create_dev_user_context(self) -> UserContext:
        """Create a UserContext from DEV_* settings for development bypass."""
        # Normalize role
        role_str = (settings.DEV_USER_ROLE or "candidate").lower()
        try:
            role = UserRole(role_str)
        except ValueError:
            logger.warning(
                f"Unknown DEV_USER_ROLE '{settings.DEV_USER_ROLE}', defaulting to candidate"
            )
            role = UserRole.CANDIDATE
        # Ensure numeric-compatible IDs to satisfy endpoints that cast to int
        dev_user_id = settings.DEV_USER_ID or "1"
        if not str(dev_user_id).isdigit():
            logger.warning("DEV_USER_ID is non-numeric; defaulting to '1' for local testing")
            dev_user_id = "1"
        dev_tenant_id = settings.DEV_TENANT_ID or "1"
        if not str(dev_tenant_id).isdigit():
            logger.warning("DEV_TENANT_ID is non-numeric; defaulting to '1' for local testing")
            dev_tenant_id = "1"

        return UserContext(
            user_id=str(dev_user_id),
            email=settings.DEV_USER_EMAIL,
            role=role,
            tenant_id=str(dev_tenant_id),
            metadata={"role": role.value, "tenant_id": str(dev_tenant_id), "dev": True},
        )

class ClerkHTTPBearer(HTTPBearer):
    """Custom HTTPBearer for Clerk token verification."""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[UserContext]:
        """Verify token and return user context."""
        
        # Check if user context is already set by middleware
        user_context = getattr(request.state, 'user_context', None)
        if user_context:
            return user_context
        
        # Get credentials from request
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        try:
            raw_token = credentials.credentials
            # Dev auth path
            if settings.dev_auth_enabled and settings.DEV_BEARER_TOKEN == raw_token:
                user_context = self._create_dev_user_context()
                request.state.user_context = user_context
                return user_context

            # Verify token via Clerk when enabled
            if settings.clerk_enabled and clerk_client.enabled:
                user_data = await clerk_client.verify_token(raw_token)
                user_context = self._create_user_context(user_data)
                request.state.user_context = user_context
                return user_context
            
            # If neither dev nor Clerk is enabled, auto-inject a default dev user (local development convenience)
            if not settings.clerk_enabled and not settings.dev_auth_enabled:
                logger.info("Auth disabled (no Clerk/dev token). Injecting default dev user context for local development.")
                user_context = self._create_dev_user_context()
                request.state.user_context = user_context
                return user_context
            # Otherwise treat as unauthenticated
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        except HTTPException:
            if self.auto_error:
                raise
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
    
    def _create_user_context(self, user_data: dict) -> UserContext:
        """Create UserContext from Clerk user data."""
        user_id = user_data.get("sub")
        email = user_data.get("email")
        role_str = clerk_client.extract_user_role(user_data)
        tenant_id = clerk_client.extract_tenant_id(user_data)
        
        # Convert role string to UserRole enum
        try:
            role = UserRole(role_str)
        except ValueError:
            logger.warning(f"Unknown role '{role_str}' for user {user_id}, defaulting to candidate")
            role = UserRole.CANDIDATE
        
        return UserContext(
            user_id=user_id,
            email=email,
            role=role,
            tenant_id=tenant_id,
            metadata=user_data.get("metadata", {})
        )

    def _create_dev_user_context(self) -> UserContext:
        """Create a UserContext from DEV_* settings for development bypass."""
        role_str = (settings.DEV_USER_ROLE or "candidate").lower()
        try:
            role = UserRole(role_str)
        except ValueError:
            logger.warning(
                f"Unknown DEV_USER_ROLE '{settings.DEV_USER_ROLE}', defaulting to candidate"
            )
            role = UserRole.CANDIDATE
        dev_user_id = settings.DEV_USER_ID or "1"
        if not str(dev_user_id).isdigit():
            logger.warning("DEV_USER_ID is non-numeric; defaulting to '1' for local testing")
            dev_user_id = "1"
        dev_tenant_id = settings.DEV_TENANT_ID or "1"
        if not str(dev_tenant_id).isdigit():
            logger.warning("DEV_TENANT_ID is non-numeric; defaulting to '1' for local testing")
            dev_tenant_id = "1"
        return UserContext(
            user_id=str(dev_user_id),
            email=settings.DEV_USER_EMAIL,
            role=role,
            tenant_id=str(dev_tenant_id),
            metadata={"role": role.value, "tenant_id": str(dev_tenant_id), "dev": True},
        )

# Global instances
clerk_bearer = ClerkHTTPBearer()
optional_clerk_bearer = ClerkHTTPBearer(auto_error=False)

# Utility to conditionally add middleware

def setup_clerk_middleware(app):
    # Add middleware if Clerk or dev auth is enabled
    if settings.clerk_enabled or settings.dev_auth_enabled:
        app.add_middleware(ClerkAuthMiddleware)