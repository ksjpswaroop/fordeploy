"""Authentication dependencies for FastAPI endpoints."""

from fastapi import Depends, HTTPException, Request, status
from typing import Optional
import logging

from .middleware import clerk_bearer, optional_clerk_bearer
from .permissions import UserContext, UserRole, Permission

logger = logging.getLogger(__name__)

# Basic authentication dependencies
async def get_current_user(user_context: UserContext = Depends(clerk_bearer)) -> UserContext:
    """Get the current authenticated user."""
    return user_context

async def get_current_user_optional(user_context: Optional[UserContext] = Depends(optional_clerk_bearer)) -> Optional[UserContext]:
    """Get the current user if authenticated, None otherwise."""
    return user_context

async def require_authenticated(user_context: UserContext = Depends(get_current_user)) -> UserContext:
    """Require any authenticated user."""
    return user_context

# Role-based dependencies
async def require_admin(user_context: UserContext = Depends(get_current_user)) -> UserContext:
    """Require admin role."""
    if not user_context.has_role(UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user_context

async def require_manager(user_context: UserContext = Depends(get_current_user)) -> UserContext:
    """Require manager role or higher."""
    if not user_context.has_role(UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required"
        )
    return user_context

async def require_recruiter(user_context: UserContext = Depends(get_current_user)) -> UserContext:
    """Require recruiter (or manager/admin) role."""
    if not user_context.has_role(UserRole.RECRUITER, UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter or higher access required"
        )
    return user_context

async def require_candidate(user_context: UserContext = Depends(get_current_user)) -> UserContext:
    """Require candidate role or higher (any authenticated user)."""
    return user_context

# Permission-based dependencies
def require_permission(permission: Permission):
    """Create a dependency that requires a specific permission."""
    async def permission_dependency(user_context: UserContext = Depends(get_current_user)) -> UserContext:
        if not user_context.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission.value}' required"
            )
        return user_context
    return permission_dependency

# Tenant-based dependencies
async def get_tenant_id(user_context: UserContext = Depends(get_current_user)) -> str:
    """Get the current user's tenant ID."""
    if not user_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with any tenant"
        )
    return user_context.tenant_id

def require_same_tenant(resource_tenant_id: str):
    """Create a dependency that ensures user belongs to the same tenant as the resource."""
    async def tenant_dependency(user_context: UserContext = Depends(get_current_user)) -> UserContext:
        if user_context.tenant_id != resource_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: different tenant"
            )
        return user_context
    return tenant_dependency

# Ownership-based dependencies
def require_ownership_or_role(resource_user_id: str, allowed_roles: list[UserRole] = None):
    """Create a dependency that requires ownership or specific roles."""
    if allowed_roles is None:
        allowed_roles = [UserRole.ADMIN, UserRole.MANAGER]
    
    async def ownership_dependency(user_context: UserContext = Depends(get_current_user)) -> UserContext:
        # Check if user owns the resource
        if user_context.user_id == resource_user_id:
            return user_context
        
        # Check if user has allowed role
        if any(user_context.has_role(role) for role in allowed_roles):
            return user_context
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient permissions"
        )
    
    return ownership_dependency

# Composite dependencies
async def require_admin_or_manager(user_context: UserContext = Depends(get_current_user)) -> UserContext:
    """Require admin or manager role."""
    if not (user_context.has_role(UserRole.ADMIN) or user_context.has_role(UserRole.MANAGER)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Manager access required"
        )
    return user_context

async def require_recruiter_or_manager(user_context: UserContext = Depends(get_current_user)) -> UserContext:
    """Require recruiter, manager, or admin role."""
    allowed_roles = [UserRole.RECRUITER, UserRole.MANAGER, UserRole.ADMIN]
    if not any(user_context.has_role(role) for role in allowed_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter, Manager, or Admin access required"
        )
    return user_context

# Utility functions for request context
async def get_user_from_request(request: Request) -> Optional[UserContext]:
    """Get user context from request state (set by middleware)."""
    return getattr(request.state, 'user_context', None)

def create_permission_dependency(permissions: list[Permission]):
    """Create a dependency that requires any of the specified permissions."""
    async def multi_permission_dependency(user_context: UserContext = Depends(get_current_user)) -> UserContext:
        if not any(user_context.has_permission(perm) for perm in permissions):
            permission_names = [perm.value for perm in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these permissions required: {', '.join(permission_names)}"
            )
        return user_context
    return multi_permission_dependency

# Specific business logic dependencies
async def require_job_management_access(user_context: UserContext = Depends(get_current_user)) -> UserContext:
    """Require access to job management features."""
    required_permissions = [Permission.MANAGE_JOBS, Permission.VIEW_JOBS]
    if not any(user_context.has_permission(perm) for perm in required_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Job management access required"
        )
    return user_context

async def require_candidate_management_access(user_context: UserContext = Depends(get_current_user)) -> UserContext:
    """Require access to candidate management features."""
    required_permissions = [Permission.MANAGE_CANDIDATES, Permission.VIEW_CANDIDATES]
    if not any(user_context.has_permission(perm) for perm in required_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate management access required"
        )
    return user_context

async def require_interview_management_access(user_context: UserContext = Depends(get_current_user)) -> UserContext:
    """Require access to interview management features."""
    required_permissions = [Permission.MANAGE_INTERVIEWS, Permission.SCHEDULE_INTERVIEWS]
    if not any(user_context.has_permission(perm) for perm in required_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Interview management access required"
        )
    return user_context