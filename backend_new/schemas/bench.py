from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from .base import (
    TimestampMixin, BenchStatus, AvailabilityStatus, SalesStatus,
    WorkAuthorization, RemoteWorkPreference, SkillLevel
)

# Candidate Bench Schemas
class CandidateBenchBase(BaseModel):
    """Base schema for candidate bench"""
    current_title: str = Field(..., min_length=1, max_length=200)
    experience_years: int = Field(..., ge=0, le=50)
    current_salary: Optional[Decimal] = Field(None, ge=0)
    expected_salary: Optional[Decimal] = Field(None, ge=0)
    salary_currency: str = Field(default="USD", max_length=3)
    
    # Location and Availability
    current_location: str = Field(..., min_length=1, max_length=200)
    willing_to_relocate: bool = Field(default=False)
    preferred_locations: Optional[List[str]] = Field(default=[])
    remote_work_preference: RemoteWorkPreference = Field(default=RemoteWorkPreference.FLEXIBLE)
    
    # Availability
    availability_status: AvailabilityStatus = Field(default=AvailabilityStatus.AVAILABLE)
    available_from: Optional[datetime] = None
    notice_period_days: int = Field(default=0, ge=0)
    
    # Work Authorization
    work_authorization: WorkAuthorization = Field(...)
    visa_status: Optional[str] = Field(None, max_length=100)
    visa_expiry: Optional[datetime] = None
    
    # Education
    highest_education: Optional[str] = Field(None, max_length=100)
    education_field: Optional[str] = Field(None, max_length=200)
    university: Optional[str] = Field(None, max_length=200)
    graduation_year: Optional[int] = Field(None, ge=1950, le=2030)
    
    # Professional Summary
    professional_summary: Optional[str] = None
    key_achievements: Optional[List[str]] = Field(default=[])
    
    # Documents
    resume_url: Optional[str] = Field(None, max_length=500)
    portfolio_url: Optional[str] = Field(None, max_length=500)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)
    
    # Sales Information
    hourly_rate: Optional[Decimal] = Field(None, ge=0)
    markup_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    
    # Marketing
    marketing_approved: bool = Field(default=False)
    marketing_notes: Optional[str] = None
    unique_selling_points: Optional[List[str]] = Field(default=[])
    
    # Contact Preferences
    preferred_contact_method: str = Field(default="email", max_length=50)
    best_time_to_contact: Optional[str] = Field(None, max_length=100)
    timezone: str = Field(default="UTC", max_length=50)

class CandidateBenchCreate(CandidateBenchBase):
    """Schema for creating candidate bench profile"""
    user_id: int = Field(..., gt=0)
    profile_manager_id: Optional[int] = Field(None, gt=0)

class CandidateBenchUpdate(BaseModel):
    """Schema for updating candidate bench profile"""
    current_title: Optional[str] = Field(None, min_length=1, max_length=200)
    experience_years: Optional[int] = Field(None, ge=0, le=50)
    current_salary: Optional[Decimal] = Field(None, ge=0)
    expected_salary: Optional[Decimal] = Field(None, ge=0)
    current_location: Optional[str] = Field(None, min_length=1, max_length=200)
    willing_to_relocate: Optional[bool] = None
    preferred_locations: Optional[List[str]] = None
    remote_work_preference: Optional[RemoteWorkPreference] = None
    availability_status: Optional[AvailabilityStatus] = None
    available_from: Optional[datetime] = None
    notice_period_days: Optional[int] = Field(None, ge=0)
    work_authorization: Optional[WorkAuthorization] = None
    visa_status: Optional[str] = Field(None, max_length=100)
    visa_expiry: Optional[datetime] = None
    professional_summary: Optional[str] = None
    key_achievements: Optional[List[str]] = None
    hourly_rate: Optional[Decimal] = Field(None, ge=0)
    markup_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    marketing_approved: Optional[bool] = None
    marketing_notes: Optional[str] = None
    unique_selling_points: Optional[List[str]] = None
    profile_manager_id: Optional[int] = Field(None, gt=0)

class CandidateSkill(BaseModel):
    """Schema for candidate skills"""
    skill_id: int = Field(..., gt=0)
    skill_name: str = Field(..., min_length=1, max_length=100)
    skill_level: SkillLevel = Field(...)
    years_experience: Optional[int] = Field(None, ge=0)
    is_primary: bool = Field(default=False)
    verified: bool = Field(default=False)

class CandidateCertification(BaseModel):
    """Schema for candidate certifications"""
    certification_id: int = Field(..., gt=0)
    certification_name: str = Field(..., min_length=1, max_length=200)
    issuing_organization: str = Field(..., min_length=1, max_length=200)
    obtained_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    is_active: bool = Field(default=True)

class CandidateBenchResponse(CandidateBenchBase, TimestampMixin):
    """Schema for candidate bench response"""
    id: int
    user_id: int
    profile_manager_id: Optional[int] = None
    bench_status: BenchStatus
    bench_start_date: datetime
    bench_end_date: Optional[datetime] = None
    
    # Performance Metrics
    interview_success_rate: Optional[Decimal] = None
    placement_success_rate: Optional[Decimal] = None
    client_satisfaction_score: Optional[Decimal] = None
    
    # Calculated fields
    is_available: bool
    years_on_bench: float
    total_submissions: int
    successful_placements: int
    
    # Related data
    skills: Optional[List[CandidateSkill]] = Field(default=[])
    certifications: Optional[List[CandidateCertification]] = Field(default=[])
    
    model_config = ConfigDict(from_attributes=True)

class CandidateBenchSummary(BaseModel):
    """Summary schema for candidate bench listings"""
    id: int
    user_id: int
    current_title: str
    experience_years: int
    current_location: str
    availability_status: AvailabilityStatus
    bench_status: BenchStatus
    hourly_rate: Optional[Decimal] = None
    work_authorization: WorkAuthorization
    remote_work_preference: RemoteWorkPreference
    years_on_bench: float
    total_submissions: int
    successful_placements: int
    
    model_config = ConfigDict(from_attributes=True)

# Candidate Submission Schemas
class CandidateSubmissionBase(BaseModel):
    """Base schema for candidate submissions"""
    position_title: str = Field(..., min_length=1, max_length=200)
    client_rate: Optional[Decimal] = Field(None, ge=0)
    duration_months: Optional[int] = Field(None, ge=1, le=60)
    submission_notes: Optional[str] = None

class CandidateSubmissionCreate(CandidateSubmissionBase):
    """Schema for creating candidate submission"""
    candidate_id: int = Field(..., gt=0)
    client_id: int = Field(..., gt=0)
    job_opportunity_id: Optional[int] = Field(None, gt=0)

class CandidateSubmissionUpdate(BaseModel):
    """Schema for updating candidate submission"""
    status: Optional[str] = Field(None, max_length=50)
    client_feedback: Optional[str] = None
    rejection_reason: Optional[str] = Field(None, max_length=200)
    interview_scheduled: Optional[bool] = None
    interview_date: Optional[datetime] = None
    interview_feedback: Optional[str] = None
    follow_up_date: Optional[datetime] = None

class CandidateSubmissionResponse(CandidateSubmissionBase, TimestampMixin):
    """Schema for candidate submission response"""
    id: int
    candidate_id: int
    client_id: int
    job_opportunity_id: Optional[int] = None
    submitted_by: int
    submission_date: datetime
    status: str
    status_updated_at: datetime
    client_feedback: Optional[str] = None
    rejection_reason: Optional[str] = None
    interview_scheduled: bool
    interview_date: Optional[datetime] = None
    interview_feedback: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Candidate Sale Schemas
class CandidateSaleBase(BaseModel):
    """Base schema for candidate sales"""
    start_date: datetime = Field(...)
    end_date: Optional[datetime] = None
    hourly_rate: Decimal = Field(..., gt=0)
    markup_percentage: Decimal = Field(..., ge=0, le=100)
    contract_type: str = Field(..., max_length=50)
    duration_months: Optional[int] = Field(None, ge=1, le=60)
    hours_per_week: int = Field(default=40, ge=1, le=80)

class CandidateSaleCreate(CandidateSaleBase):
    """Schema for creating candidate sale"""
    candidate_id: int = Field(..., gt=0)
    client_id: int = Field(..., gt=0)
    submission_id: Optional[int] = Field(None, gt=0)
    sales_person_id: int = Field(..., gt=0)

class CandidateSaleUpdate(BaseModel):
    """Schema for updating candidate sale"""
    end_date: Optional[datetime] = None
    status: Optional[str] = Field(None, max_length=50)
    client_satisfaction_score: Optional[Decimal] = Field(None, ge=1, le=5)
    renewal_probability: Optional[Decimal] = Field(None, ge=0, le=1)
    commission_percentage: Optional[Decimal] = Field(None, ge=0, le=100)

class CandidateSaleResponse(CandidateSaleBase, TimestampMixin):
    """Schema for candidate sale response"""
    id: int
    candidate_id: int
    client_id: int
    submission_id: Optional[int] = None
    sales_person_id: int
    sale_date: datetime
    status: str
    gross_margin: Decimal
    total_revenue: Optional[Decimal] = None
    commission_percentage: Optional[Decimal] = None
    commission_amount: Optional[Decimal] = None
    client_satisfaction_score: Optional[Decimal] = None
    renewal_probability: Optional[Decimal] = None
    monthly_revenue: Decimal
    
    model_config = ConfigDict(from_attributes=True)

# Interview Schemas
class CandidateInterviewBase(BaseModel):
    """Base schema for candidate interviews"""
    interview_date: datetime = Field(...)
    interview_type: str = Field(..., max_length=50)
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    interviewer_name: Optional[str] = Field(None, max_length=200)
    interviewer_title: Optional[str] = Field(None, max_length=200)
    interviewer_email: Optional[str] = Field(None, max_length=255)

class CandidateInterviewCreate(CandidateInterviewBase):
    """Schema for creating candidate interview"""
    candidate_id: int = Field(..., gt=0)
    client_id: int = Field(..., gt=0)
    submission_id: Optional[int] = Field(None, gt=0)

class CandidateInterviewUpdate(BaseModel):
    """Schema for updating candidate interview"""
    interview_date: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    overall_rating: Optional[int] = Field(None, ge=1, le=10)
    technical_rating: Optional[int] = Field(None, ge=1, le=10)
    communication_rating: Optional[int] = Field(None, ge=1, le=10)
    cultural_fit_rating: Optional[int] = Field(None, ge=1, le=10)
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    detailed_feedback: Optional[str] = None
    recommendation: Optional[str] = Field(None, max_length=50)
    next_steps: Optional[str] = None
    status: Optional[str] = Field(None, max_length=50)

class CandidateInterviewResponse(CandidateInterviewBase, TimestampMixin):
    """Schema for candidate interview response"""
    id: int
    candidate_id: int
    client_id: int
    submission_id: Optional[int] = None
    overall_rating: Optional[int] = None
    technical_rating: Optional[int] = None
    communication_rating: Optional[int] = None
    cultural_fit_rating: Optional[int] = None
    strengths: Optional[List[str]] = Field(default=[])
    weaknesses: Optional[List[str]] = Field(default=[])
    detailed_feedback: Optional[str] = None
    recommendation: Optional[str] = None
    next_steps: Optional[str] = None
    status: str
    
    model_config = ConfigDict(from_attributes=True)

# Search and Filter Schemas
class CandidateBenchFilters(BaseModel):
    """Schema for filtering candidate bench"""
    availability_status: Optional[List[AvailabilityStatus]] = None
    bench_status: Optional[List[BenchStatus]] = None
    work_authorization: Optional[List[WorkAuthorization]] = None
    remote_work_preference: Optional[List[RemoteWorkPreference]] = None
    experience_years_min: Optional[int] = Field(None, ge=0)
    experience_years_max: Optional[int] = Field(None, ge=0)
    hourly_rate_min: Optional[Decimal] = Field(None, ge=0)
    hourly_rate_max: Optional[Decimal] = Field(None, ge=0)
    locations: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    profile_manager_id: Optional[int] = Field(None, gt=0)
    marketing_approved: Optional[bool] = None
    
    @validator('experience_years_max')
    def validate_experience_range(cls, v, values):
        if v is not None and 'experience_years_min' in values and values['experience_years_min'] is not None:
            if v < values['experience_years_min']:
                raise ValueError('experience_years_max must be greater than or equal to experience_years_min')
        return v
    
    @validator('hourly_rate_max')
    def validate_rate_range(cls, v, values):
        if v is not None and 'hourly_rate_min' in values and values['hourly_rate_min'] is not None:
            if v < values['hourly_rate_min']:
                raise ValueError('hourly_rate_max must be greater than or equal to hourly_rate_min')
        return v

class CandidateBenchSearch(BaseModel):
    """Schema for searching candidate bench"""
    query: Optional[str] = Field(None, min_length=1, max_length=200)
    filters: Optional[CandidateBenchFilters] = None
    sort_by: Optional[str] = Field(default="created_at", max_length=50)
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")

# Analytics Schemas
class BenchAnalytics(BaseModel):
    """Schema for bench analytics"""
    total_candidates: int
    active_candidates: int
    available_candidates: int
    engaged_candidates: int
    total_submissions: int
    successful_placements: int
    average_time_to_placement: Optional[float] = None
    total_revenue: Decimal
    average_hourly_rate: Optional[Decimal] = None
    top_skills: List[Dict[str, Any]]
    placement_rate: float
    
    model_config = ConfigDict(from_attributes=True)

class ProfileManagerStats(BaseModel):
    """Schema for profile manager statistics"""
    profile_manager_id: int
    managed_candidates_count: int
    active_candidates_count: int
    total_submissions: int
    successful_placements: int
    total_revenue: Decimal
    placement_rate: float
    average_time_to_placement: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)