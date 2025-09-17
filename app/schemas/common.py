from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional, Generic, TypeVar, List
from datetime import datetime, date
from uuid import UUID

T = TypeVar('T')

# Health check schemas
class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    database: str = Field(..., description="Database status")
    redis: str = Field(..., description="Redis status")
    services: Dict[str, str] = Field(..., description="Individual service statuses")
    
    model_config = ConfigDict(from_attributes=True)

class SystemStatsResponse(BaseModel):
    """Detailed system statistics response"""
    status: str
    timestamp: datetime
    uptime_seconds: int
    total_users: int
    total_jobs: int
    total_applications: int
    active_jobs: int
    memory_usage_mb: float
    cpu_usage_percent: float
    disk_usage_percent: float
    database_connections: int
    redis_connections: int
    
    model_config = ConfigDict(from_attributes=True)

# File upload schemas
class FileUploadResponse(BaseModel):
    """File upload response"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    document_type: str
    upload_url: str
    uploaded_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# System information schemas
class SystemFeatures(BaseModel):
    """System features"""
    file_upload: bool = True
    notifications: bool = True
    search: bool = True
    analytics: bool = True
    email: bool = True
    
    model_config = ConfigDict(from_attributes=True)

class SystemLimits(BaseModel):
    """System limits"""
    max_file_size: int
    allowed_file_types: list
    pagination_limit: int
    
    model_config = ConfigDict(from_attributes=True)

class SystemInfoResponse(BaseModel):
    """System information response"""
    app_name: str
    version: str
    environment: str
    features: SystemFeatures
    limits: SystemLimits
    
    model_config = ConfigDict(from_attributes=True)

# Error response schemas
class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    error: str = "validation_error"
    message: str
    field_errors: Dict[str, list] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

# Pagination schemas
class PaginationMeta(BaseModel):
    """Pagination metadata"""
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedResponse(BaseModel, Generic[T]):
    """Base paginated response"""
    data: List[T]
    meta: PaginationMeta
    
    model_config = ConfigDict(from_attributes=True)

# Generic response schemas
class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)

class DateRangeFilter(BaseModel):
    """Date range filter schema"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    model_config = ConfigDict(from_attributes=True)

# File and Upload schemas
class FileUploadResponse(BaseModel):
    """File upload response schema"""
    id: UUID
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    file_type: str
    upload_url: str
    download_url: Optional[str] = None
    is_public: bool = False
    description: Optional[str] = None
    uploaded_by: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Notification schemas
class NotificationCreate(BaseModel):
    """Notification creation schema"""
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    notification_type: str = Field(..., max_length=50)
    recipient_id: str
    priority: str = Field(default="normal", pattern=r'^(low|normal|high|urgent)$')
    action_url: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None

class NotificationResponse(BaseModel):
    """Notification response schema"""
    id: UUID
    title: str
    message: str
    notification_type: str
    recipient_id: str
    priority: str
    is_read: bool = False
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    read_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Search schemas
class SearchRequest(BaseModel):
    """Search request schema"""
    query: str = Field(..., min_length=1, max_length=500)
    content_types: List[str] = []
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = Field(None, max_length=50)
    sort_order: str = Field(default="desc", pattern=r'^(asc|desc)$')
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    include_highlights: bool = True

class SearchResult(BaseModel):
    """Individual search result schema"""
    id: str
    title: str
    content_type: str
    summary: str
    url: Optional[str] = None
    score: float
    highlights: List[str] = []
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class SearchResponse(BaseModel):
    """Search response schema"""
    results: List[SearchResult]
    total_count: int
    query: str
    took_ms: int
    facets: Optional[Dict[str, Any]] = None
    suggestions: List[str] = []
    
    model_config = ConfigDict(from_attributes=True)

# Health and System schemas
class HealthCheckResponse(BaseModel):
    """Health check response schema"""
    status: str = "healthy"
    timestamp: datetime
    version: str
    uptime_seconds: int
    environment: str
    
    model_config = ConfigDict(from_attributes=True)

class ServiceStatus(BaseModel):
    """Individual service status schema"""
    name: str
    status: str
    response_time_ms: Optional[float] = None
    last_check: datetime
    error_message: Optional[str] = None

class SystemStatusResponse(BaseModel):
    """Detailed system status response schema"""
    overall_status: str
    timestamp: datetime
    version: str
    uptime_seconds: int
    environment: str
    services: List[ServiceStatus]
    database_status: str
    cache_status: str
    storage_status: str
    memory_usage_percent: float
    cpu_usage_percent: float
    disk_usage_percent: float
    
    model_config = ConfigDict(from_attributes=True)