from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import TimestampMixin, NotificationType, Priority

# Message schemas
class MessageBase(BaseModel):
    """Base message schema"""
    subject: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    priority: Priority = Priority.MEDIUM
    is_read: bool = False

class MessageCreate(MessageBase):
    """Message creation schema"""
    recipient_id: int
    related_application_id: Optional[int] = None
    related_job_id: Optional[int] = None

class MessageUpdate(BaseModel):
    """Message update schema"""
    is_read: Optional[bool] = None
    priority: Optional[Priority] = None

class MessageResponse(MessageBase, TimestampMixin):
    """Message response schema"""
    id: int
    sender_id: int
    recipient_id: int
    related_application_id: Optional[int] = None
    related_job_id: Optional[int] = None
    
    # Related data
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class MessageDetailResponse(MessageResponse):
    """Detailed message response"""
    thread_messages: Optional[List['MessageResponse']] = []
    attachments: Optional[List[Dict[str, Any]]] = []

# Notification schemas
class NotificationBase(BaseModel):
    """Base notification schema"""
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    notification_type: NotificationType
    priority: Priority = Priority.MEDIUM
    is_read: bool = False
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class NotificationCreate(NotificationBase):
    """Notification creation schema"""
    user_id: int
    related_id: Optional[int] = None  # Related entity ID (job, application, etc.)

class NotificationUpdate(BaseModel):
    """Notification update schema"""
    is_read: Optional[bool] = None

class NotificationResponse(NotificationBase, TimestampMixin):
    """Notification response schema"""
    id: int
    user_id: int
    related_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

# Call log schemas
class CallLogBase(BaseModel):
    """Base call log schema"""
    call_type: str = Field(..., pattern="^(incoming|outgoing)$")
    duration_minutes: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    outcome: Optional[str] = Field(None, max_length=100)
    follow_up_required: bool = False
    follow_up_date: Optional[datetime] = None

class CallLogCreate(CallLogBase):
    """Call log creation schema"""
    contact_id: int  # candidate or recruiter ID
    related_application_id: Optional[int] = None
    related_job_id: Optional[int] = None

class CallLogUpdate(BaseModel):
    """Call log update schema"""
    duration_minutes: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    outcome: Optional[str] = Field(None, max_length=100)
    follow_up_required: Optional[bool] = None
    follow_up_date: Optional[datetime] = None

class CallLogResponse(CallLogBase, TimestampMixin):
    """Call log response schema"""
    id: int
    recruiter_id: int
    contact_id: int
    related_application_id: Optional[int] = None
    related_job_id: Optional[int] = None
    call_date: datetime
    
    # Related data
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    recruiter_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Email template schemas
class EmailTemplateBase(BaseModel):
    """Base email template schema"""
    name: str = Field(..., min_length=1, max_length=100)
    subject: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    template_type: str = Field(..., max_length=50)  # welcome, interview_invite, rejection, etc.
    is_active: bool = True
    variables: Optional[List[str]] = []  # Available template variables

class EmailTemplateCreate(EmailTemplateBase):
    """Email template creation schema"""
    pass

class EmailTemplateUpdate(BaseModel):
    """Email template update schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    subject: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    template_type: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    variables: Optional[List[str]] = None

class EmailTemplateResponse(EmailTemplateBase, TimestampMixin):
    """Email template response schema"""
    id: int
    created_by: int
    
    model_config = ConfigDict(from_attributes=True)

# Communication preferences schemas
class CommunicationPreferencesBase(BaseModel):
    """Base communication preferences schema"""
    email_notifications: bool = True
    sms_notifications: bool = False
    push_notifications: bool = True
    application_updates: bool = True
    interview_reminders: bool = True
    job_recommendations: bool = True
    marketing_emails: bool = False
    frequency: str = Field(default="immediate", pattern="^(immediate|daily|weekly)$")
    quiet_hours_start: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = Field(default="UTC", max_length=50)

class CommunicationPreferencesUpdate(BaseModel):
    """Communication preferences update schema"""
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    application_updates: Optional[bool] = None
    interview_reminders: Optional[bool] = None
    job_recommendations: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    frequency: Optional[str] = Field(None, pattern="^(immediate|daily|weekly)$")
    quiet_hours_start: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    timezone: Optional[str] = Field(None, max_length=50)

class CommunicationPreferencesResponse(CommunicationPreferencesBase, TimestampMixin):
    """Communication preferences response schema"""
    id: int
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Bulk communication schemas
class BulkMessageCreate(BaseModel):
    """Bulk message creation schema"""
    recipient_ids: List[int]
    subject: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    priority: Priority = Priority.MEDIUM
    send_immediately: bool = True
    scheduled_at: Optional[datetime] = None

class BulkMessageResponse(BaseModel):
    """Bulk message response"""
    message_id: str
    total_recipients: int
    sent_count: int
    failed_count: int
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# List response schemas
class MessageListResponse(BaseModel):
    """Message list response with pagination"""
    messages: List[MessageResponse]
    total: int
    skip: int
    limit: int
    
    model_config = ConfigDict(from_attributes=True)

class CommunicationHistory(BaseModel):
    """Communication history for a candidate/recruiter"""
    messages: List[MessageResponse]
    call_logs: List[CallLogResponse]
    notifications: List[NotificationResponse]
    total_interactions: int
    last_contact: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)