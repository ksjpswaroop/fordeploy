"""Clerk authentication client integration."""

import os
from typing import Optional, Dict, Any
from clerk_backend_api import Clerk
from clerk_backend_api.models import User as ClerkUser
from fastapi import HTTPException, status
import jwt
from jwt.exceptions import InvalidTokenError
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class ClerkAuthClient:
    """Clerk authentication client for token verification and user management."""
    
    def __init__(self) -> None:
        if not settings.clerk_enabled:
            # Clerk is disabled; create a no-op client
            self._enabled = False
            return
        
        self.secret_key = settings.CLERK_SECRET_KEY
        if not self.secret_key:
            raise ValueError("CLERK_SECRET_KEY setting is required")
        
        self.clerk = Clerk(bearer_auth=self.secret_key)
        self.jwt_secret = settings.CLERK_JWT_SECRET
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return getattr(self, "_enabled", False)
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify Clerk JWT token and return user information.
        
        Args:
            token: JWT token from Clerk
            
        Returns:
            Dict containing user information and claims
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token[7:]
            
            # Verify JWT token
            if self.jwt_secret:
                payload = jwt.decode(
                    token, 
                    self.jwt_secret, 
                    algorithms=["RS256"],
                    options={"verify_signature": True}
                )
            else:
                # Fallback to Clerk API verification
                payload = await self._verify_with_clerk_api(token)
            
            return payload
            
        except InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def _verify_with_clerk_api(self, token: str) -> Dict[str, Any]:
        """Verify token using Clerk API as fallback."""
        try:
            # Use Clerk SDK to verify token
            # This is a placeholder - actual implementation depends on Clerk SDK version
            user = await self.clerk.users.get_user(token)
            return {
                "sub": user.id,
                "email": user.email_addresses[0].email_address if user.email_addresses else None,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "metadata": user.public_metadata or {}
            }
        except Exception as e:
            logger.error(f"Clerk API verification failed: {e}")
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[ClerkUser]:
        """Get user information by Clerk user ID.
        
        Args:
            user_id: Clerk user ID
            
        Returns:
            ClerkUser object or None if not found
        """
        try:
            user = await self.clerk.users.get_user(user_id)
            return user
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def update_user_metadata(self, user_id: str, metadata: Dict[str, Any]) -> bool:
        """Update user metadata in Clerk.
        
        Args:
            user_id: Clerk user ID
            metadata: Metadata to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self.clerk.users.update_user(
                user_id=user_id,
                public_metadata=metadata
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update user metadata for {user_id}: {e}")
            return False
    
    def extract_user_role(self, user_data: Dict[str, Any]) -> str:
        """Extract user role from Clerk user data.
        
        Args:
            user_data: User data from token verification
            
        Returns:
            User role string (default: 'candidate')
        """
        metadata = user_data.get("metadata", {})
        return metadata.get("role", "candidate")
    
    def extract_tenant_id(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Extract tenant/organization ID from user data.
        
        Args:
            user_data: User data from token verification
            
        Returns:
            Tenant ID or None
        """
        metadata = user_data.get("metadata", {})
        return metadata.get("tenant_id")

# Global instance
clerk_client = ClerkAuthClient()