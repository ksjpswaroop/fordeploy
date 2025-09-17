

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from .base import TimestampMixin, JobStatus, ExperienceLevel, ApplicationStatus

# Application status update schema
class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


# Job schemas
class JobBase(BaseModel):
    """Base job schema"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    requirements: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1, max_length=200)
    department: str = Field(..., min_length=1, max_length=100)
    employment_type: str = Field(..., min_length=1, max_length=50)  # full-time, part-time, contract
    experience_level: ExperienceLevel
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    currency: str = Field(default="USD", max_length=3)
    remote_allowed: bool = False
    benefits: Optional[List[str]] = []
    skills_required: Optional[List[str]] = []
    skills_preferred: Optional[List[str]] = []

class JobCreate(JobBase):
    """Job creation schema"""
    recruiter_id: Optional[int] = None

class JobUpdate(BaseModel):
    """Job update schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    requirements: Optional[str] = Field(None, min_length=1)
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    employment_type: Optional[str] = Field(None, min_length=1, max_length=50)
    experience_level: Optional[ExperienceLevel] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    currency: Optional[str] = Field(None, max_length=3)
    remote_allowed: Optional[bool] = None
    benefits: Optional[List[str]] = None
    skills_required: Optional[List[str]] = None
    skills_preferred: Optional[List[str]] = None
    status: Optional[JobStatus] = None
    recruiter_id: Optional[int] = None

class JobResponse(JobBase, TimestampMixin):
    """Job response schema"""
    id: int
    status: JobStatus
    recruiter_id: Optional[int] = None
    posted_date: Optional[date] = None
    closing_date: Optional[date] = None
    applications_count: int = 0
    views_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

class JobListResponse(BaseModel):
    """Job list item response"""
    id: int
    title: str
    location: str
    department: str
    employment_type: str
    experience_level: ExperienceLevel
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    currency: str
    remote_allowed: bool
    status: JobStatus
    posted_date: Optional[date] = None
    applications_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# Application schemas
class ApplicationBase(BaseModel):
    """Base application schema"""
    cover_letter: Optional[str] = None
    expected_salary: Optional[Decimal] = None
    available_from: Optional[date] = None
    notes: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    """Application creation schema"""
    job_id: int

class ApplicationUpdate(BaseModel):
    """Application update schema"""
    status: Optional[ApplicationStatus] = None
    cover_letter: Optional[str] = None
    expected_salary: Optional[Decimal] = None
    available_from: Optional[date] = None
    notes: Optional[str] = None
    recruiter_notes: Optional[str] = None

class ApplicationResponse(ApplicationBase, TimestampMixin):
    """Application response schema"""
    id: int
    job_id: int
    candidate_id: int
    status: ApplicationStatus
    applied_date: datetime
    recruiter_notes: Optional[str] = None
    
    # Related data
    job_title: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ApplicationDetailResponse(ApplicationResponse):
    """Detailed application response"""
    job: Optional[JobResponse] = None
    candidate: Optional[Dict[str, Any]] = None
    feedback: Optional[List[Dict[str, Any]]] = []
    interviews: Optional[List[Dict[str, Any]]] = []
    documents: Optional[List[Dict[str, Any]]] = []

# Saved job schemas
class SavedJobCreate(BaseModel):
    """Saved job creation schema"""
    job_id: int
    notes: Optional[str] = None

class SavedJobResponse(TimestampMixin):
    """Saved job response schema"""
    id: int
    job_id: int
    candidate_id: int
    notes: Optional[str] = None
    job: Optional[JobListResponse] = None
    
    model_config = ConfigDict(from_attributes=True)

# Job search and filter schemas
class JobSearchParams(BaseModel):
    """Job search parameters"""
    q: Optional[str] = None  # Search query
    location: Optional[str] = None
    department: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[ExperienceLevel] = None
    remote_allowed: Optional[bool] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    skills: Optional[List[str]] = None
    posted_after: Optional[date] = None
    status: Optional[JobStatus] = None

class JobRecommendationResponse(JobListResponse):
    """Job recommendation response with match score"""
    match_score: float = Field(..., ge=0, le=1)
    match_reasons: List[str] = []