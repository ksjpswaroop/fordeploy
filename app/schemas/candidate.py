from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from .base import TimestampMixin, SkillLevel, ExperienceLevel
from .job import JobResponse
from .application import ApplicationResponse
from .interview import InterviewResponse

# Candidate profile schemas
class CandidateProfileBase(BaseModel):
    """Base candidate profile schema"""
    bio: Optional[str] = Field(None, max_length=1000)
    location: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    current_title: Optional[str] = Field(None, max_length=200)
    current_company: Optional[str] = Field(None, max_length=200)
    experience_level: Optional[ExperienceLevel] = None
    expected_salary: Optional[Decimal] = None
    currency: str = Field(default="USD", max_length=3)
    available_from: Optional[date] = None
    willing_to_relocate: bool = False
    remote_work_preference: bool = False

class CandidateProfileCreate(CandidateProfileBase):
    """Candidate profile creation schema"""
    pass

class CandidateProfileUpdate(BaseModel):
    """Candidate profile update schema"""
    bio: Optional[str] = Field(None, max_length=1000)
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    current_title: Optional[str] = Field(None, max_length=200)
    current_company: Optional[str] = Field(None, max_length=200)
    experience_level: Optional[ExperienceLevel] = None
    expected_salary: Optional[Decimal] = None
    currency: Optional[str] = Field(None, max_length=3)
    available_from: Optional[date] = None
    willing_to_relocate: Optional[bool] = None
    remote_work_preference: Optional[bool] = None

class CandidateProfileResponse(CandidateProfileBase, TimestampMixin):
    """Candidate profile response schema"""
    id: int
    user_id: int
    avatar_url: Optional[str] = None
    resume_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Skills schemas
class SkillBase(BaseModel):
    """Base skill schema"""
    name: str = Field(..., min_length=1, max_length=100)
    level: SkillLevel
    years_of_experience: Optional[int] = Field(None, ge=0, le=50)
    is_primary: bool = False

class SkillCreate(SkillBase):
    """Skill creation schema"""
    pass

class SkillUpdate(BaseModel):
    """Skill update schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    level: Optional[SkillLevel] = None
    years_of_experience: Optional[int] = Field(None, ge=0, le=50)
    is_primary: Optional[bool] = None

class SkillResponse(SkillBase, TimestampMixin):
    """Skill response schema"""
    id: int
    candidate_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Experience schemas
class ExperienceBase(BaseModel):
    """Base experience schema"""
    company: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=200)
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False
    achievements: Optional[List[str]] = []
    technologies: Optional[List[str]] = []

class ExperienceCreate(ExperienceBase):
    """Experience creation schema"""
    pass

class ExperienceUpdate(BaseModel):
    """Experience update schema"""
    company: Optional[str] = Field(None, min_length=1, max_length=200)
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    achievements: Optional[List[str]] = None
    technologies: Optional[List[str]] = None

class ExperienceResponse(ExperienceBase, TimestampMixin):
    """Experience response schema"""
    id: int
    candidate_id: int
    duration_months: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

# Education schemas
class EducationBase(BaseModel):
    """Base education schema"""
    institution: str = Field(..., min_length=1, max_length=200)
    degree: str = Field(..., min_length=1, max_length=200)
    field_of_study: str = Field(..., min_length=1, max_length=200)
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False
    gpa: Optional[float] = Field(None, ge=0, le=4.0)
    achievements: Optional[List[str]] = []
    relevant_coursework: Optional[List[str]] = []

class EducationCreate(EducationBase):
    """Education creation schema"""
    pass

class EducationUpdate(BaseModel):
    """Education update schema"""
    institution: Optional[str] = Field(None, min_length=1, max_length=200)
    degree: Optional[str] = Field(None, min_length=1, max_length=200)
    field_of_study: Optional[str] = Field(None, min_length=1, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    gpa: Optional[float] = Field(None, ge=0, le=4.0)
    achievements: Optional[List[str]] = None
    relevant_coursework: Optional[List[str]] = None

class EducationResponse(EducationBase, TimestampMixin):
    """Education response schema"""
    id: int
    candidate_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Preferences schemas
class JobPreferencesBase(BaseModel):
    """Base job preferences schema"""
    preferred_locations: List[str] = []
    preferred_departments: List[str] = []
    preferred_employment_types: List[str] = []
    min_salary: Optional[Decimal] = None
    max_salary: Optional[Decimal] = None
    currency: str = Field(default="USD", max_length=3)
    remote_work_only: bool = False
    willing_to_relocate: bool = False
    preferred_company_sizes: List[str] = []  # startup, small, medium, large, enterprise
    preferred_industries: List[str] = []
    work_authorization_required: bool = False

class JobPreferencesUpdate(JobPreferencesBase):
    """Job preferences update schema"""
    pass

class JobPreferencesResponse(JobPreferencesBase, TimestampMixin):
    """Job preferences response schema"""
    id: int
    candidate_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Settings schemas
class CandidateSettingsBase(BaseModel):
    """Base candidate settings schema"""
    profile_visibility: str = Field(default="public", pattern="^(public|private|recruiters_only)$")
    email_notifications: bool = True
    sms_notifications: bool = False
    job_alerts: bool = True
    application_updates: bool = True
    interview_reminders: bool = True
    marketing_emails: bool = False
    timezone: str = Field(default="UTC", max_length=50)
    language: str = Field(default="en", max_length=5)

class CandidateSettingsUpdate(BaseModel):
    """Candidate settings update schema"""
    profile_visibility: Optional[str] = Field(None, pattern="^(public|private|recruiters_only)$")
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    job_alerts: Optional[bool] = None
    application_updates: Optional[bool] = None
    interview_reminders: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=5)

class CandidateSettingsResponse(CandidateSettingsBase, TimestampMixin):
    """Candidate settings response schema"""
    id: int
    candidate_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Analytics schemas
class CandidateAnalyticsResponse(BaseModel):
    """Candidate analytics response"""
    total_applications: int = 0
    applications_this_month: int = 0
    interview_invitations: int = 0
    interviews_completed: int = 0
    offers_received: int = 0
    profile_views: int = 0
    profile_views_this_month: int = 0
    response_rate: float = 0.0
    interview_success_rate: float = 0.0
    application_status_breakdown: Dict[str, int] = {}
    monthly_application_trend: List[Dict[str, Any]] = []
    top_skills_in_demand: List[Dict[str, Any]] = []

# Job recommendations schema
class CandidateJobRecommendations(BaseModel):
    """Job recommendations for candidate"""
    recommended_jobs: List[JobResponse] = []
    match_reasons: List[str] = []
    total_recommendations: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Application history schema
class CandidateApplicationHistory(BaseModel):
    """Candidate application history with analytics"""
    applications: List[ApplicationResponse] = []
    total_applications: int = 0
    applications_by_status: Dict[str, int] = {}
    success_rate: float = 0.0
    avg_response_time_days: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)

# Interview history schema
class CandidateInterviewHistory(BaseModel):
    """Candidate interview history schema"""
    interviews: List[InterviewResponse] = []
    total_interviews: int = 0
    completed_interviews: int = 0
    avg_rating: float = 0.0
    upcoming_interviews: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Additional schemas for API endpoints
class CandidateAuthResponse(BaseModel):
    """Candidate authentication response schema"""
    id: UUID
    user_id: str
    email: str
    first_name: str
    last_name: str
    profile_completed: bool = False
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class JobApplicationCreate(BaseModel):
    """Job application creation schema"""
    job_id: UUID
    cover_letter: Optional[str] = Field(None, max_length=2000)
    resume_id: Optional[UUID] = None
    additional_documents: List[UUID] = []
    expected_salary: Optional[Decimal] = None
    available_start_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=1000)

class JobApplicationResponse(BaseModel):
    """Job application response schema"""
    id: UUID
    job_id: UUID
    job_title: str
    company_name: str
    candidate_id: str
    status: str
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = None
    expected_salary: Optional[Decimal] = None
    available_start_date: Optional[date] = None
    notes: Optional[str] = None
    applied_at: datetime
    last_updated: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ApplicationStatusUpdate(BaseModel):
    """Application status update schema"""
    status: str = Field(..., pattern=r'^(applied|under_review|interview_scheduled|interviewed|offer_extended|hired|rejected|withdrawn)$')
    notes: Optional[str] = Field(None, max_length=1000)

class ResumeUploadResponse(BaseModel):
    """Resume upload response schema"""
    id: UUID
    filename: str
    file_size: int
    mime_type: str
    upload_url: str
    download_url: Optional[str] = None
    is_primary: bool = False
    parsed_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class DocumentUploadResponse(BaseModel):
    """Document upload response schema"""
    id: UUID
    filename: str
    document_type: str
    file_size: int
    mime_type: str
    upload_url: str
    download_url: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class InterviewAvailabilityCreate(BaseModel):
    """Interview availability creation schema"""
    start_time: datetime
    end_time: datetime
    timezone: str = Field(default="UTC", max_length=50)
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)

class InterviewAvailabilityResponse(BaseModel):
    """Interview availability response schema"""
    id: UUID
    candidate_id: str
    start_time: datetime
    end_time: datetime
    timezone: str
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    notes: Optional[str] = None
    is_booked: bool = False
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CommunicationPreferencesUpdate(BaseModel):
    """Communication preferences update schema"""
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    phone_notifications: Optional[bool] = None
    job_alerts: Optional[bool] = None
    application_updates: Optional[bool] = None
    interview_reminders: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    preferred_contact_time: Optional[str] = None
    timezone: Optional[str] = Field(None, max_length=50)

class CommunicationPreferencesResponse(BaseModel):
    """Communication preferences response schema"""
    id: UUID
    candidate_id: str
    email_notifications: bool = True
    sms_notifications: bool = False
    phone_notifications: bool = False
    job_alerts: bool = True
    application_updates: bool = True
    interview_reminders: bool = True
    marketing_emails: bool = False
    preferred_contact_time: Optional[str] = None
    timezone: str = "UTC"
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CandidateSkillCreate(BaseModel):
    """Candidate skill creation schema"""
    name: str = Field(..., min_length=1, max_length=100)
    level: SkillLevel
    years_of_experience: Optional[int] = Field(None, ge=0, le=50)
    is_primary: bool = False
    certifications: List[str] = []
    last_used: Optional[date] = None

class CandidateSkillResponse(BaseModel):
    """Candidate skill response schema"""
    id: UUID
    candidate_id: str
    name: str
    level: SkillLevel
    years_of_experience: Optional[int] = None
    is_primary: bool = False
    certifications: List[str] = []
    last_used: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SkillAssessmentResponse(BaseModel):
    """Skill assessment response schema"""
    id: UUID
    candidate_id: str
    skill_name: str
    assessment_type: str
    score: Optional[float] = None
    max_score: Optional[float] = None
    percentage: Optional[float] = None
    level_achieved: Optional[SkillLevel] = None
    assessment_date: datetime
    expires_at: Optional[datetime] = None
    certificate_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class JobPreferencesCreate(BaseModel):
    """Job preferences creation schema"""
    preferred_locations: List[str] = []
    preferred_departments: List[str] = []
    preferred_employment_types: List[str] = []
    min_salary: Optional[Decimal] = None
    max_salary: Optional[Decimal] = None
    currency: str = Field(default="USD", max_length=3)
    remote_work_only: bool = False
    willing_to_relocate: bool = False
    preferred_company_sizes: List[str] = []
    preferred_industries: List[str] = []
    work_authorization_required: bool = False

class ApplicationMetrics(BaseModel):
    """Application metrics schema"""
    total_applications: int = 0
    applications_this_week: int = 0
    applications_this_month: int = 0
    response_rate: float = 0.0
    interview_rate: float = 0.0
    offer_rate: float = 0.0
    avg_response_time_days: float = 0.0
    status_breakdown: Dict[str, int] = {}
    monthly_trend: List[Dict[str, Any]] = []