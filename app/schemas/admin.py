"""Pydantic schemas for admin functionality."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    """User role definitions."""
    ADMIN = "admin"
    MANAGER = "manager"
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"
    VIEWER = "viewer"

class SystemSettingType(str, Enum):
    """System setting type classifications."""
    GENERAL = "general"
    SECURITY = "security"
    EMAIL = "email"
    NOTIFICATION = "notification"
    INTEGRATION = "integration"
    FEATURE_FLAG = "feature_flag"
    PERFORMANCE = "performance"
    ANALYTICS = "analytics"
    BILLING = "billing"
    COMPLIANCE = "compliance"

class AuditAction(str, Enum):
    """Audit log action types."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"
    ASSIGN = "assign"
    UNASSIGN = "unassign"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    RESET_PASSWORD = "reset_password"
    CHANGE_ROLE = "change_role"
    BULK_OPERATION = "bulk_operation"
    SYSTEM_CONFIG = "system_config"
    DATA_MIGRATION = "data_migration"
    SECURITY_EVENT = "security_event"

# Role Management Schemas
class RolePermission(BaseModel):
    """Role permission schema."""
    id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    resource: str = Field(..., min_length=1, max_length=100)  # jobs, candidates, etc.
    action: str = Field(..., min_length=1, max_length=50)  # create, read, update, delete
    conditions: Dict[str, Any] = {}  # Additional permission conditions
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RoleCreate(BaseModel):
    """Schema for creating roles."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permissions: List[str] = []  # Permission IDs
    is_system_role: bool = False
    tenant_id: Optional[str] = None

class RoleUpdate(BaseModel):
    """Schema for updating roles."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permissions: Optional[List[str]] = None  # Permission IDs
    is_active: Optional[bool] = None

class RoleResponse(BaseModel):
    """Role response schema."""
    id: UUID
    name: str
    description: Optional[str] = None
    permissions: List[RolePermission] = []
    user_count: int = 0
    is_system_role: bool = False
    is_active: bool = True
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# User Role Assignment Schemas
class UserRoleAssignment(BaseModel):
    """User role assignment schema."""
    user_id: str = Field(..., description="Clerk user ID")
    role_ids: List[str] = Field(..., min_items=1, description="Role IDs to assign")
    tenant_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    reason: Optional[str] = Field(None, max_length=500)

class UserRoleResponse(BaseModel):
    """User role response schema."""
    user_id: str
    user_email: str
    user_name: str
    roles: List[RoleResponse] = []
    tenant_id: Optional[str] = None
    assigned_at: datetime
    assigned_by: str  # Admin user ID
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# System Settings Schemas
class SystemSettingCreate(BaseModel):
    """Schema for creating system settings."""
    key: str = Field(..., min_length=1, max_length=200)
    value: str = Field(..., max_length=5000)
    setting_type: SystemSettingType
    description: Optional[str] = Field(None, max_length=500)
    is_encrypted: bool = False
    is_public: bool = False
    tenant_id: Optional[str] = None

class SystemSettingUpdate(BaseModel):
    """Schema for updating system settings."""
    value: Optional[str] = Field(None, max_length=5000)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None

class SystemSettingResponse(BaseModel):
    """System setting response schema."""
    id: UUID
    key: str
    value: str
    setting_type: SystemSettingType
    description: Optional[str] = None
    is_encrypted: bool = False
    is_public: bool = False
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    updated_by: str  # Admin user ID
    
    class Config:
        from_attributes = True

# Tenant Management Schemas
class TenantCreate(BaseModel):
    """Schema for creating tenants."""
    name: str = Field(..., min_length=1, max_length=200)
    domain: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    settings: Dict[str, Any] = {}
    max_users: int = Field(100, ge=1, le=10000)
    max_jobs: int = Field(1000, ge=1, le=100000)
    features: List[str] = []  # Enabled features
    billing_plan: str = "basic"
    contact_email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    contact_name: str = Field(..., min_length=1, max_length=100)

class TenantUpdate(BaseModel):
    """Schema for updating tenants."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    settings: Optional[Dict[str, Any]] = None
    max_users: Optional[int] = Field(None, ge=1, le=10000)
    max_jobs: Optional[int] = Field(None, ge=1, le=100000)
    features: Optional[List[str]] = None
    billing_plan: Optional[str] = None
    contact_email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    contact_name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None

class TenantResponse(BaseModel):
    """Tenant response schema."""
    id: UUID
    name: str
    domain: str
    description: Optional[str] = None
    settings: Dict[str, Any] = {}
    max_users: int
    max_jobs: int
    current_users: int = 0
    current_jobs: int = 0
    features: List[str] = []
    billing_plan: str
    contact_email: str
    contact_name: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Audit Log Schemas
class AuditLogResponse(BaseModel):
    """Audit log response schema."""
    id: UUID
    user_id: str  # Clerk user ID
    user_email: str
    action: AuditAction
    resource_type: str  # job, candidate, user, etc.
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    tenant_id: Optional[str] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True

class AuditLogFilter(BaseModel):
    """Audit log filter schema."""
    user_id: Optional[str] = None
    action: Optional[AuditAction] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tenant_id: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=1000)

# System Monitoring Schemas
class SystemMetrics(BaseModel):
    """System metrics schema."""
    timestamp: datetime
    active_users: int = 0
    total_users: int = 0
    active_jobs: int = 0
    total_jobs: int = 0
    total_applications: int = 0
    pending_applications: int = 0
    scheduled_interviews: int = 0
    system_load: float = 0.0
    memory_usage_percent: float = 0.0
    cpu_usage_percent: float = 0.0
    disk_usage_percent: float = 0.0
    database_connections: int = 0
    api_requests_per_minute: int = 0
    error_rate_percent: float = 0.0
    average_response_time_ms: float = 0.0
    
class SystemAlert(BaseModel):
    """System alert schema."""
    id: UUID
    alert_type: str = Field(..., min_length=1, max_length=100)
    severity: str = Field(..., pattern=r'^(low|medium|high|critical)$')
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    details: Dict[str, Any] = {}
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None  # Admin user ID
    tenant_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class BulkUserOperation(BaseModel):
    """Bulk user operation schema."""
    user_ids: List[str] = Field(..., min_items=1, max_items=1000)
    operation: str = Field(..., pattern=r'^(activate|deactivate|delete|assign_role|remove_role|reset_password)$')
    parameters: Dict[str, Any] = {}  # Operation-specific parameters
    reason: Optional[str] = Field(None, max_length=500)
    
class BulkOperationResult(BaseModel):
    """Bulk operation result schema."""
    operation: str
    total_requested: int
    successful_count: int
    failed_count: int
    successful_items: List[str] = []  # User IDs
    failed_items: List[Dict[str, str]] = []  # [{"user_id": "123", "error": "reason"}]
    started_at: datetime
    completed_at: datetime