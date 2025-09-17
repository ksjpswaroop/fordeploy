from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from sqlalchemy import JSON
from datetime import datetime
from .base import BaseModel, AuditMixin, MetadataMixin
from ..schemas.base import NotificationType, Priority

class Message(BaseModel, AuditMixin, MetadataMixin):
    """Messages between users"""
    __tablename__ = 'messages'
    
    # Participants
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Message content
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default='direct', nullable=False)  # direct, broadcast, system
    
    # Context
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True, index=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=True, index=True)
    
    # Status and tracking
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    
    # Priority and flags
    priority = Column(SQLEnum(Priority), default=Priority.MEDIUM, nullable=False)
    is_urgent = Column(Boolean, default=False, nullable=False)
    requires_response = Column(Boolean, default=False, nullable=False)
    response_deadline = Column(DateTime(timezone=True), nullable=True)
    
    # Threading
    thread_id = Column(String(100), nullable=True, index=True)  # For grouping related messages
    parent_message_id = Column(Integer, ForeignKey('messages.id', use_alter=True), nullable=True)
    
    # Attachments
    attachments = Column(JSON, nullable=True, default=[])  # File references
    
    # Delivery tracking
    delivery_status = Column(String(50), default='sent', nullable=False)  # sent, delivered, failed
    delivery_attempts = Column(Integer, default=0, nullable=False)
    last_delivery_attempt = Column(DateTime(timezone=True), nullable=True)
    
    # External integrations
    external_message_id = Column(String(255), nullable=True)
    email_message_id = Column(String(255), nullable=True)
    
    # Relationships
    sender = relationship('User', foreign_keys=[sender_id], back_populates='sent_messages')
    recipient = relationship('User', foreign_keys=[recipient_id], back_populates='received_messages')
    application = relationship('Application')
    job = relationship('Job')
    interview = relationship('Interview')
    parent_message = relationship('Message', remote_side='Message.id')
    replies = relationship('Message', back_populates='parent_message')
    
    def __repr__(self):
        return f"<Message(id={self.id}, sender_id={self.sender_id}, recipient_id={self.recipient_id}, type='{self.message_type}')>"
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
    
    def archive(self):
        """Archive the message"""
        if not self.is_archived:
            self.is_archived = True
            self.archived_at = datetime.utcnow()
    
    @property
    def is_overdue(self):
        """Check if response is overdue"""
        if self.requires_response and self.response_deadline:
            return datetime.utcnow() > self.response_deadline and not self.is_read
        return False

class Notification(BaseModel, AuditMixin):
    """System notifications"""
    __tablename__ = 'notifications'
    
    # Recipient
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Notification content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    
    # Context and references
    reference_type = Column(String(50), nullable=True)  # application, job, interview, etc.
    reference_id = Column(Integer, nullable=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True, index=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=True, index=True)
    
    # Status and tracking
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    is_dismissed = Column(Boolean, default=False, nullable=False, index=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Priority and behavior
    priority = Column(SQLEnum(Priority), default=Priority.MEDIUM, nullable=False)
    is_actionable = Column(Boolean, default=False, nullable=False)
    action_url = Column(String(500), nullable=True)
    action_text = Column(String(100), nullable=True)
    
    # Delivery channels
    send_email = Column(Boolean, default=False, nullable=False)
    send_sms = Column(Boolean, default=False, nullable=False)
    send_push = Column(Boolean, default=True, nullable=False)
    
    # Delivery tracking
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    sms_sent = Column(Boolean, default=False, nullable=False)
    sms_sent_at = Column(DateTime(timezone=True), nullable=True)
    push_sent = Column(Boolean, default=False, nullable=False)
    push_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Grouping and batching
    group_key = Column(String(100), nullable=True, index=True)  # For grouping similar notifications
    batch_id = Column(String(100), nullable=True)  # For batch processing
    
    # Additional data
    data = Column(JSON, nullable=True, default={})  # Extra context data
    
    # Relationships
    # Explicitly bind the relationship to the recipient "user_id" to avoid ambiguity
    # with AuditMixin.created_by/updated_by which also reference users.id
    user = relationship('User', back_populates='notifications', foreign_keys=[user_id])
    application = relationship('Application')
    job = relationship('Job')
    interview = relationship('Interview')
    
    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type='{self.notification_type}', read={self.is_read})>"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
    
    def dismiss(self):
        """Dismiss the notification"""
        if not self.is_dismissed:
            self.is_dismissed = True
            self.dismissed_at = datetime.utcnow()
    
    @property
    def is_expired(self):
        """Check if notification is expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    @property
    def delivery_status(self):
        """Get overall delivery status"""
        channels = []
        if self.send_email:
            channels.append('email' if self.email_sent else 'email_pending')
        if self.send_sms:
            channels.append('sms' if self.sms_sent else 'sms_pending')
        if self.send_push:
            channels.append('push' if self.push_sent else 'push_pending')
        
        return channels

# Additional indexes for query performance
Index('ix_notifications_created_at', Notification.created_at)
Index('ix_notifications_user_created_at', Notification.user_id, Notification.created_at)

class CallLog(BaseModel, AuditMixin):
    """Phone call logs"""
    __tablename__ = 'call_logs'
    
    # Participants
    caller_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # Nullable for external calls
    
    # Call details
    phone_number = Column(String(20), nullable=False)
    call_type = Column(String(50), nullable=False)  # inbound, outbound, missed
    call_direction = Column(String(20), nullable=False)  # incoming, outgoing
    
    # Context
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True, index=True)
    candidate_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Call status
    status = Column(String(50), nullable=False)  # completed, missed, busy, failed, no_answer
    disposition = Column(String(100), nullable=True)  # Call outcome
    
    # Call content
    purpose = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_date = Column(DateTime(timezone=True), nullable=True)
    
    # Recording
    is_recorded = Column(Boolean, default=False, nullable=False)
    recording_url = Column(String(500), nullable=True)
    recording_duration = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=True)
    
    # Quality and feedback
    call_quality = Column(Integer, nullable=True)  # 1-5 rating
    connection_quality = Column(String(50), nullable=True)  # excellent, good, fair, poor
    
    # External integration
    external_call_id = Column(String(255), nullable=True)
    provider = Column(String(100), nullable=True)  # Twilio, etc.
    
    # Cost tracking
    cost_cents = Column(Integer, nullable=True)
    billing_duration = Column(Integer, nullable=True)
    
    # Relationships
    caller = relationship('User', foreign_keys=[caller_id])
    recipient = relationship('User', foreign_keys=[recipient_id])
    application = relationship('Application')
    job = relationship('Job')
    candidate = relationship('User', foreign_keys=[candidate_id])
    
    def __repr__(self):
        return f"<CallLog(id={self.id}, caller_id={self.caller_id}, type='{self.call_type}', status='{self.status}')>"
    
    @property
    def duration_display(self):
        """Get formatted call duration"""
        if self.duration_seconds:
            minutes = self.duration_seconds // 60
            seconds = self.duration_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"
    
    @property
    def cost_display(self):
        """Get formatted cost"""
        if self.cost_cents:
            return f"${self.cost_cents / 100:.2f}"
        return "$0.00"

class EmailTemplate(BaseModel, AuditMixin, MetadataMixin):
    """Email templates for various communications"""
    __tablename__ = 'email_templates'
    
    # Template identification
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    template_type = Column(String(100), nullable=False, index=True)  # application_received, interview_scheduled, etc.
    
    # Template content
    subject = Column(String(500), nullable=False)
    html_content = Column(Text, nullable=False)
    text_content = Column(Text, nullable=True)
    
    # Template variables
    variables = Column(JSON, nullable=True, default=[])  # Available template variables
    sample_data = Column(JSON, nullable=True, default={})  # Sample data for preview
    
    # Usage and status
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Categorization
    category = Column(String(100), nullable=True)  # recruitment, onboarding, general
    audience = Column(String(100), nullable=True)  # candidates, recruiters, managers
    
    # Localization
    language = Column(String(10), default='en', nullable=False)
    
    # Version control
    version = Column(String(20), default='1.0', nullable=False)
    parent_template_id = Column(Integer, ForeignKey('email_templates.id'), nullable=True)
    
    # Relationships
    parent_template = relationship('EmailTemplate', remote_side='EmailTemplate.id')
    child_templates = relationship('EmailTemplate', back_populates='parent_template')
    
    def __repr__(self):
        return f"<EmailTemplate(id={self.id}, name='{self.name}', type='{self.template_type}')>"
    
    def render(self, context: dict):
        """Render template with provided context"""
        # This would integrate with a templating engine like Jinja2
        # For now, simple string replacement
        rendered_subject = self.subject
        rendered_html = self.html_content
        rendered_text = self.text_content or ''
        
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            rendered_subject = rendered_subject.replace(placeholder, str(value))
            rendered_html = rendered_html.replace(placeholder, str(value))
            rendered_text = rendered_text.replace(placeholder, str(value))
        
        return {
            'subject': rendered_subject,
            'html_content': rendered_html,
            'text_content': rendered_text
        }
    
    def increment_usage(self):
        """Increment usage counter"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()

class CommunicationPreference(BaseModel, AuditMixin):
    """User communication preferences"""
    __tablename__ = 'communication_preferences'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True, index=True)
    
    # Email preferences
    email_notifications = Column(Boolean, default=True, nullable=False)
    email_marketing = Column(Boolean, default=False, nullable=False)
    email_job_alerts = Column(Boolean, default=True, nullable=False)
    email_application_updates = Column(Boolean, default=True, nullable=False)
    email_interview_reminders = Column(Boolean, default=True, nullable=False)
    
    # SMS preferences
    sms_notifications = Column(Boolean, default=False, nullable=False)
    sms_urgent_only = Column(Boolean, default=True, nullable=False)
    sms_interview_reminders = Column(Boolean, default=False, nullable=False)
    
    # Push notification preferences
    push_notifications = Column(Boolean, default=True, nullable=False)
    push_job_matches = Column(Boolean, default=True, nullable=False)
    push_messages = Column(Boolean, default=True, nullable=False)
    
    # Phone call preferences
    allow_phone_calls = Column(Boolean, default=True, nullable=False)
    preferred_call_times = Column(JSON, nullable=True, default=[])  # Time ranges
    do_not_call_times = Column(JSON, nullable=True, default=[])  # Blocked time ranges
    
    # Frequency preferences
    digest_frequency = Column(String(20), default='daily', nullable=False)  # immediate, daily, weekly
    max_emails_per_day = Column(Integer, default=5, nullable=False)
    
    # Language and timezone
    preferred_language = Column(String(10), default='en', nullable=False)
    timezone = Column(String(50), default='UTC', nullable=False)
    
    # Contact information
    preferred_email = Column(String(255), nullable=True)
    preferred_phone = Column(String(20), nullable=True)
    
    # Relationships
    user = relationship('User', back_populates='communication_preferences', foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<CommunicationPreference(id={self.id}, user_id={self.user_id})>"
    
    def can_send_email(self, email_type: str = 'general'):
        """Check if user allows email for specific type"""
        if not self.email_notifications:
            return False
        
        type_mapping = {
            'marketing': self.email_marketing,
            'job_alerts': self.email_job_alerts,
            'application_updates': self.email_application_updates,
            'interview_reminders': self.email_interview_reminders
        }
        
        return type_mapping.get(email_type, True)
    
    def can_send_sms(self, is_urgent: bool = False):
        """Check if user allows SMS"""
        if not self.sms_notifications:
            return False
        
        if self.sms_urgent_only and not is_urgent:
            return False
        
        return True

class BulkCommunication(BaseModel, AuditMixin):
    """Bulk communication campaigns"""
    __tablename__ = 'bulk_communications'
    
    # Campaign details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(String(50), nullable=False)  # email, sms, notification
    
    # Content
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    template_id = Column(Integer, ForeignKey('email_templates.id'), nullable=True)
    
    # Targeting
    target_audience = Column(String(100), nullable=False)  # all_candidates, active_applicants, etc.
    filters = Column(JSON, nullable=True, default={})  # Audience filters
    
    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    send_immediately = Column(Boolean, default=False, nullable=False)
    
    # Status and tracking
    status = Column(String(50), default='draft', nullable=False)  # draft, scheduled, sending, sent, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Statistics
    total_recipients = Column(Integer, default=0, nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    delivered_count = Column(Integer, default=0, nullable=False)
    opened_count = Column(Integer, default=0, nullable=False)
    clicked_count = Column(Integer, default=0, nullable=False)
    bounced_count = Column(Integer, default=0, nullable=False)
    unsubscribed_count = Column(Integer, default=0, nullable=False)
    
    # Error tracking
    error_count = Column(Integer, default=0, nullable=False)
    error_details = Column(JSON, nullable=True, default=[])
    
    # Relationships
    template = relationship('EmailTemplate')
    
    def __repr__(self):
        return f"<BulkCommunication(id={self.id}, name='{self.name}', type='{self.campaign_type}', status='{self.status}')>"
    
    @property
    def delivery_rate(self):
        """Calculate delivery rate percentage"""
        if self.sent_count > 0:
            return (self.delivered_count / self.sent_count) * 100
        return 0
    
    @property
    def open_rate(self):
        """Calculate open rate percentage"""
        if self.delivered_count > 0:
            return (self.opened_count / self.delivered_count) * 100
        return 0
    
    @property
    def click_rate(self):
        """Calculate click rate percentage"""
        if self.opened_count > 0:
            return (self.clicked_count / self.opened_count) * 100
        return 0
    
    def start_campaign(self):
        """Start the campaign"""
        if self.status != 'scheduled':
            raise ValueError(f"Cannot start campaign in status: {self.status}")
        
        self.status = 'sending'
        self.started_at = datetime.utcnow()
    
    def complete_campaign(self):
        """Mark campaign as completed"""
        if self.status != 'sending':
            raise ValueError(f"Cannot complete campaign in status: {self.status}")
        
        self.status = 'sent'
        self.completed_at = datetime.utcnow()