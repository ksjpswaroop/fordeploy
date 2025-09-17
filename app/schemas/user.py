from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from .base import TimestampMixin, UserRole

# UserLogin schema for authentication
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# User schemas
class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: bool = True

class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole

class UserUpdate(BaseModel):
    """User update schema"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None

class RoleBrief(BaseModel):
    name: str
    display_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class UserResponse(UserBase, TimestampMixin):
    """User response schema"""
    id: int
    role: Optional[UserRole] = None
    roles: List[RoleBrief] = []
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class UserProfile(UserResponse):
    """Extended user profile"""
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None

# Authentication schemas
class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str

class PasswordChangeRequest(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

# Role schemas
class RoleBase(BaseModel):
    """Base role schema"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    permissions: List[str] = []

class RoleCreate(RoleBase):
    """Role creation schema"""
    pass

class RoleUpdate(BaseModel):
    """Role update schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    permissions: Optional[List[str]] = None

class RoleResponse(RoleBase, TimestampMixin):
    """Role response schema"""
    id: int
    
    model_config = ConfigDict(from_attributes=True)

# Permission schemas
class PermissionBase(BaseModel):
    """Base permission schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)

class PermissionResponse(PermissionBase):
    """Permission response schema"""
    id: int
    
    model_config = ConfigDict(from_attributes=True)

# Additional schemas for specific operations
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    must_change_password: bool = False

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class PermissionCreate(BaseModel):
    name: str
    description: str = ""

class PermissionUpdate(BaseModel):
    name: str
    description: str = ""