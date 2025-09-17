"""Admin API endpoints for role management and system settings."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID

from app.auth.dependencies import require_admin, get_current_user
from app.auth.permissions import UserContext
from app.schemas.admin import (
    RoleCreate, RoleUpdate, RoleResponse,
    UserRoleAssignment, UserRoleResponse,
    SystemSettingUpdate, SystemSettingResponse,
    TenantCreate, TenantUpdate, TenantResponse,
    AuditLogResponse, AuditLogFilter
)
from app.schemas.common import PaginatedResponse, SuccessResponse

router = APIRouter(prefix="/admin", tags=["admin"])

# Role Management Endpoints
@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: UserContext = Depends(require_admin)
):
    """Create a new role with specified permissions."""
    from datetime import datetime
    return RoleResponse(
        id=UUID(int=0),
        name=role_data.name,
        description=role_data.description,
        permissions=[],
        user_count=0,
        is_system_role=role_data.is_system_role,
        is_active=True,
        tenant_id=role_data.tenant_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: UserContext = Depends(require_admin)
):
    """List all available roles and their permissions."""
    return []

@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    current_user: UserContext = Depends(require_admin)
):
    """Get detailed information about a specific role."""
    from datetime import datetime
    return RoleResponse(
        id=role_id,
        name="placeholder",
        description="Placeholder role",
        permissions=[],
        user_count=0,
        is_system_role=False,
        is_active=True,
        tenant_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    current_user: UserContext = Depends(require_admin)
):
    """Update role permissions and settings."""
    from datetime import datetime
    return RoleResponse(
        id=role_id,
        name=role_data.name or "updated-role",
        description=role_data.description or "Updated role",
        permissions=[],
        user_count=0,
        is_system_role=False,
        is_active=True,
        tenant_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@router.delete("/roles/{role_id}", response_model=SuccessResponse)
async def delete_role(
    role_id: UUID,
    current_user: UserContext = Depends(require_admin)
):
    """Delete a role (if not in use)."""
    return SuccessResponse(success=True, message="Role deleted (stub)")

# User Role Assignment Endpoints
@router.post("/users/{user_id}/roles", response_model=UserRoleResponse)
async def assign_user_role(
    user_id: UUID,
    assignment: UserRoleAssignment,
    current_user: UserContext = Depends(require_admin)
):
    """Assign a role to a user."""
    from datetime import datetime
    return UserRoleResponse(
        user_id=assignment.user_id,
        user_email="user@example.com",
        user_name="User Placeholder",
        roles=[],
        tenant_id=assignment.tenant_id,
        assigned_at=datetime.utcnow(),
        assigned_by=current_user.user_id,
        expires_at=assignment.expires_at
    )

@router.get("/users/{user_id}/roles", response_model=List[UserRoleResponse])
async def get_user_roles(
    user_id: UUID,
    current_user: UserContext = Depends(require_admin)
):
    """Get all roles assigned to a user."""
    return []

@router.delete("/users/{user_id}/roles/{role_id}", response_model=SuccessResponse)
async def revoke_user_role(
    user_id: UUID,
    role_id: UUID,
    current_user: UserContext = Depends(require_admin)
):
    """Revoke a role from a user."""
    return SuccessResponse(success=True, message="Role revoked (stub)")

# System Settings Endpoints
@router.get("/settings", response_model=SystemSettingResponse)
async def get_system_settings(
    current_user: UserContext = Depends(require_admin)
):
    """Get current system settings and configuration."""
    from datetime import datetime
    return SystemSettingResponse(
        id=UUID(int=0),
        key="setting.key",
        value="value",
        setting_type="general",
        description="Placeholder setting",
        is_encrypted=False,
        is_public=False,
        tenant_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        updated_by=current_user.user_id
    )

@router.put("/settings", response_model=SystemSettingResponse)
async def update_system_settings(
    settings: SystemSettingUpdate,
    current_user: UserContext = Depends(require_admin)
):
    """Update system settings and configuration."""
    from datetime import datetime
    return SystemSettingResponse(
        id=UUID(int=0),
        key="setting.key",
        value=settings.value or "updated",
        setting_type="general",
        description=settings.description or "Updated setting",
        is_encrypted=False,
        is_public=settings.is_public if settings.is_public is not None else False,
        tenant_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        updated_by=current_user.user_id
    )

# Tenant Management Endpoints
@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: UserContext = Depends(require_admin)
):
    """Create a new tenant organization."""
    from datetime import datetime
    return TenantResponse(
        id=UUID(int=0),
        name=tenant_data.name,
        domain=tenant_data.domain,
        description=tenant_data.description,
        settings=tenant_data.settings,
        max_users=tenant_data.max_users,
        max_jobs=tenant_data.max_jobs,
        current_users=0,
        current_jobs=0,
        features=tenant_data.features,
        billing_plan=tenant_data.billing_plan,
        contact_email=tenant_data.contact_email,
        contact_name=tenant_data.contact_name,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@router.get("/tenants", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserContext = Depends(require_admin)
):
    """List all tenant organizations."""
    return PaginatedResponse[TenantResponse](
        data=[],
        meta={
            "total": 0,
            "page": 1,
            "page_size": limit,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False
        }
    )

@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    current_user: UserContext = Depends(require_admin)
):
    """Get detailed information about a tenant."""
    from datetime import datetime
    return TenantResponse(
        id=tenant_id,
        name="Placeholder Tenant",
        domain="placeholder.local",
        description="Placeholder tenant",
        settings={},
        max_users=100,
        max_jobs=1000,
        current_users=0,
        current_jobs=0,
        features=[],
        billing_plan="basic",
        contact_email="admin@example.com",
        contact_name="Admin",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: TenantUpdate,
    current_user: UserContext = Depends(require_admin)
):
    """Update tenant information and settings."""
    from datetime import datetime
    return TenantResponse(
        id=tenant_id,
        name=tenant_data.name or "Updated Tenant",
        domain="placeholder.local",
        description=tenant_data.description or "Updated tenant",
        settings=tenant_data.settings or {},
        max_users=tenant_data.max_users or 100,
        max_jobs=tenant_data.max_jobs or 1000,
        current_users=0,
        current_jobs=0,
        features=tenant_data.features or [],
        billing_plan=tenant_data.billing_plan or "basic",
        contact_email=tenant_data.contact_email or "admin@example.com",
        contact_name=tenant_data.contact_name or "Admin",
        is_active=tenant_data.is_active if tenant_data.is_active is not None else True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

@router.delete("/tenants/{tenant_id}", response_model=SuccessResponse)
async def delete_tenant(
    tenant_id: UUID,
    current_user: UserContext = Depends(require_admin)
):
    """Delete a tenant (with proper cleanup)."""
    return SuccessResponse(success=True, message="Tenant deleted (stub)")

# Audit and Monitoring Endpoints
@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
async def get_audit_logs(
    filters: AuditLogFilter = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserContext = Depends(require_admin)
):
    """Get system audit logs with filtering."""
    return PaginatedResponse[AuditLogResponse](
        data=[],
        meta={
            "total": 0,
            "page": 1,
            "page_size": limit,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False
        }
    )

@router.get("/system-health", response_model=dict)
async def get_system_health(
    current_user: UserContext = Depends(require_admin)
):
    """Get system health and performance metrics."""
    return {"status": "healthy", "services": {}, "metrics": {}}

@router.post("/maintenance-mode", response_model=SuccessResponse)
async def toggle_maintenance_mode(
    enabled: bool,
    current_user: UserContext = Depends(require_admin)
):
    """Enable or disable system maintenance mode."""
    return SuccessResponse(success=True, message=f"Maintenance mode set to {enabled} (stub)")