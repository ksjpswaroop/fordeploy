from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import TimestampMixin, InterviewStatus, InterviewType, Priority

# Interview schemas
class InterviewBase(BaseModel):
    """Base interview schema"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    interview_type: InterviewType
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=480)
    location: Optional[str] = Field(None, max_length=500)
    meeting_link: Optional[str] = None
    interviewer_notes: Optional[str] = None
    preparation_notes: Optional[str] = None

class InterviewCreate(InterviewBase):
    """Interview creation schema"""
    application_id: int
    interviewer_ids: List[int] = []

class InterviewUpdate(BaseModel):
    """Interview update schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    interview_type: Optional[InterviewType] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    location: Optional[str] = Field(None, max_length=500)
    meeting_link: Optional[str] = None
    status: Optional[InterviewStatus] = None
    interviewer_notes: Optional[str] = None
    preparation_notes: Optional[str] = None
    interviewer_ids: Optional[List[int]] = None

class InterviewResponse(InterviewBase, TimestampMixin):
    """Interview response schema"""
    id: int
    application_id: int
    status: InterviewStatus
    candidate_id: int
    job_id: int
    
    # Related data
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    job_title: Optional[str] = None
    interviewer_names: List[str] = []
    
    model_config = ConfigDict(from_attributes=True)

class InterviewDetailResponse(InterviewResponse):
    """Detailed interview response"""
    application: Optional[Dict[str, Any]] = None
    interviewers: Optional[List[Dict[str, Any]]] = []
    feedback: Optional[List[Dict[str, Any]]] = []
    candidate_feedback: Optional[Dict[str, Any]] = None

# Interview feedback schemas
class InterviewFeedbackBase(BaseModel):
    """Base interview feedback schema"""
    overall_rating: int = Field(..., ge=1, le=5)
    technical_skills: Optional[int] = Field(None, ge=1, le=5)
    communication_skills: Optional[int] = Field(None, ge=1, le=5)
    cultural_fit: Optional[int] = Field(None, ge=1, le=5)
    experience_relevance: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = None
    strengths: Optional[List[str]] = []
    areas_for_improvement: Optional[List[str]] = []
    recommendation: str = Field(..., pattern="^(hire|maybe|no_hire)$")
    next_steps: Optional[str] = None

class InterviewFeedbackCreate(InterviewFeedbackBase):
    """Interview feedback creation schema"""
    pass

class InterviewFeedbackUpdate(BaseModel):
    """Interview feedback update schema"""
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    technical_skills: Optional[int] = Field(None, ge=1, le=5)
    communication_skills: Optional[int] = Field(None, ge=1, le=5)
    cultural_fit: Optional[int] = Field(None, ge=1, le=5)
    experience_relevance: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = None
    strengths: Optional[List[str]] = None
    areas_for_improvement: Optional[List[str]] = None
    recommendation: Optional[str] = Field(None, pattern="^(hire|maybe|no_hire)$")
    next_steps: Optional[str] = None

class InterviewFeedbackResponse(InterviewFeedbackBase, TimestampMixin):
    """Interview feedback response schema"""
    id: int
    interview_id: int
    interviewer_id: int
    interviewer_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Candidate interview feedback schemas
class CandidateInterviewFeedbackBase(BaseModel):
    """Base candidate interview feedback schema"""
    overall_experience: int = Field(..., ge=1, le=5)
    interviewer_professionalism: Optional[int] = Field(None, ge=1, le=5)
    process_clarity: Optional[int] = Field(None, ge=1, le=5)
    company_interest: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = None
    suggestions: Optional[str] = None
    would_recommend_company: Optional[bool] = None

class CandidateInterviewFeedbackCreate(CandidateInterviewFeedbackBase):
    """Candidate interview feedback creation schema"""
    pass

class CandidateInterviewFeedbackResponse(CandidateInterviewFeedbackBase, TimestampMixin):
    """Candidate interview feedback response schema"""
    id: int
    interview_id: int
    candidate_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Interview scheduling schemas
class InterviewRescheduleRequest(BaseModel):
    """Interview reschedule request schema"""
    new_scheduled_at: datetime
    reason: Optional[str] = Field(None, max_length=500)

class InterviewAcceptRequest(BaseModel):
    """Interview accept request schema"""
    notes: Optional[str] = Field(None, max_length=500)

class InterviewDeclineRequest(BaseModel):
    """Interview decline request schema"""
    reason: str = Field(..., min_length=1, max_length=500)

# Interview availability schemas
class InterviewSlotBase(BaseModel):
    """Base interview slot schema"""
    start_time: datetime
    end_time: datetime
    is_available: bool = True
    notes: Optional[str] = None

class InterviewSlotCreate(InterviewSlotBase):
    """Interview slot creation schema"""
    interviewer_id: int

class InterviewSlotResponse(InterviewSlotBase, TimestampMixin):
    """Interview slot response schema"""
    id: int
    interviewer_id: int
    interviewer_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Interview analytics schemas
class InterviewAnalyticsResponse(BaseModel):
    """Interview analytics response"""
    total_interviews: int = 0
    interviews_this_month: int = 0
    completed_interviews: int = 0
    cancelled_interviews: int = 0
    average_rating: float = 0.0
    hire_rate: float = 0.0
    no_show_rate: float = 0.0
    average_duration: int = 0
    interview_type_breakdown: Dict[str, int] = {}
    monthly_interview_trend: List[Dict[str, Any]] = []
    interviewer_performance: List[Dict[str, Any]] = []