from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy import JSON
from datetime import datetime, timedelta
from .base import BaseModel, AuditMixin, MetadataMixin
from ..schemas.base import DocumentType

class FileUpload(BaseModel, AuditMixin, MetadataMixin):
    """File upload tracking and management"""
    __tablename__ = 'file_uploads'
    
    # File identification
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False, unique=True)
    file_path = Column(String(1000), nullable=False)
    
    # File properties
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(200), nullable=False)
    file_extension = Column(String(20), nullable=False)
    
    # Content analysis
    file_hash = Column(String(128), nullable=False, index=True)  # SHA-256 hash
    is_duplicate = Column(Boolean, default=False, nullable=False)
    duplicate_of_id = Column(Integer, ForeignKey('file_uploads.id', use_alter=True), nullable=True)
    
    # Document classification
    document_type = Column(SQLEnum(DocumentType), nullable=True, index=True)
    document_category = Column(String(100), nullable=True)  # resume, cover_letter, portfolio, etc.
    
    # Context and associations
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True, index=True)
    candidate_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # Processing status
    processing_status = Column(String(50), default='pending', nullable=False)  # pending, processing, completed, failed
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_error = Column(Text, nullable=True)
    
    # Content extraction
    extracted_text = Column(Text, nullable=True)
    extraction_confidence = Column(Numeric(5, 2), nullable=True)  # 0-100
    language_detected = Column(String(10), nullable=True)
    
    # Security and validation
    virus_scan_status = Column(String(50), default='pending', nullable=False)  # pending, clean, infected, failed
    virus_scan_result = Column(Text, nullable=True)
    is_safe = Column(Boolean, default=False, nullable=False)
    
    # Access control
    is_public = Column(Boolean, default=False, nullable=False)
    access_token = Column(String(255), nullable=True)  # For secure sharing
    access_expires_at = Column(DateTime(timezone=True), nullable=True)
    download_count = Column(Integer, default=0, nullable=False)
    
    # Storage and backup
    storage_provider = Column(String(100), default='local', nullable=False)  # local, s3, gcs, azure
    storage_path = Column(String(1000), nullable=True)  # Cloud storage path
    backup_status = Column(String(50), default='pending', nullable=False)
    backup_path = Column(String(1000), nullable=True)
    
    # Retention and cleanup
    retention_policy = Column(String(100), nullable=True)  # Policy name
    expires_at = Column(DateTime(timezone=True), nullable=True)
    auto_delete = Column(Boolean, default=False, nullable=False)
    
    # Thumbnails and previews
    has_thumbnail = Column(Boolean, default=False, nullable=False)
    thumbnail_path = Column(String(1000), nullable=True)
    has_preview = Column(Boolean, default=False, nullable=False)
    preview_path = Column(String(1000), nullable=True)
    
    # Relationships
    uploader = relationship('User', foreign_keys=[uploaded_by], back_populates='uploaded_files')
    application = relationship('Application', foreign_keys=[application_id])
    job = relationship('Job')
    candidate = relationship('User', foreign_keys=[candidate_id])
    duplicate_of = relationship('FileUpload', remote_side='FileUpload.id')
    duplicates = relationship('FileUpload', back_populates='duplicate_of')
    
    # Related entities
    shares = relationship('FileShare', back_populates='file', cascade='all, delete-orphan')
    versions = relationship('FileVersion', back_populates='file', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<FileUpload(id={self.id}, filename='{self.original_filename}', size={self.file_size_bytes})>"
    
    @property
    def file_size_display(self):
        """Get formatted file size"""
        if self.file_size_bytes < 1024:
            return f"{self.file_size_bytes} B"
        elif self.file_size_bytes < 1024 * 1024:
            return f"{self.file_size_bytes / 1024:.1f} KB"
        elif self.file_size_bytes < 1024 * 1024 * 1024:
            return f"{self.file_size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{self.file_size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    @property
    def is_expired(self):
        """Check if file access has expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    @property
    def is_image(self):
        """Check if file is an image"""
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
        return self.mime_type in image_types
    
    @property
    def is_document(self):
        """Check if file is a document"""
        doc_types = ['application/pdf', 'application/msword', 
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'text/plain', 'text/rtf']
        return self.mime_type in doc_types
    
    def increment_download_count(self):
        """Increment download counter"""
        self.download_count += 1
    
    def generate_access_token(self, expires_in_hours: int = 24):
        """Generate secure access token"""
        import secrets
        self.access_token = secrets.token_urlsafe(32)
        self.access_expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        return self.access_token
    
    def mark_as_processed(self, success: bool = True, error: str = None):
        """Mark file processing as completed"""
        self.processing_completed_at = datetime.utcnow()
        if success:
            self.processing_status = 'completed'
        else:
            self.processing_status = 'failed'
            self.processing_error = error

class Document(BaseModel, AuditMixin, MetadataMixin):
    """Document management with versioning"""
    __tablename__ = 'documents'
    
    # Document identification
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    document_type = Column(SQLEnum(DocumentType), nullable=False, index=True)
    
    # Current version
    current_version_id = Column(Integer, ForeignKey('file_uploads.id', use_alter=True), nullable=True)
    version_number = Column(String(20), default='1.0', nullable=False)
    
    # Document properties
    is_template = Column(Boolean, default=False, nullable=False)
    is_required = Column(Boolean, default=False, nullable=False)
    is_confidential = Column(Boolean, default=False, nullable=False)
    
    # Context and associations
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True, index=True)
    
    # Status and workflow
    status = Column(String(50), default='draft', nullable=False)  # draft, review, approved, rejected
    approval_required = Column(Boolean, default=False, nullable=False)
    approved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Access control
    is_public = Column(Boolean, default=False, nullable=False)
    allowed_roles = Column(JSON, nullable=True)  # Store as JSON array
    allowed_users = Column(JSON, nullable=True)  # Store as JSON array
    
    # Organization
    folder_path = Column(String(1000), nullable=True)
    tags = Column(JSON, nullable=True)  # Store as JSON array
    category = Column(String(100), nullable=True)
    
    # Expiration and retention
    expires_at = Column(DateTime(timezone=True), nullable=True)
    retention_period_days = Column(Integer, nullable=True)
    
    # Relationships
    owner = relationship('User', foreign_keys=[owner_id])
    approver = relationship('User', foreign_keys=[approved_by])
    current_version = relationship('FileUpload', foreign_keys=[current_version_id])
    application = relationship('Application')
    job = relationship('Job')
    
    # Related entities
    versions = relationship('DocumentVersion', back_populates='document', cascade='all, delete-orphan')
    comments = relationship('DocumentComment', back_populates='document', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', type='{self.document_type}')>"
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def approve(self, approved_by: int):
        """Approve the document"""
        if self.approval_required:
            self.status = 'approved'
            self.approved_by = approved_by
            self.approved_at = datetime.utcnow()
    
    def reject(self, reason: str = None):
        """Reject the document"""
        self.status = 'rejected'
        if reason:
            self.notes = reason

class DocumentVersion(BaseModel, AuditMixin):
    """Document version history"""
    __tablename__ = 'document_versions'
    
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey('file_uploads.id'), nullable=False, index=True)
    
    # Version details
    version_number = Column(String(20), nullable=False)
    version_notes = Column(Text, nullable=True)
    is_current = Column(Boolean, default=False, nullable=False)
    
    # Change tracking
    changes_summary = Column(Text, nullable=True)
    previous_version_id = Column(Integer, ForeignKey('document_versions.id', use_alter=True), nullable=True)
    
    # Relationships
    document = relationship('Document', back_populates='versions')
    file = relationship('FileUpload')
    previous_version = relationship('DocumentVersion', remote_side='DocumentVersion.id')
    
    def __repr__(self):
        return f"<DocumentVersion(id={self.id}, document_id={self.document_id}, version='{self.version_number}')>"

class DocumentComment(BaseModel, AuditMixin):
    """Comments on documents"""
    __tablename__ = 'document_comments'
    
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False, index=True)
    commenter_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Comment content
    content = Column(Text, nullable=False)
    comment_type = Column(String(50), default='general', nullable=False)  # general, review, approval
    
    # Threading
    parent_comment_id = Column(Integer, ForeignKey('document_comments.id', use_alter=True), nullable=True)
    
    # Status
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    document = relationship('Document', back_populates='comments')
    commenter = relationship('User', foreign_keys=[commenter_id])
    resolver = relationship('User', foreign_keys=[resolved_by])
    parent_comment = relationship('DocumentComment', remote_side='DocumentComment.id')
    replies = relationship('DocumentComment', back_populates='parent_comment')
    
    def __repr__(self):
        return f"<DocumentComment(id={self.id}, document_id={self.document_id}, type='{self.comment_type}')>"
    
    def resolve(self, resolved_by: int):
        """Mark comment as resolved"""
        self.is_resolved = True
        self.resolved_by = resolved_by
        self.resolved_at = datetime.utcnow()

class FileShare(BaseModel, AuditMixin):
    """File sharing and access management"""
    __tablename__ = 'file_shares'
    
    file_id = Column(Integer, ForeignKey('file_uploads.id'), nullable=False, index=True)
    shared_by = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    shared_with = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # Null for public shares
    
    # Share configuration
    share_type = Column(String(50), nullable=False)  # private, public, link
    access_level = Column(String(50), default='view', nullable=False)  # view, download, edit
    
    # Access control
    access_token = Column(String(255), nullable=True, unique=True)
    password_protected = Column(Boolean, default=False, nullable=False)
    password_hash = Column(String(255), nullable=True)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    max_downloads = Column(Integer, nullable=True)
    current_downloads = Column(Integer, default=0, nullable=False)
    
    # Tracking
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    access_count = Column(Integer, default=0, nullable=False)
    
    # Notifications
    notify_on_access = Column(Boolean, default=False, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationships
    file = relationship('FileUpload', back_populates='shares')
    sharer = relationship('User', foreign_keys=[shared_by])
    recipient = relationship('User', foreign_keys=[shared_with])
    revoker = relationship('User', foreign_keys=[revoked_by])
    
    # Related entities
    access_logs = relationship('FileAccessLog', back_populates='share', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<FileShare(id={self.id}, file_id={self.file_id}, type='{self.share_type}')>"
    
    @property
    def is_expired(self):
        """Check if share is expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    @property
    def is_download_limit_reached(self):
        """Check if download limit is reached"""
        if self.max_downloads:
            return self.current_downloads >= self.max_downloads
        return False
    
    @property
    def can_access(self):
        """Check if share can be accessed"""
        return (self.is_active and not self.is_expired and 
                not self.is_download_limit_reached)
    
    def record_access(self, accessed_by: int = None):
        """Record file access"""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()
        
        if self.access_level in ['download', 'edit']:
            self.current_downloads += 1
    
    def revoke(self, revoked_by: int):
        """Revoke the share"""
        self.is_active = False
        self.revoked_at = datetime.utcnow()
        self.revoked_by = revoked_by

class FileAccessLog(BaseModel):
    """File access logging"""
    __tablename__ = 'file_access_logs'
    
    file_id = Column(Integer, ForeignKey('file_uploads.id'), nullable=False, index=True)
    share_id = Column(Integer, ForeignKey('file_shares.id'), nullable=True, index=True)
    accessed_by = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # Access details
    access_type = Column(String(50), nullable=False)  # view, download, edit
    access_method = Column(String(50), nullable=False)  # direct, share_link, api
    
    # Request information
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    referer = Column(String(500), nullable=True)
    
    # Geographic information
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Success/failure
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(String(500), nullable=True)
    
    # Timing
    accessed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    duration_ms = Column(Integer, nullable=True)  # Request duration
    
    # Relationships
    file = relationship('FileUpload')
    share = relationship('FileShare', back_populates='access_logs')
    user = relationship('User', foreign_keys=[accessed_by])
    
    def __repr__(self):
        return f"<FileAccessLog(id={self.id}, file_id={self.file_id}, type='{self.access_type}')>"

class FileVersion(BaseModel, AuditMixin):
    """File version history"""
    __tablename__ = 'file_versions'
    
    file_id = Column(Integer, ForeignKey('file_uploads.id'), nullable=False, index=True)
    
    # Version details
    version_number = Column(Integer, nullable=False)
    version_notes = Column(Text, nullable=True)
    
    # File properties (snapshot)
    filename = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    file_hash = Column(String(128), nullable=False)
    
    # Storage
    file_path = Column(String(1000), nullable=False)
    is_current = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    file = relationship('FileUpload', back_populates='versions')
    
    def __repr__(self):
        return f"<FileVersion(id={self.id}, file_id={self.file_id}, version={self.version_number})>"

class BulkUpload(BaseModel, AuditMixin):
    """Bulk file upload operations"""
    __tablename__ = 'bulk_uploads'
    
    # Upload session
    session_id = Column(String(100), nullable=False, unique=True, index=True)
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Upload details
    total_files = Column(Integer, nullable=False)
    processed_files = Column(Integer, default=0, nullable=False)
    successful_files = Column(Integer, default=0, nullable=False)
    failed_files = Column(Integer, default=0, nullable=False)
    
    # Status
    status = Column(String(50), default='pending', nullable=False)  # pending, processing, completed, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Configuration
    upload_config = Column(JSON, nullable=True, default={})  # Upload settings
    processing_options = Column(JSON, nullable=True, default={})  # Processing options
    
    # Results
    results = Column(JSON, nullable=True, default=[])  # Per-file results
    errors = Column(JSON, nullable=True, default=[])  # Error details
    
    # Context
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True, index=True)
    
    # Relationships
    uploader = relationship('User', foreign_keys=[uploaded_by])
    application = relationship('Application')
    job = relationship('Job')
    
    def __repr__(self):
        return f"<BulkUpload(id={self.id}, session='{self.session_id}', status='{self.status}')>"
    
    @property
    def progress_percentage(self):
        """Calculate upload progress percentage"""
        if self.total_files > 0:
            return (self.processed_files / self.total_files) * 100
        return 0
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.processed_files > 0:
            return (self.successful_files / self.processed_files) * 100
        return 0
    
    def start_processing(self):
        """Start bulk upload processing"""
        self.status = 'processing'
        self.started_at = datetime.utcnow()
    
    def complete_processing(self):
        """Complete bulk upload processing"""
        self.status = 'completed' if self.failed_files == 0 else 'completed_with_errors'
        self.completed_at = datetime.utcnow()
    
    def add_result(self, filename: str, success: bool, file_id: int = None, error: str = None):
        """Add processing result for a file"""
        result = {
            'filename': filename,
            'success': success,
            'file_id': file_id,
            'error': error,
            'processed_at': datetime.utcnow().isoformat()
        }
        
        if not self.results:
            self.results = []
        self.results.append(result)
        
        self.processed_files += 1
        if success:
            self.successful_files += 1
        else:
            self.failed_files += 1
            if not self.errors:
                self.errors = []
            self.errors.append(result)