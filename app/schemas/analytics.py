from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from .base import TimestampMixin

# Base analytics schemas
class DateRangeFilter(BaseModel):
    """Date range filter for analytics"""
    start_date: date
    end_date: date
    
    def validate_date_range(self):
        if self.start_date > self.end_date:
            raise ValueError("Start date must be before end date")
        return self

class AnalyticsFilter(BaseModel):
    """Common analytics filter"""
    date_range: Optional[DateRangeFilter] = None
    department_ids: Optional[List[int]] = []
    job_ids: Optional[List[int]] = []
    recruiter_ids: Optional[List[int]] = []
    location: Optional[str] = None
    job_type: Optional[str] = None

# Recruitment metrics schemas
class RecruitmentMetrics(BaseModel):
    """Recruitment metrics response"""
    total_jobs: int = 0
    active_jobs: int = 0
    total_applications: int = 0
    new_applications: int = 0
    interviews_scheduled: int = 0
    interviews_completed: int = 0
    offers_made: int = 0
    offers_accepted: int = 0
    hires_made: int = 0
    
    # Calculated metrics
    application_to_interview_rate: float = 0.0
    interview_to_offer_rate: float = 0.0
    offer_acceptance_rate: float = 0.0
    time_to_hire_avg_days: float = 0.0
    cost_per_hire: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)

class RecruitmentTrends(BaseModel):
    """Recruitment trends over time"""
    period: str  # daily, weekly, monthly
    data_points: List[Dict[str, Union[str, int, float]]]  # [{"date": "2024-01", "applications": 50, "hires": 5}]
    
    model_config = ConfigDict(from_attributes=True)

# Job analytics schemas
class JobAnalytics(BaseModel):
    """Job-specific analytics"""
    job_id: int
    job_title: str
    total_applications: int = 0
    qualified_applications: int = 0
    interviews_scheduled: int = 0
    offers_made: int = 0
    hires_made: int = 0
    avg_time_to_fill_days: float = 0.0
    application_sources: Dict[str, int] = {}  # {"linkedin": 20, "website": 15}
    top_skills_required: List[str] = []
    salary_range_applications: Dict[str, int] = {}  # {"50k-60k": 10, "60k-70k": 15}
    
    model_config = ConfigDict(from_attributes=True)

class JobPerformanceMetrics(BaseModel):
    """Job performance metrics"""
    job_id: int
    views: int = 0
    applications: int = 0
    view_to_application_rate: float = 0.0
    quality_score: float = 0.0  # Based on qualified applications
    competition_index: float = 0.0  # Compared to similar jobs
    
    model_config = ConfigDict(from_attributes=True)

# Candidate analytics schemas
class CandidateAnalytics(BaseModel):
    """Candidate analytics"""
    total_candidates: int = 0
    active_candidates: int = 0
    new_registrations: int = 0
    candidates_by_experience: Dict[str, int] = {}  # {"entry": 50, "mid": 30, "senior": 20}
    candidates_by_location: Dict[str, int] = {}
    candidates_by_skills: Dict[str, int] = {}
    top_universities: List[Dict[str, Union[str, int]]] = []  # [{"name": "MIT", "count": 15}]
    avg_response_time_hours: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)

class CandidateEngagement(BaseModel):
    """Candidate engagement metrics"""
    profile_completion_rate: float = 0.0
    application_completion_rate: float = 0.0
    interview_attendance_rate: float = 0.0
    offer_acceptance_rate: float = 0.0
    avg_applications_per_candidate: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)

# Recruiter analytics schemas
class RecruiterPerformance(BaseModel):
    """Recruiter performance metrics"""
    recruiter_id: int
    recruiter_name: str
    jobs_managed: int = 0
    applications_reviewed: int = 0
    interviews_conducted: int = 0
    offers_made: int = 0
    hires_made: int = 0
    avg_time_to_hire_days: float = 0.0
    candidate_satisfaction_score: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)

RecruiterPerformanceResponse = RecruiterPerformance

# Aliases for API response imports
RecruiterPerformanceResponse = RecruiterPerformance

class TeamPerformance(BaseModel):
    """Team performance metrics"""
    team_name: str
    total_recruiters: int = 0
    total_jobs: int = 0
    total_hires: int = 0
    avg_time_to_hire_days: float = 0.0
    team_efficiency_score: float = 0.0
    top_performers: List[RecruiterPerformance] = []
    
    model_config = ConfigDict(from_attributes=True)

JobAnalyticsResponse = JobAnalytics

# Alias for API response import
JobAnalyticsResponse = JobAnalytics

# Pipeline analytics schemas
class PipelineStage(BaseModel):
    """Pipeline stage metrics"""
    stage_name: str
    candidate_count: int = 0
    avg_time_in_stage_days: float = 0.0
    conversion_rate: float = 0.0
    drop_off_rate: float = 0.0

class PipelineAnalytics(BaseModel):
    """Recruitment pipeline analytics"""
    total_candidates_in_pipeline: int = 0
    stages: List[PipelineStage] = []
    bottlenecks: List[str] = []  # Stages with high drop-off rates
    avg_pipeline_duration_days: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)

# Source analytics schemas
class SourceAnalytics(BaseModel):
    """Application source analytics"""
    source_name: str
    applications: int = 0
    qualified_applications: int = 0
    interviews: int = 0
    hires: int = 0
    cost_per_application: float = 0.0
    cost_per_hire: float = 0.0
    quality_score: float = 0.0
    roi: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)

# Diversity analytics schemas
class DiversityMetrics(BaseModel):
    """Diversity and inclusion metrics"""
    gender_distribution: Dict[str, int] = {}  # {"male": 60, "female": 35, "other": 5}
    age_distribution: Dict[str, int] = {}  # {"20-30": 40, "30-40": 35, "40+": 25}
    ethnicity_distribution: Dict[str, int] = {}
    education_distribution: Dict[str, int] = {}
    diversity_index: float = 0.0  # Overall diversity score
    
    model_config = ConfigDict(from_attributes=True)

# Financial analytics schemas
class CostAnalytics(BaseModel):
    """Cost and budget analytics"""
    total_recruitment_cost: float = 0.0
    cost_per_hire: float = 0.0
    cost_by_source: Dict[str, float] = {}
    cost_by_department: Dict[str, float] = {}
    budget_utilization: float = 0.0
    projected_costs: Dict[str, float] = {}  # Monthly projections
    
    model_config = ConfigDict(from_attributes=True)

# Predictive analytics schemas
class PredictiveMetrics(BaseModel):
    """Predictive analytics and forecasting"""
    predicted_hires_next_month: int = 0
    predicted_applications_next_month: int = 0
    hiring_velocity_trend: str = "stable"  # increasing, decreasing, stable
    candidate_quality_trend: str = "stable"
    time_to_hire_forecast: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)

# Dashboard schemas
class DashboardMetrics(BaseModel):
    """Main dashboard metrics"""
    recruitment_metrics: RecruitmentMetrics
    candidate_analytics: CandidateAnalytics
    pipeline_analytics: PipelineAnalytics
    top_performing_jobs: List[JobAnalytics]
    recent_activities: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]  # Performance alerts, bottlenecks, etc.
    
    model_config = ConfigDict(from_attributes=True)

# Report schemas
class ReportRequest(BaseModel):
    """Report generation request"""
    report_type: str = Field(..., pattern="^(recruitment|candidate|job|recruiter|pipeline|diversity|cost)$")
    filters: AnalyticsFilter
    format: str = Field(default="json", pattern="^(json|csv|pdf)$")
    include_charts: bool = True
    email_recipients: Optional[List[str]] = []

class ReportResponse(BaseModel):
    """Report generation response"""
    report_id: str
    report_type: str
    status: str = "generating"  # generating, completed, failed
    download_url: Optional[str] = None
    generated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Custom analytics schemas
class CustomMetricDefinition(BaseModel):
    """Custom metric definition"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    formula: str  # SQL-like formula or calculation logic
    data_sources: List[str]  # Tables or entities used
    filters: Optional[Dict[str, Any]] = {}
    visualization_type: str = Field(default="number", pattern="^(number|chart|table|gauge)$")

class CustomMetricResponse(CustomMetricDefinition, TimestampMixin):
    """Custom metric response"""
    id: int
    created_by: int
    is_active: bool = True
    last_calculated: Optional[datetime] = None
    current_value: Optional[Union[int, float, str]] = None
    
    model_config = ConfigDict(from_attributes=True)