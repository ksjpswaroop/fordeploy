"""Role-Based Access Control (RBAC) and permission decorators."""

from functools import wraps
from typing import List, Optional, Callable, Any
from fastapi import HTTPException, status, Depends, Request
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class UserRole(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    MANAGER = "manager"
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"

class Permission(str, Enum):
    """System permissions."""
    # User Management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Role Management
    ROLE_CREATE = "role:create"
    ROLE_READ = "role:read"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    
    # Job Management
    JOB_CREATE = "job:create"
    JOB_READ = "job:read"
    JOB_UPDATE = "job:update"
    JOB_DELETE = "job:delete"
    JOB_ASSIGN = "job:assign"
    
    # Candidate Management
    CANDIDATE_CREATE = "candidate:create"
    CANDIDATE_READ = "candidate:read"
    CANDIDATE_UPDATE = "candidate:update"
    CANDIDATE_DELETE = "candidate:delete"
    
    # Application Management
    APPLICATION_CREATE = "application:create"
    APPLICATION_READ = "application:read"
    APPLICATION_UPDATE = "application:update"
    APPLICATION_DELETE = "application:delete"
    
    # Interview Management
    INTERVIEW_CREATE = "interview:create"
    INTERVIEW_READ = "interview:read"
    INTERVIEW_UPDATE = "interview:update"
    INTERVIEW_DELETE = "interview:delete"
    
    # Communication
    MESSAGE_SEND = "message:send"
    MESSAGE_READ = "message:read"

    # Notifications
    NOTIFICATION_READ = "notification:read"
    NOTIFICATION_UPDATE = "notification:update"
    
    # Analytics
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_ADMIN = "analytics:admin"
    
    # Settings
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"

# Role-Permission Matrix
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        # Full access to everything
        Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE, Permission.USER_DELETE,
        Permission.ROLE_CREATE, Permission.ROLE_READ, Permission.ROLE_UPDATE, Permission.ROLE_DELETE,
        Permission.JOB_CREATE, Permission.JOB_READ, Permission.JOB_UPDATE, Permission.JOB_DELETE, Permission.JOB_ASSIGN,
        Permission.CANDIDATE_CREATE, Permission.CANDIDATE_READ, Permission.CANDIDATE_UPDATE, Permission.CANDIDATE_DELETE,
        Permission.APPLICATION_CREATE, Permission.APPLICATION_READ, Permission.APPLICATION_UPDATE, Permission.APPLICATION_DELETE,
        Permission.INTERVIEW_CREATE, Permission.INTERVIEW_READ, Permission.INTERVIEW_UPDATE, Permission.INTERVIEW_DELETE,
    Permission.MESSAGE_SEND, Permission.MESSAGE_READ,
    Permission.NOTIFICATION_READ, Permission.NOTIFICATION_UPDATE,
        Permission.ANALYTICS_READ, Permission.ANALYTICS_ADMIN,
        Permission.SETTINGS_READ, Permission.SETTINGS_UPDATE,
    ],
    UserRole.MANAGER: [
        # Team management and oversight
        Permission.USER_READ, Permission.USER_UPDATE,
        Permission.JOB_CREATE, Permission.JOB_READ, Permission.JOB_UPDATE, Permission.JOB_ASSIGN,
    Permission.CANDIDATE_CREATE, Permission.CANDIDATE_READ, Permission.CANDIDATE_UPDATE,
        Permission.APPLICATION_READ, Permission.APPLICATION_UPDATE,
        Permission.INTERVIEW_CREATE, Permission.INTERVIEW_READ, Permission.INTERVIEW_UPDATE,
    Permission.MESSAGE_SEND, Permission.MESSAGE_READ,
    Permission.NOTIFICATION_READ, Permission.NOTIFICATION_UPDATE,
        Permission.ANALYTICS_READ,
        Permission.SETTINGS_READ,
    ],
    UserRole.RECRUITER: [
        # Recruitment activities
        Permission.JOB_READ,
        Permission.CANDIDATE_CREATE, Permission.CANDIDATE_READ, Permission.CANDIDATE_UPDATE,
        Permission.APPLICATION_CREATE, Permission.APPLICATION_READ, Permission.APPLICATION_UPDATE,
        Permission.INTERVIEW_CREATE, Permission.INTERVIEW_READ, Permission.INTERVIEW_UPDATE,
    Permission.MESSAGE_SEND, Permission.MESSAGE_READ,
    Permission.NOTIFICATION_READ, Permission.NOTIFICATION_UPDATE,
        Permission.ANALYTICS_READ,
    ],
    UserRole.CANDIDATE: [
        # Self-service only
        Permission.APPLICATION_CREATE, Permission.APPLICATION_READ,
        Permission.INTERVIEW_READ,
    Permission.MESSAGE_SEND, Permission.MESSAGE_READ,
    Permission.NOTIFICATION_READ, Permission.NOTIFICATION_UPDATE,
    ]
}

class UserContext:
    """Current user context with role and permissions."""
    
    def __init__(self, user_id: str, email: str, role: UserRole, 
                 tenant_id: Optional[str] = None, metadata: Optional[dict] = None):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.tenant_id = tenant_id
        self.metadata = metadata or {}
        self.permissions = ROLE_PERMISSIONS.get(role, [])
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions
    
    def has_role(self, *roles: UserRole) -> bool:
        """Check if user has any of the specified roles."""
        return self.role in roles
    
    def can_access_resource(self, resource_owner_id: str) -> bool:
        """Check if user can access a resource based on ownership."""
        # Admins can access everything
        if self.role == UserRole.ADMIN:
            return True
        
        # Users can access their own resources
        if self.user_id == resource_owner_id:
            return True
        
        # Managers and recruiters can access resources in their tenant
        if self.role in [UserRole.MANAGER, UserRole.RECRUITER] and self.tenant_id:
            # This would need additional logic to check if resource belongs to same tenant
            return True
        
        return False

def get_current_user(request: Request) -> UserContext:
    """Get current user context from request.
    
    This function should be used as a FastAPI dependency.
    """
    user_context = getattr(request.state, 'user_context', None)
    if not user_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_context

def require_role(*roles: UserRole):
    """Decorator to require specific roles.
    
    Args:
        *roles: Required roles
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user context from kwargs (injected by dependency)
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, UserContext):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not current_user.has_role(*roles):
                logger.warning(
                    f"User {current_user.user_id} with role {current_user.role} "
                    f"attempted to access endpoint requiring roles: {roles}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {[r.value for r in roles]}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_permission(*permissions: Permission):
    """Decorator to require specific permissions.
    
    Args:
        *permissions: Required permissions
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user context from kwargs
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, UserContext):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check if user has any of the required permissions
            has_permission = any(current_user.has_permission(perm) for perm in permissions)
            
            if not has_permission:
                logger.warning(
                    f"User {current_user.user_id} with role {current_user.role} "
                    f"attempted to access endpoint requiring permissions: {permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {[p.value for p in permissions]}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_ownership(resource_id_param: str = "resource_id"):
    """Decorator to require resource ownership or admin role.
    
    Args:
        resource_id_param: Parameter name containing the resource owner ID
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user context and resource ID
            current_user = None
            resource_owner_id = kwargs.get(resource_id_param)
            
            for key, value in kwargs.items():
                if isinstance(value, UserContext):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not resource_owner_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Resource ID parameter '{resource_id_param}' is required"
                )
            
            if not current_user.can_access_resource(resource_owner_id):
                logger.warning(
                    f"User {current_user.user_id} attempted to access resource "
                    f"owned by {resource_owner_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Insufficient permissions for this resource."
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# FastAPI Dependencies
CurrentUser = Depends(get_current_user)
RequireAdmin = Depends(lambda user: require_role(UserRole.ADMIN))
RequireManager = Depends(lambda user: require_role(UserRole.MANAGER, UserRole.ADMIN))
RequireRecruiter = Depends(lambda user: require_role(UserRole.RECRUITER, UserRole.MANAGER, UserRole.ADMIN))