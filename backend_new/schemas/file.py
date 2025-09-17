"""Pydantic schemas for file management."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum

class FileType(str, Enum):
    """File type classifications."""
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    PORTFOLIO = "portfolio"
    CERTIFICATE = "certificate"
    TRANSCRIPT = "transcript"
    REFERENCE = "reference"
    PROFILE_PHOTO = "profile_photo"
    COMPANY_LOGO = "company_logo"
    JOB_ATTACHMENT = "job_attachment"
    SYSTEM_DOCUMENT = "system_document"
    OTHER = "other"

class FileMetadata(BaseModel):
    """Schema for file metadata."""
    id: UUID
    filename: str = Field(..., min_length=1, max_length=255)
    original_filename: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., ge=0)
    content_type: str = Field(..., min_length=1, max_length=100)
    file_type: FileType
    description: Optional[str] = Field(None, max_length=500)
    is_public: bool = False
    owner_id: str  # Clerk user ID
    tenant_id: Optional[str] = None
    storage_path: str
    download_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metadata: Dict[str, Any] = {}  # Additional file-specific metadata
    virus_scan_status: str = "pending"  # pending, clean, infected, error
    virus_scan_date: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class FileUploadRequest(BaseModel):
    """Schema for file upload request."""
    file_type: FileType
    description: Optional[str] = Field(None, max_length=500)
    is_public: bool = False
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)

class FileUploadResponse(BaseModel):
    """Schema for file upload response."""
    id: UUID
    filename: str
    file_size: int
    content_type: str
    file_type: FileType
    upload_url: Optional[str] = None  # For direct upload to cloud storage
    download_url: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class FileBatchUploadRequest(BaseModel):
    """Schema for batch file upload request."""
    files: list[FileUploadRequest] = Field(..., min_items=1, max_items=10)

class FileBatchUploadResponse(BaseModel):
    """Schema for batch file upload response."""
    successful_uploads: list[FileUploadResponse] = []
    failed_uploads: list[Dict[str, Any]] = []
    total_files: int
    successful_count: int
    failed_count: int