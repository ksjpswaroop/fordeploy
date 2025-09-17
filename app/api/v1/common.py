"""Common API endpoints shared across all user roles."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import os
from contextlib import suppress
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user, UserContext
from app.core.database import get_db
from app.models.communication import Notification
from app.schemas.communication import NotificationResponse as CommNotificationResponse
from app.schemas.file import FileMetadata, FileType
from app.schemas.common import (
    FileUploadResponse,
    SearchRequest,
    SearchResponse,
    HealthCheckResponse,
    SystemStatusResponse,
    PaginatedResponse,
    SuccessResponse,
    PaginationMeta,
)

router = APIRouter(prefix="/common", tags=["common"])

# File Upload and Management
@router.post("/files/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    file_type: FileType = Query(...),
    description: Optional[str] = Query(None),
    is_public: bool = Query(False),
    current_user: UserContext = Depends(get_current_user)
):
    """Upload a file to the system with proper categorization."""
    # Stub implementation
    now = datetime.utcnow()
    return FileUploadResponse(
        id=uuid4(),
        filename=file.filename,
        original_filename=file.filename,
        file_size=0,
        mime_type=file.content_type or "application/octet-stream",
        file_type=file_type.value,
        upload_url=f"/files/{uuid4()}/download",
        download_url=None,
        is_public=is_public,
        description=description,
        uploaded_by=current_user.user_id,
        created_at=now
    )

@router.get("/files", response_model=PaginatedResponse[FileMetadata])
async def get_files(
    file_type: Optional[FileType] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserContext = Depends(get_current_user)
):
    """Get files accessible to the current user."""
    # Stub: return empty list with pagination meta
    return PaginatedResponse[FileMetadata](
        data=[],
        meta=PaginationMeta(
            total=0,
            page=1,
            page_size=limit,
            total_pages=0,
            has_next=False,
            has_prev=False
        )
    )

@router.get("/files/{file_id}", response_model=FileMetadata)
async def get_file_metadata(
    file_id: UUID,
    current_user: UserContext = Depends(get_current_user)
):
    """Get metadata for a specific file."""
    # Stub placeholder metadata
    now = datetime.utcnow()
    return FileMetadata(
        id=file_id,
        filename=f"placeholder-{file_id}.dat",
        original_filename=f"placeholder-{file_id}.dat",
        file_size=1234,
        content_type="application/octet-stream",
        file_type=FileType.OTHER,
        description="Placeholder file metadata",
        is_public=False,
        owner_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        storage_path=f"/storage/{file_id}",
        download_url=f"/common/files/{file_id}/download",
        thumbnail_url=None,
        metadata={},
        virus_scan_status="clean",
        virus_scan_date=now,
        access_count=0,
        last_accessed=None,
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
        expires_at=None
    )

@router.get("/files/{file_id}/download")
async def download_file(
    file_id: UUID,
    current_user: UserContext = Depends(get_current_user)
):
    """Download a file if user has access permissions."""
    # Stub: pretend file exists; in real impl we'd return StreamingResponse
    return {"message": "Download placeholder - content not implemented", "file_id": str(file_id)}

@router.delete("/files/{file_id}", response_model=SuccessResponse)
async def delete_file(
    file_id: UUID,
    current_user: UserContext = Depends(get_current_user)
):
    """Delete a file if user has permission."""
    # Stub deletion success
    return SuccessResponse(success=True, message="File deleted (stub)")

"""
Deprecated: Notifications endpoints have moved to /api/v1/notifications.
We intentionally removed legacy handlers here to avoid duplication.
"""

@router.get("/notifications")
async def legacy_notifications_redirect():
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="Endpoint moved to /api/v1/notifications")

@router.get("/notifications/unread-count")
async def legacy_notifications_unread_redirect():
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="Endpoint moved to /api/v1/notifications")

# Search Functionality
@router.post("/search", response_model=SearchResponse)
async def search_content(
    search_request: SearchRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """Search across various content types based on user permissions."""
    # Stub: echo back empty results
    return SearchResponse(
        results=[],
        total_count=0,
        query=search_request.query,
        took_ms=1,
        facets={}
    )

@router.get("/search/suggestions", response_model=List[str])
async def get_search_suggestions(
    query: str = Query(..., min_length=2),
    content_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    current_user: UserContext = Depends(get_current_user)
):
    """Get search suggestions based on partial query."""
    # Stub suggestions
    return [f"{query} suggestion 1", f"{query} suggestion 2"]

@router.get("/search/recent", response_model=List[str])
async def get_recent_searches(
    limit: int = Query(10, ge=1, le=50),
    current_user: UserContext = Depends(get_current_user)
):
    """Get recent search queries for the current user."""
    # Stub recent searches
    return ["jobs", "candidates", "analytics"][:limit]

# Health and System Status
_SERVICE_START = datetime.utcnow()

@router.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check(db: Session = Depends(get_db)):
    """Basic health check endpoint.

    Attempts a lightweight DB connectivity check but never raises 5xx; returns a
    degraded status if the check fails. Provides uptime and environment.
    """
    status_str = "healthy"
    with suppress(Exception):
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            status_str = "degraded"
    uptime = int((datetime.utcnow() - _SERVICE_START).total_seconds())
    return HealthCheckResponse(
        status=status_str,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        uptime_seconds=uptime,
        environment=os.getenv("ENVIRONMENT", "unknown")
    )

@router.get("/health/detailed", response_model=SystemStatusResponse, tags=["health"])
async def detailed_health_check(
    current_user: UserContext = Depends(get_current_user)
):
    """Detailed system health check - requires authentication."""
    # TODO: Implement detailed health check
    # - Check all system components
    # - Include performance metrics
    # - Check external integrations
    # - Return detailed status report
    # - Only accessible to admin users
    if not current_user.has_permission("system:health:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for detailed health check"
        )
    
    # Stub detailed system status (requires permission check above)
    now = datetime.utcnow()
    return SystemStatusResponse(
        overall_status="healthy",
        timestamp=now,
        version="1.0.0",
        uptime_seconds=12345,
        environment="development",
        services=[
            {"name": "database", "status": "healthy", "response_time_ms": 5.2, "last_check": now},
            {"name": "cache", "status": "healthy", "response_time_ms": 0.8, "last_check": now},
        ],
        database_status="healthy",
        cache_status="healthy",
        storage_status="healthy",
        memory_usage_percent=12.5,
        cpu_usage_percent=7.3,
        disk_usage_percent=40.1
    )

# System Information
@router.get("/system/info", response_model=Dict[str, Any])
async def get_system_info(
    current_user: UserContext = Depends(get_current_user)
):
    """Get system information and configuration."""
    # TODO: Implement system info
    # - Return non-sensitive system information
    # - Include feature flags
    # - Show system capabilities
    # - Filter based on user role
    if not current_user.has_permission("system:info:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for system information"
        )
    
    # Stub system info
    return {
        "app_name": "AI Driven Recruitment Backend",
        "version": "1.0.0",
        "environment": "development",
        "features": {
            "file_upload": True,
            "notifications": True,
            "search": True,
            "analytics": True,
            "email": True
        },
        "limits": {
            "max_file_size": 10 * 1024 * 1024,
            "allowed_file_types": ["pdf", "doc", "docx", "txt"],
            "pagination_limit": 100
        }
    }

# User Activity Logging
@router.post("/activity/log", response_model=SuccessResponse)
async def log_user_activity(
    activity_data: Dict[str, Any],
    current_user: UserContext = Depends(get_current_user)
):
    """Log user activity for analytics and audit purposes."""
    # Stub: pretend activity logged
    return SuccessResponse(success=True, message="Activity logged (stub)")

# Configuration and Settings
@router.get("/config/client", response_model=Dict[str, Any])
async def get_client_config(
    current_user: UserContext = Depends(get_current_user)
):
    """Get client-side configuration based on user role."""
    # Stub client config
    return {
        "feature_flags": {
            "new_dashboard": True,
            "advanced_search": True,
            "recruiter_metrics": True
        },
        "user_role": current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        "api_version": "v1",
        "environment": "development"
    }

# Utility Endpoints
@router.get("/time", response_model=Dict[str, str])
async def get_server_time():
    """Get current server time in ISO8601 format (UTC)."""
    return {"server_time": datetime.utcnow().isoformat() + "Z"}

@router.get("/version", response_model=Dict[str, str])
async def get_api_version():
    """Get API version information."""
    return {
        "version": "1.0.0",
        "build": "development",
        "api_version": "v1"
    }