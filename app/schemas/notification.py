"""Pydantic schemas for notification management."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    """Notification type classifications."""
    APPLICATION_STATUS = "application_status"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_REMINDER = "interview_reminder"
    INTERVIEW_CANCELLED = "interview_cancelled"
    JOB_MATCH = "job_match"
    MESSAGE_RECEIVED = "message_received"
    PROFILE_UPDATE = "profile_update"
    SYSTEM_ALERT = "system_alert"
    DEADLINE_REMINDER = "deadline_reminder"
    FEEDBACK_REQUEST = "feedback_request"
    ROLE_ASSIGNMENT = "role_assignment"
    TEAM_UPDATE = "team_update"
    PERFORMANCE_ALERT = "performance_alert"
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_REVIEWED = "document_reviewed"
    SKILL_ASSESSMENT = "skill_assessment"
    REFERENCE_REQUEST = "reference_request"
    OFFER_EXTENDED = "offer_extended"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    WELCOME = "welcome"
    ACCOUNT_VERIFICATION = "account_verification"
    PASSWORD_RESET = "password_reset"
    SECURITY_ALERT = "security_alert"
    MAINTENANCE = "maintenance"
    FEATURE_ANNOUNCEMENT = "feature_announcement"
    OTHER = "other"

class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"

class NotificationBase(BaseModel):
    """Base notification schema."""
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channels: List[NotificationChannel] = [NotificationChannel.IN_APP]
    metadata: Dict[str, Any] = {}
    action_url: Optional[str] = Field(None, max_length=500)
    action_text: Optional[str] = Field(None, max_length=50)
    expires_at: Optional[datetime] = None
    
class NotificationCreate(NotificationBase):
    """Schema for creating notifications."""
    recipient_id: str  # Clerk user ID
    tenant_id: Optional[str] = None
    send_immediately: bool = True
    scheduled_for: Optional[datetime] = None

class NotificationBulkCreate(BaseModel):
    """Schema for creating bulk notifications."""
    recipient_ids: List[str] = Field(..., min_items=1, max_items=1000)
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channels: List[NotificationChannel] = [NotificationChannel.IN_APP]
    metadata: Dict[str, Any] = {}
    action_url: Optional[str] = Field(None, max_length=500)
    action_text: Optional[str] = Field(None, max_length=50)
    tenant_id: Optional[str] = None
    send_immediately: bool = True
    scheduled_for: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class NotificationUpdate(BaseModel):
    """Schema for updating notifications."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    message: Optional[str] = Field(None, min_length=1, max_length=1000)
    priority: Optional[NotificationPriority] = None
    action_url: Optional[str] = Field(None, max_length=500)
    action_text: Optional[str] = Field(None, max_length=50)
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class NotificationResponse(NotificationBase):
    """Schema for notification response."""
    id: UUID
    recipient_id: str
    tenant_id: Optional[str] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    is_delivered: bool = False
    delivered_at: Optional[datetime] = None
    delivery_attempts: int = 0
    last_delivery_attempt: Optional[datetime] = None
    delivery_errors: List[str] = []
    created_at: datetime
    updated_at: datetime
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class NotificationMarkReadRequest(BaseModel):
    """Schema for marking notifications as read."""
    notification_ids: List[UUID] = Field(..., min_items=1, max_items=100)

class NotificationPreferences(BaseModel):
    """Schema for user notification preferences."""
    user_id: str  # Clerk user ID
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    in_app_enabled: bool = True
    notification_types: Dict[NotificationType, bool] = {}
    quiet_hours_start: Optional[str] = Field(None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
    quiet_hours_end: Optional[str] = Field(None, pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
    timezone: str = "UTC"
    frequency_limit: int = Field(10, ge=1, le=100)  # Max notifications per hour
    
    class Config:
        from_attributes = True

class NotificationStats(BaseModel):
    """Schema for notification statistics."""
    total_sent: int = 0
    total_delivered: int = 0
    total_read: int = 0
    total_failed: int = 0
    delivery_rate: float = 0.0
    read_rate: float = 0.0
    by_type: Dict[NotificationType, int] = {}
    by_channel: Dict[NotificationChannel, int] = {}
    by_priority: Dict[NotificationPriority, int] = {}
    recent_activity: List[Dict[str, Any]] = []
    
class NotificationTemplate(BaseModel):
    """Schema for notification templates."""
    id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    notification_type: NotificationType
    title_template: str = Field(..., min_length=1, max_length=200)
    message_template: str = Field(..., min_length=1, max_length=1000)
    default_priority: NotificationPriority = NotificationPriority.MEDIUM
    default_channels: List[NotificationChannel] = [NotificationChannel.IN_APP]
    variables: List[str] = []  # Template variables like {user_name}, {job_title}
    is_active: bool = True
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True