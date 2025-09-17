from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy import JSON
from datetime import datetime, timedelta
from .base import BaseModel, AuditMixin, MetadataMixin
from ..schemas.base import InterviewStatus, InterviewType

class Interview(BaseModel, AuditMixin, MetadataMixin):
    """Interview model"""
    __tablename__ = 'interviews'
    
    # Foreign keys
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    interviewer_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Interview details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    interview_type = Column(SQLEnum(InterviewType), nullable=False)
    interview_round = Column(Integer, default=1, nullable=False)
    
    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(Integer, default=60, nullable=False)
    timezone = Column(String(50), default='UTC', nullable=False)
    
    # Location/Platform
    location = Column(String(500), nullable=True)  # Physical address or meeting room
    meeting_url = Column(String(500), nullable=True)  # Video call link
    meeting_id = Column(String(100), nullable=True)  # Meeting ID for platforms
    meeting_password = Column(String(100), nullable=True)
    dial_in_number = Column(String(50), nullable=True)
    
    # Status and tracking
    status = Column(SQLEnum(InterviewStatus), default=InterviewStatus.SCHEDULED, nullable=False, index=True)
    previous_status = Column(SQLEnum(InterviewStatus), nullable=True)
    status_changed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Actual timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)
    
    # Preparation and requirements
    preparation_notes = Column(Text, nullable=True)
    required_materials = Column(JSON, nullable=True)  # Store as JSON array
    technical_requirements = Column(JSON, nullable=True, default={})
    
    # Interview structure
    agenda = Column(JSON, nullable=True, default=[])  # List of agenda items
    questions = Column(JSON, nullable=True, default=[])  # Prepared questions
    evaluation_criteria = Column(JSON, nullable=True, default=[])  # Scoring criteria
    
    # Reminders and notifications
    reminder_sent_candidate = Column(Boolean, default=False, nullable=False)
    reminder_sent_interviewer = Column(Boolean, default=False, nullable=False)
    confirmation_received_candidate = Column(Boolean, default=False, nullable=False)
    confirmation_received_interviewer = Column(Boolean, default=False, nullable=False)
    
    # Rescheduling
    reschedule_count = Column(Integer, default=0, nullable=False)
    last_rescheduled_at = Column(DateTime(timezone=True), nullable=True)
    reschedule_reason = Column(String(500), nullable=True)
    
    # Cancellation
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    cancellation_reason = Column(String(500), nullable=True)
    
    # External integrations
    calendar_event_id = Column(String(255), nullable=True)  # Google Calendar, Outlook, etc.
    video_call_id = Column(String(255), nullable=True)  # Zoom, Teams, etc.
    external_interview_id = Column(String(100), nullable=True)
    
    # Relationships
    application = relationship('Application', back_populates='interviews')
    job = relationship('Job', back_populates='interviews')
    candidate = relationship('User', foreign_keys=[candidate_id], back_populates='interviews_as_candidate')
    interviewer = relationship('User', foreign_keys=[interviewer_id], back_populates='interviews_as_interviewer')
    cancelled_by_user = relationship('User', foreign_keys=[cancelled_by])
    
    # Related entities
    feedback = relationship('InterviewFeedback', back_populates='interview', cascade='all, delete-orphan')
    notes = relationship('InterviewNote', back_populates='interview', cascade='all, delete-orphan')
    recordings = relationship('InterviewRecording', back_populates='interview', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Interview(id={self.id}, type='{self.interview_type}', scheduled_at='{self.scheduled_at}', status='{self.status}')>"
    
    @property
    def end_time(self):
        """Calculate interview end time"""
        return self.scheduled_at + timedelta(minutes=self.duration_minutes)
    
    @property
    def is_upcoming(self):
        """Check if interview is upcoming"""
        return self.scheduled_at > datetime.utcnow() and self.status == InterviewStatus.SCHEDULED
    
    @property
    def is_overdue(self):
        """Check if interview is overdue (past scheduled time but not completed)"""
        return (self.scheduled_at < datetime.utcnow() and 
                self.status in [InterviewStatus.SCHEDULED, InterviewStatus.IN_PROGRESS])
    
    @property
    def can_be_rescheduled(self):
        """Check if interview can be rescheduled"""
        return self.status in [InterviewStatus.SCHEDULED, InterviewStatus.CONFIRMED]
    
    @property
    def time_until_interview(self):
        """Get time until interview in minutes"""
        if self.scheduled_at > datetime.utcnow():
            delta = self.scheduled_at - datetime.utcnow()
            return int(delta.total_seconds() / 60)
        return 0
    
    def reschedule(self, new_datetime: datetime, reason: str = None):
        """Reschedule the interview"""
        if not self.can_be_rescheduled:
            raise ValueError(f"Cannot reschedule interview in status: {self.status}")
        
        self.scheduled_at = new_datetime
        self.reschedule_count += 1
        self.last_rescheduled_at = datetime.utcnow()
        self.reschedule_reason = reason
        
        # Reset confirmation status
        self.confirmation_received_candidate = False
        self.confirmation_received_interviewer = False
        self.reminder_sent_candidate = False
        self.reminder_sent_interviewer = False
    
    def start_interview(self):
        """Mark interview as started"""
        if self.status != InterviewStatus.SCHEDULED:
            raise ValueError(f"Cannot start interview in status: {self.status}")
        
        self.status = InterviewStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.status_changed_at = datetime.utcnow()
    
    def complete_interview(self):
        """Mark interview as completed"""
        if self.status != InterviewStatus.IN_PROGRESS:
            raise ValueError(f"Cannot complete interview in status: {self.status}")
        
        self.status = InterviewStatus.COMPLETED
        self.ended_at = datetime.utcnow()
        self.status_changed_at = datetime.utcnow()
        
        if self.started_at:
            delta = self.ended_at - self.started_at
            self.actual_duration_minutes = int(delta.total_seconds() / 60)
    
    def cancel_interview(self, cancelled_by: int, reason: str = None):
        """Cancel the interview"""
        if self.status in [InterviewStatus.COMPLETED, InterviewStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel interview in status: {self.status}")
        
        self.status = InterviewStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        self.status_changed_at = datetime.utcnow()

class InterviewFeedback(BaseModel, AuditMixin):
    """Interview feedback from interviewers"""
    __tablename__ = 'interview_feedback'
    
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=False, index=True)
    
    # Overall assessment
    overall_rating = Column(Integer, nullable=True)  # 1-10 scale
    recommendation = Column(String(50), nullable=True)  # strong_hire, hire, no_hire, strong_no_hire
    
    # Detailed ratings
    technical_skills = Column(Integer, nullable=True)  # 1-10
    communication_skills = Column(Integer, nullable=True)  # 1-10
    problem_solving = Column(Integer, nullable=True)  # 1-10
    cultural_fit = Column(Integer, nullable=True)  # 1-10
    leadership_potential = Column(Integer, nullable=True)  # 1-10
    
    # Structured feedback
    strengths = Column(JSON, nullable=True)  # Store as JSON array
    weaknesses = Column(JSON, nullable=True)  # Store as JSON array
    concerns = Column(JSON, nullable=True)  # Store as JSON array
    
    # Detailed comments
    technical_comments = Column(Text, nullable=True)
    behavioral_comments = Column(Text, nullable=True)
    general_comments = Column(Text, nullable=True)
    
    # Questions and responses
    questions_asked = Column(JSON, nullable=True, default=[])  # Questions with responses
    
    # Interview quality
    interview_quality = Column(Integer, nullable=True)  # How well did the interview go
    candidate_engagement = Column(Integer, nullable=True)
    
    # Follow-up
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_notes = Column(Text, nullable=True)
    
    # Confidentiality
    is_confidential = Column(Boolean, default=True, nullable=False)
    shared_with_candidate = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    interview = relationship('Interview', back_populates='feedback')
    reviewer = relationship('User', foreign_keys='InterviewFeedback.created_by', primaryjoin='User.id==InterviewFeedback.created_by')
    
    def __repr__(self):
        return f"<InterviewFeedback(id={self.id}, interview_id={self.interview_id}, rating={self.overall_rating})>"
    
    @property
    def average_skill_rating(self):
        """Calculate average of all skill ratings"""
        ratings = []
        for rating in [self.technical_skills, self.communication_skills, 
                      self.problem_solving, self.cultural_fit, self.leadership_potential]:
            if rating is not None:
                ratings.append(rating)
        
        return sum(ratings) / len(ratings) if ratings else None

class InterviewNote(BaseModel, AuditMixin):
    """Notes taken during interviews"""
    __tablename__ = 'interview_notes'
    
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=False, index=True)
    
    # Note details
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    note_type = Column(String(50), default='general', nullable=False)  # general, technical, behavioral
    
    # Timing
    timestamp_in_interview = Column(Integer, nullable=True)  # Minutes from start
    
    # Categorization
    tags = Column(JSON, nullable=True)  # Store as JSON array
    is_important = Column(Boolean, default=False, nullable=False)
    
    # Visibility
    is_private = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    interview = relationship('Interview', back_populates='notes')
    author = relationship('User', foreign_keys='InterviewNote.created_by', primaryjoin='User.id==InterviewNote.created_by')
    
    def __repr__(self):
        return f"<InterviewNote(id={self.id}, interview_id={self.interview_id}, type='{self.note_type}')>"

class InterviewRecording(BaseModel, AuditMixin):
    """Interview recordings and transcripts"""
    __tablename__ = 'interview_recordings'
    
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=False, index=True)
    
    # Recording details
    recording_type = Column(String(50), nullable=False)  # video, audio, screen_share
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Processing status
    processing_status = Column(String(50), default='pending', nullable=False)  # pending, processing, completed, failed
    transcript = Column(Text, nullable=True)
    transcript_confidence = Column(Numeric(5, 2), nullable=True)  # AI confidence score
    
    # Access control
    is_encrypted = Column(Boolean, default=True, nullable=False)
    access_key = Column(String(255), nullable=True)
    retention_until = Column(DateTime(timezone=True), nullable=True)
    
    # Consent and compliance
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # External storage
    external_url = Column(String(500), nullable=True)
    external_id = Column(String(255), nullable=True)
    
    # Relationships
    interview = relationship('Interview', back_populates='recordings')
    
    def __repr__(self):
        return f"<InterviewRecording(id={self.id}, interview_id={self.interview_id}, type='{self.recording_type}')>"
    
    @property
    def duration_display(self):
        """Get formatted duration"""
        if self.duration_seconds:
            hours = self.duration_seconds // 3600
            minutes = (self.duration_seconds % 3600) // 60
            seconds = self.duration_seconds % 60
            
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            return f"{minutes:02d}:{seconds:02d}"
        return "Unknown"

class InterviewSlot(BaseModel, AuditMixin):
    """Available interview time slots"""
    __tablename__ = 'interview_slots'
    
    interviewer_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Slot details
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    timezone = Column(String(50), default='UTC', nullable=False)
    
    # Availability
    is_available = Column(Boolean, default=True, nullable=False)
    is_recurring = Column(Boolean, default=False, nullable=False)
    recurrence_pattern = Column(JSON, nullable=True)  # For recurring slots
    
    # Slot configuration
    interview_types = Column(JSON, nullable=True)  # Which types of interviews - Store as JSON array
    max_bookings = Column(Integer, default=1, nullable=False)
    current_bookings = Column(Integer, default=0, nullable=False)
    
    # Location/Platform
    location = Column(String(500), nullable=True)
    meeting_url = Column(String(500), nullable=True)
    
    # Relationships
    interviewer = relationship('User', foreign_keys='InterviewSlot.interviewer_id', primaryjoin='User.id==InterviewSlot.interviewer_id')
    
    def __repr__(self):
        return f"<InterviewSlot(id={self.id}, interviewer_id={self.interviewer_id}, start='{self.start_time}')>"
    
    @property
    def is_fully_booked(self):
        """Check if slot is fully booked"""
        return self.current_bookings >= self.max_bookings
    
    @property
    def duration_minutes(self):
        """Get slot duration in minutes"""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)

class InterviewTemplate(BaseModel, AuditMixin):
    """Interview templates for different types/roles"""
    __tablename__ = 'interview_templates'
    
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    interview_type = Column(SQLEnum(InterviewType), nullable=False)
    
    # Template configuration
    default_duration_minutes = Column(Integer, default=60, nullable=False)
    preparation_time_minutes = Column(Integer, default=15, nullable=False)
    
    # Template content
    agenda = Column(JSON, nullable=True, default=[])
    questions = Column(JSON, nullable=True, default=[])
    evaluation_criteria = Column(JSON, nullable=True, default=[])
    required_materials = Column(JSON, nullable=True)  # Store as JSON array
    
    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Categorization
    job_roles = Column(JSON, nullable=True)  # Which roles this template is for - Store as JSON array
    departments = Column(JSON, nullable=True)  # Store as JSON array
    
    def __repr__(self):
        return f"<InterviewTemplate(id={self.id}, name='{self.name}', type='{self.interview_type}')>"
    
    def create_interview_from_template(self, **overrides):
        """Create a new interview from this template"""
        interview_data = {
            'title': self.name,
            'interview_type': self.interview_type,
            'duration_minutes': self.default_duration_minutes,
            'agenda': self.agenda,
            'questions': self.questions,
            'evaluation_criteria': self.evaluation_criteria,
            'required_materials': self.required_materials
        }
        interview_data.update(overrides)
        return Interview(**interview_data)