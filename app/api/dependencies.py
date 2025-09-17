from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, Role

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user

async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require admin role for access."""
    if not any(role.name == "admin" for role in current_user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def require_manager(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require manager role for access."""
    user_roles = [role.name for role in current_user.roles]
    if not any(role in ["admin", "manager"] for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required"
        )
    return current_user

async def require_recruiter(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require recruiter role for access."""
    user_roles = [role.name for role in current_user.roles]
    if not any(role in ["admin", "manager", "recruiter"] for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter access required"
        )
    return current_user

async def require_recruiter_owner(
    recruiter_identifier: str,
    current_user: User = Depends(get_current_user)
) -> User:
    """Enforce that a recruiter can only access their own resources.

    Rules:
      - Admin (or manager) can access any recruiter_identifier.
      - Recruiter can only access paths where recruiter_identifier matches their email (case-insensitive) OR a future dedicated field.
      - Other roles forbidden.
    """
    user_roles = [role.name for role in current_user.roles]
    # Admin or manager bypass
    if any(r in ("admin", "manager") for r in user_roles):
        return current_user
    # Must be recruiter
    if "recruiter" not in user_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recruiter access required")
    # Match by email (authoritative identifier for now)
    if (current_user.email or "").lower() != recruiter_identifier.lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: recruiter scope mismatch")
    return current_user

async def require_candidate(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require candidate role for access."""
    user_roles = [role.name for role in current_user.roles]
    if "candidate" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate access required"
        )
    return current_user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get the current user if authenticated, otherwise return None."""
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        return None
    
    return user

def check_permission(permission_name: str, resource: str = None):
    """Check if user has specific permission."""
    def permission_checker(current_user: User = Depends(get_current_user)):
        # Admin has all permissions
        if any(role.name == "admin" for role in current_user.roles):
            return current_user
        
        # Check if user has the specific permission
        for role in current_user.roles:
            for permission in role.permissions:
                if permission.name == permission_name:
                    if resource is None or permission.resource == resource:
                        return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission_name}' required"
        )
    
    return permission_checker


# --- Password freshness enforcement (no schema migration required) ---
def _must_change_password(user: User) -> bool:
    """Return True if the user is flagged to change password.

    We use the `preferences` JSON column to store a soft flag
    to avoid DB migrations: preferences["must_change_password"] == True.
    """
    try:
        prefs = user.preferences or {}
        return bool(prefs.get("must_change_password", False))
    except Exception:
        return False


async def require_password_fresh(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    """Block access to business routes until password is changed when flagged.

    Allowed paths even when flagged: /auth/change-password, /auth/reset-password
    (keep parity with existing auth router endpoints).
    """
    allowed_paths = {"/auth/change-password", "/auth/reset-password"}
    path = request.url.path
    if _must_change_password(current_user) and path not in allowed_paths:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required",
        )
    return current_user