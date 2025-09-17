"""Pydantic schemas for recruiter functionality."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, date, time
from enum import Enum
from decimal import Decimal

class FeedbackType(str, Enum):
    """Feedback type classifications."""
    INTERVIEW = "interview"
    APPLICATION_REVIEW = "application_review"
    SKILL_ASSESSMENT = "skill_assessment"
    CULTURAL_FIT = "cultural_fit"
    TECHNICAL_EVALUATION = "technical_evaluation"
    REFERENCE_CHECK = "reference_check"
    FINAL_DECISION = "final_decision"
    GENERAL = "general"

class InterviewType(str, Enum):
    """Interview type classifications."""
    PHONE_SCREENING = "phone_screening"
    VIDEO_INTERVIEW = "video_interview"
    IN_PERSON = "in_person"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    PANEL = "panel"
    GROUP = "group"
    FINAL = "final"
    INFORMAL = "informal"

class InterviewStatus(str, Enum):
    """Interview status types."""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    NO_SHOW = "no_show"

class CommunicationType(str, Enum):
    """Communication type classifications."""
    EMAIL = "email"
    PHONE = "phone"
    SMS = "sms"
    VIDEO_CALL = "video_call"
    IN_PERSON = "in_person"
    CHAT = "chat"
    SYSTEM_MESSAGE = "system_message"

class DocumentType(str, Enum):
    """Document type classifications."""
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    PORTFOLIO = "portfolio"
    CERTIFICATE = "certificate"
    REFERENCE_LETTER = "reference_letter"
    TRANSCRIPT = "transcript"
    WORK_SAMPLE = "work_sample"
    CONTRACT = "contract"
    OFFER_LETTER = "offer_letter"
    BACKGROUND_CHECK = "background_check"
    OTHER = "other"

# Feedback Management Schemas
class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""
    candidate_id: str = Field(..., description="Candidate user ID")
    job_id: UUID = Field(..., description="Job ID")
    application_id: Optional[UUID] = None
    interview_id: Optional[UUID] = None
    feedback_type: FeedbackType
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []
    skills_evaluated: List[Dict[str, Any]] = []  # [{"skill": "Python", "rating": 4}]
    is_positive: Optional[bool] = None
    is_confidential: bool = False
    tags: List[str] = []
    
class FeedbackUpdate(BaseModel):
    """Schema for updating feedback."""
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    skills_evaluated: Optional[List[Dict[str, Any]]] = None
    is_positive: Optional[bool] = None
    is_confidential: Optional[bool] = None
    tags: Optional[List[str]] = None
    
class FeedbackResponse(BaseModel):
    """Feedback response schema."""
    id: UUID
    candidate_id: str
    candidate_name: str
    job_id: UUID
    job_title: str
    application_id: Optional[UUID] = None
    interview_id: Optional[UUID] = None
    feedback_type: FeedbackType
    rating: Optional[int] = None
    title: str
    content: str
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []
    skills_evaluated: List[Dict[str, Any]] = []
    is_positive: Optional[bool] = None
    is_confidential: bool = False
    tags: List[str] = []
    recruiter_id: str  # Clerk user ID
    recruiter_name: str
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Interview Management Schemas
class InterviewCreate(BaseModel):
    """Schema for creating interviews."""
    candidate_id: str = Field(..., description="Candidate user ID")
    job_id: UUID = Field(..., description="Job ID")
    application_id: Optional[UUID] = None
    interview_type: InterviewType
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    scheduled_at: datetime
    duration_minutes: int = Field(60, ge=15, le=480)
    location: Optional[str] = Field(None, max_length=500)
    meeting_link: Optional[str] = Field(None, max_length=500)
    meeting_id: Optional[str] = Field(None, max_length=100)
    meeting_password: Optional[str] = Field(None, max_length=100)
    interviewer_ids: List[str] = Field(..., min_items=1)  # Clerk user IDs
    preparation_notes: Optional[str] = Field(None, max_length=2000)
    questions: List[str] = []
    required_documents: List[str] = []
    send_calendar_invite: bool = True
    send_reminder: bool = True
    reminder_minutes_before: int = Field(60, ge=5, le=1440)
    
class InterviewUpdate(BaseModel):
    """Schema for updating interviews."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    location: Optional[str] = Field(None, max_length=500)
    meeting_link: Optional[str] = Field(None, max_length=500)
    meeting_id: Optional[str] = Field(None, max_length=100)
    meeting_password: Optional[str] = Field(None, max_length=100)
    interviewer_ids: Optional[List[str]] = None
    preparation_notes: Optional[str] = Field(None, max_length=2000)
    questions: Optional[List[str]] = None
    required_documents: Optional[List[str]] = None
    status: Optional[InterviewStatus] = None
    
class InterviewResponse(BaseModel):
    """Interview response schema."""
    id: UUID
    candidate_id: str
    candidate_name: str
    candidate_email: str
    job_id: UUID
    job_title: str
    application_id: Optional[UUID] = None
    interview_type: InterviewType
    title: str
    description: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: int
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    meeting_id: Optional[str] = None
    meeting_password: Optional[str] = None
    interviewers: List[Dict[str, str]] = []  # [{"id": "123", "name": "John"}]
    preparation_notes: Optional[str] = None
    questions: List[str] = []
    required_documents: List[str] = []
    status: InterviewStatus
    feedback_id: Optional[UUID] = None
    created_by: str  # Recruiter user ID
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class InterviewScheduleRequest(BaseModel):
    """Interview schedule request schema."""
    candidate_id: str = Field(..., description="Candidate user ID")
    job_id: UUID = Field(..., description="Job ID")
    application_id: Optional[UUID] = None
    interview_type: InterviewType
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    scheduled_at: datetime
    duration_minutes: int = Field(60, ge=15, le=480)
    location: Optional[str] = Field(None, max_length=500)
    meeting_link: Optional[str] = Field(None, max_length=500)
    meeting_id: Optional[str] = Field(None, max_length=100)
    meeting_password: Optional[str] = Field(None, max_length=100)
    interviewer_ids: List[str] = Field(..., min_items=1)
    preparation_notes: Optional[str] = Field(None, max_length=2000)
    questions: List[str] = []
    required_documents: List[str] = []
    send_calendar_invite: bool = True
    send_reminder: bool = True
    reminder_minutes_before: int = Field(60, ge=5, le=1440)

class InterviewRescheduleRequest(BaseModel):
    """Interview reschedule request schema."""
    new_scheduled_at: datetime
    reason: str = Field(..., min_length=1, max_length=500)
    notify_candidate: bool = True
    notify_interviewers: bool = True
    
# Communication Management Schemas
class CommunicationCreate(BaseModel):
    """Schema for creating communications."""
    recipient_id: str = Field(..., description="Recipient user ID")
    recipient_type: str = Field(..., pattern=r'^(candidate|recruiter|manager|admin)$')
    communication_type: CommunicationType
    subject: Optional[str] = Field(None, max_length=200)
    content: str = Field(..., min_length=1, max_length=10000)
    job_id: Optional[UUID] = None
    application_id: Optional[UUID] = None
    interview_id: Optional[UUID] = None
    priority: str = Field("medium", pattern=r'^(low|medium|high|urgent)$')
    scheduled_for: Optional[datetime] = None
    template_id: Optional[UUID] = None
    template_variables: Dict[str, str] = {}
    attachments: List[str] = []  # File IDs
    tags: List[str] = []
    
class CommunicationResponse(BaseModel):
    """Communication response schema."""
    id: UUID
    sender_id: str  # Recruiter user ID
    sender_name: str
    recipient_id: str
    recipient_name: str
    recipient_type: str
    communication_type: CommunicationType
    subject: Optional[str] = None
    content: str
    job_id: Optional[UUID] = None
    job_title: Optional[str] = None
    application_id: Optional[UUID] = None
    interview_id: Optional[UUID] = None
    priority: str
    status: str = "sent"  # sent, delivered, read, failed
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    template_id: Optional[UUID] = None
    attachments: List[Dict[str, str]] = []  # File metadata
    tags: List[str] = []
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Document Management Schemas
class DocumentCreate(BaseModel):
    """Schema for creating documents."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    document_type: DocumentType
    candidate_id: Optional[str] = None
    job_id: Optional[UUID] = None
    application_id: Optional[UUID] = None
    file_path: str = Field(..., min_length=1, max_length=500)
    file_size: int = Field(..., ge=0)
    mime_type: str = Field(..., min_length=1, max_length=100)
    is_confidential: bool = False
    expiry_date: Optional[date] = None
    tags: List[str] = []
    
class DocumentResponse(BaseModel):
    """Document response schema."""
    id: UUID
    title: str
    description: Optional[str] = None
    document_type: DocumentType
    candidate_id: Optional[str] = None
    candidate_name: Optional[str] = None
    job_id: Optional[UUID] = None
    job_title: Optional[str] = None
    application_id: Optional[UUID] = None
    file_path: str
    file_size: int
    mime_type: str
    download_url: Optional[str] = None
    is_confidential: bool = False
    expiry_date: Optional[date] = None
    tags: List[str] = []
    uploaded_by: str  # Recruiter user ID
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Candidate Notes Schemas
class CandidateNoteCreate(BaseModel):
    """Schema for creating candidate notes."""
    candidate_id: str = Field(..., description="Candidate user ID")
    job_id: Optional[UUID] = None
    application_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    note_type: str = Field("general", pattern=r'^(general|interview|screening|follow_up|concern|positive)$')
    is_private: bool = False
    is_important: bool = False
    tags: List[str] = []
    
class CandidateNoteUpdate(BaseModel):
    """Schema for updating candidate notes."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    note_type: Optional[str] = Field(None, pattern=r'^(general|interview|screening|follow_up|concern|positive)$')
    is_private: Optional[bool] = None
    is_important: Optional[bool] = None
    tags: Optional[List[str]] = None
    
class CandidateNoteResponse(BaseModel):
    """Candidate note response schema."""
    id: UUID
    candidate_id: str
    candidate_name: str
    job_id: Optional[UUID] = None
    job_title: Optional[str] = None
    application_id: Optional[UUID] = None
    title: str
    content: str
    note_type: str
    is_private: bool = False
    is_important: bool = False
    tags: List[str] = []
    author_id: str  # Recruiter user ID
    author_name: str
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Analytics Schemas
class RecruiterAnalyticsRequest(BaseModel):
    """Recruiter analytics request schema."""
    start_date: date
    end_date: date
    include_team_comparison: bool = False
    include_trends: bool = True
    metrics: List[str] = []  # Specific metrics to include
    
class RecruiterAnalyticsResponse(BaseModel):
    """Recruiter analytics response schema."""
    recruiter_id: str
    period_start: date
    period_end: date
    summary_stats: Dict[str, Any] = {}
    performance_metrics: Dict[str, float] = {}
    activity_breakdown: Dict[str, int] = {}
    success_rates: Dict[str, float] = {}
    time_analysis: Dict[str, Any] = {}
    candidate_feedback_summary: Dict[str, Any] = {}
    job_performance: List[Dict[str, Any]] = []
    trends: Dict[str, List[Dict[str, Any]]] = {}
    team_comparison: Optional[Dict[str, Any]] = None
    insights: List[str] = []
    recommendations: List[str] = []
    generated_at: datetime
    
# Dashboard Schemas
class MessageCreate(BaseModel):
    """Message creation schema."""
    subject: Optional[str] = Field(None, max_length=200)
    content: str = Field(..., min_length=1, max_length=10000)
    priority: str = Field("medium", pattern=r'^(low|medium|high|urgent)$')
    scheduled_for: Optional[datetime] = None
    template_id: Optional[UUID] = None
    template_variables: Dict[str, str] = {}
    attachments: List[str] = []  # File IDs
    tags: List[str] = []

class RecruiterMetrics(BaseModel):
    """Recruiter metrics schema."""
    recruiter_id: str
    period_start: date
    period_end: date
    jobs_posted: int = 0
    applications_received: int = 0
    interviews_conducted: int = 0
    candidates_hired: int = 0
    time_to_hire_avg: Optional[float] = None
    response_rate: Optional[float] = None
    conversion_rate: Optional[float] = None
    satisfaction_score: Optional[float] = None
    active_jobs: int = 0
    closed_jobs: int = 0

class DocumentUploadResponse(BaseModel):
    """Document upload response schema."""
    id: UUID
    title: str
    document_type: DocumentType
    file_size: int
    mime_type: str
    upload_url: str
    download_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class DocumentMetadata(BaseModel):
    """Document metadata schema."""
    id: UUID
    title: str
    document_type: DocumentType
    file_size: int
    mime_type: str
    is_confidential: bool = False
    expiry_date: Optional[date] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class JobPostingCreate(BaseModel):
    """Job posting creation schema."""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    department: str = Field(..., min_length=1, max_length=100)
    location: str = Field(..., min_length=1, max_length=200)
    employment_type: str = Field(..., pattern=r'^(full_time|part_time|contract|temporary|internship)$')
    experience_level: str = Field(..., pattern=r'^(entry|junior|mid|senior|lead|executive)$')
    salary_min: Optional[Decimal] = Field(None, ge=0)
    salary_max: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    benefits: List[str] = []
    remote_allowed: bool = False
    application_deadline: Optional[date] = None
    is_urgent: bool = False
    tags: List[str] = []

class JobPostingUpdate(BaseModel):
    """Job posting update schema."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    employment_type: Optional[str] = Field(None, pattern=r'^(full_time|part_time|contract|temporary|internship)$')
    experience_level: Optional[str] = Field(None, pattern=r'^(entry|junior|mid|senior|lead|executive)$')
    salary_min: Optional[Decimal] = Field(None, ge=0)
    salary_max: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    remote_allowed: Optional[bool] = None
    application_deadline: Optional[date] = None
    is_urgent: Optional[bool] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern=r'^(draft|active|paused|closed|archived)$')

class JobPostingResponse(BaseModel):
    """Job posting response schema."""
    id: UUID
    title: str
    description: str
    department: str
    location: str
    employment_type: str
    experience_level: str
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    currency: str
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    benefits: List[str] = []
    remote_allowed: bool = False
    application_deadline: Optional[date] = None
    is_urgent: bool = False
    tags: List[str] = []
    status: str = "draft"
    applications_count: int = 0
    views_count: int = 0
    recruiter_id: str
    recruiter_name: str
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RecruiterDashboard(BaseModel):
    """Recruiter dashboard data schema."""
    recruiter_id: str
    active_jobs: int = 0
    total_applications: int = 0
    pending_reviews: int = 0
    scheduled_interviews: int = 0
    interviews_today: int = 0
    interviews_this_week: int = 0
    recent_activities: List[Dict[str, Any]] = []
    upcoming_deadlines: List[Dict[str, Any]] = []
    performance_summary: Dict[str, Any] = {}
    quick_stats: Dict[str, int] = {}
    notifications_count: int = 0
    tasks_pending: int = 0
    goals_progress: List[Dict[str, Any]] = []
    recent_feedback: List[Dict[str, Any]] = []
    last_updated: datetime