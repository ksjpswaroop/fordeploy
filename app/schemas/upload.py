from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import TimestampMixin, DocumentType

# File upload schemas
class FileUploadBase(BaseModel):
    """Base file upload schema"""
    filename: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0)
    content_type: str = Field(..., max_length=100)
    document_type: DocumentType
    description: Optional[str] = Field(None, max_length=500)
    is_public: bool = False
    tags: Optional[List[str]] = []

class FileUploadCreate(FileUploadBase):
    """File upload creation schema"""
    file_data: str  # Base64 encoded file data or file path
    related_entity_type: Optional[str] = Field(None, max_length=50)  # user, job, application
    related_entity_id: Optional[int] = None
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'image/jpeg',
            'image/png',
            'image/gif',
            'application/zip',
            'text/csv',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]
        if v not in allowed_types:
            raise ValueError(f'Content type {v} not allowed')
        return v
    
    @validator('file_size')
    def validate_file_size(cls, v):
        max_size = 10 * 1024 * 1024  # 10MB
        if v > max_size:
            raise ValueError(f'File size {v} exceeds maximum allowed size of {max_size} bytes')
        return v

class FileUploadUpdate(BaseModel):
    """File upload update schema"""
    filename: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None
    document_type: Optional[DocumentType] = None

class FileUploadResponse(FileUploadBase, TimestampMixin):
    """File upload response schema"""
    id: int
    file_path: str
    file_url: str
    uploaded_by: int
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    download_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Metadata
    file_hash: Optional[str] = None
    virus_scan_status: Optional[str] = None  # pending, clean, infected
    virus_scan_date: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class FileUploadDetailResponse(FileUploadResponse):
    """Detailed file upload response"""
    uploader_name: Optional[str] = None
    uploader_email: Optional[str] = None
    access_history: Optional[List[Dict[str, Any]]] = []
    sharing_permissions: Optional[List[Dict[str, Any]]] = []

# Document schemas
class DocumentBase(BaseModel):
    """Base document schema"""
    title: str = Field(..., min_length=1, max_length=200)
    document_type: DocumentType
    version: str = Field(default="1.0", max_length=20)
    status: str = Field(default="draft", pattern="^(draft|review|approved|archived)$")
    content: Optional[str] = None  # For text documents
    metadata: Optional[Dict[str, Any]] = {}
    is_template: bool = False
    is_required: bool = False

class DocumentCreate(DocumentBase):
    """Document creation schema"""
    file_id: Optional[int] = None  # Link to uploaded file
    related_entity_type: Optional[str] = Field(None, max_length=50)
    related_entity_id: Optional[int] = None
    parent_document_id: Optional[int] = None  # For document versions

class DocumentUpdate(BaseModel):
    """Document update schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    version: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, pattern="^(draft|review|approved|archived)$")
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_template: Optional[bool] = None
    is_required: Optional[bool] = None

class DocumentResponse(DocumentBase, TimestampMixin):
    """Document response schema"""
    id: int
    created_by: int
    file_id: Optional[int] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    parent_document_id: Optional[int] = None
    
    # Related data
    file_info: Optional[FileUploadResponse] = None
    creator_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Resume parsing schemas
class ResumeParseRequest(BaseModel):
    """Resume parsing request"""
    file_id: int
    extract_skills: bool = True
    extract_experience: bool = True
    extract_education: bool = True
    extract_contact: bool = True
    language: str = Field(default="en", max_length=5)

class ParsedContact(BaseModel):
    """Parsed contact information"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None

class ParsedExperience(BaseModel):
    """Parsed work experience"""
    company: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_current: bool = False

class ParsedEducation(BaseModel):
    """Parsed education information"""
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None
    location: Optional[str] = None

class ResumeParseResponse(BaseModel):
    """Resume parsing response"""
    file_id: int
    parsing_status: str = "completed"  # processing, completed, failed
    confidence_score: float = 0.0
    
    # Parsed data
    contact_info: Optional[ParsedContact] = None
    summary: Optional[str] = None
    skills: Optional[List[str]] = []
    experience: Optional[List[ParsedExperience]] = []
    education: Optional[List[ParsedEducation]] = []
    certifications: Optional[List[str]] = []
    languages: Optional[List[str]] = []
    
    # Metadata
    total_experience_years: Optional[float] = None
    parsed_at: datetime
    parsing_errors: Optional[List[str]] = []
    
    model_config = ConfigDict(from_attributes=True)

# File sharing schemas
class FileShareBase(BaseModel):
    """Base file sharing schema"""
    permission_level: str = Field(..., pattern="^(view|download|edit)$")
    expires_at: Optional[datetime] = None
    password_protected: bool = False
    download_limit: Optional[int] = Field(None, gt=0)
    allow_comments: bool = False

class FileShareCreate(FileShareBase):
    """File sharing creation schema"""
    file_id: int
    shared_with_user_id: Optional[int] = None  # Specific user
    shared_with_email: Optional[str] = None  # External email
    share_type: str = Field(..., pattern="^(internal|external|public)$")
    password: Optional[str] = Field(None, min_length=6)

class FileShareUpdate(BaseModel):
    """File sharing update schema"""
    permission_level: Optional[str] = Field(None, pattern="^(view|download|edit)$")
    expires_at: Optional[datetime] = None
    password_protected: Optional[bool] = None
    download_limit: Optional[int] = Field(None, gt=0)
    allow_comments: Optional[bool] = None
    is_active: Optional[bool] = None

class FileShareResponse(FileShareBase, TimestampMixin):
    """File sharing response schema"""
    id: int
    file_id: int
    shared_by: int
    shared_with_user_id: Optional[int] = None
    shared_with_email: Optional[str] = None
    share_type: str
    share_token: str
    share_url: str
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    is_active: bool = True
    
    # Related data
    file_info: Optional[FileUploadResponse] = None
    shared_by_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Bulk upload schemas
class BulkUploadRequest(BaseModel):
    """Bulk file upload request"""
    files: List[FileUploadCreate]
    related_entity_type: Optional[str] = Field(None, max_length=50)
    related_entity_id: Optional[int] = None
    auto_process: bool = True  # Auto-parse resumes, etc.

class BulkUploadResponse(BaseModel):
    """Bulk upload response"""
    upload_id: str
    total_files: int
    successful_uploads: int
    failed_uploads: int
    processing_status: str = "completed"  # processing, completed, partial_failure
    uploaded_files: List[FileUploadResponse] = []
    errors: List[Dict[str, Any]] = []
    
    model_config = ConfigDict(from_attributes=True)

# File search schemas
class FileSearchRequest(BaseModel):
    """File search request"""
    query: Optional[str] = None
    document_types: Optional[List[DocumentType]] = []
    content_types: Optional[List[str]] = []
    uploaded_by: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    tags: Optional[List[str]] = []
    file_size_min: Optional[int] = None
    file_size_max: Optional[int] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    include_content: bool = False  # Search within file content

class FileSearchResponse(BaseModel):
    """File search response"""
    total_results: int
    files: List[FileUploadResponse]
    facets: Optional[Dict[str, Dict[str, int]]] = {}  # Aggregated filters
    search_time_ms: int
    
    model_config = ConfigDict(from_attributes=True)