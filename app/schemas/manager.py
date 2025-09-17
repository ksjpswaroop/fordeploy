"""Pydantic schemas for manager functionality."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, date
from enum import Enum
from decimal import Decimal

class PerformanceMetric(str, Enum):
    """Performance metric types."""
    APPLICATIONS_PROCESSED = "applications_processed"
    INTERVIEWS_CONDUCTED = "interviews_conducted"
    HIRES_MADE = "hires_made"
    TIME_TO_HIRE = "time_to_hire"
    CANDIDATE_SATISFACTION = "candidate_satisfaction"
    CLIENT_SATISFACTION = "client_satisfaction"
    RESPONSE_TIME = "response_time"
    QUALITY_SCORE = "quality_score"
    ACTIVITY_SCORE = "activity_score"
    GOAL_COMPLETION = "goal_completion"

class GoalStatus(str, Enum):
    """Goal status types."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"

class GoalType(str, Enum):
    """Goal type classifications."""
    INDIVIDUAL = "individual"
    TEAM = "team"
    DEPARTMENT = "department"
    COMPANY = "company"

class WorkloadStatus(str, Enum):
    """Workload status types."""
    UNDERUTILIZED = "underutilized"
    OPTIMAL = "optimal"
    OVERLOADED = "overloaded"
    CRITICAL = "critical"

# Recruiter Performance Schemas
class RecruiterPerformanceMetrics(BaseModel):
    """Recruiter performance metrics schema."""
    recruiter_id: str  # Clerk user ID
    recruiter_name: str
    recruiter_email: str
    period_start: date
    period_end: date
    metrics: Dict[PerformanceMetric, float] = {}
    total_applications: int = 0
    applications_processed: int = 0
    interviews_scheduled: int = 0
    interviews_completed: int = 0
    offers_extended: int = 0
    offers_accepted: int = 0
    hires_completed: int = 0
    average_time_to_hire_days: Optional[float] = None
    candidate_satisfaction_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    client_satisfaction_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    response_time_hours: Optional[float] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    activity_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    goal_completion_rate: Optional[float] = Field(None, ge=0.0, le=100.0)
    rank_in_team: Optional[int] = None
    total_team_members: Optional[int] = None
    improvement_suggestions: List[str] = []
    achievements: List[str] = []
    
    class Config:
        from_attributes = True

class RecruiterPerformanceResponse(BaseModel):
    """Response schema for recruiter performance data."""
    recruiter_id: str  # Clerk user ID
    recruiter_name: str
    recruiter_email: str
    period_start: date
    period_end: date
    metrics: Dict[PerformanceMetric, float] = {}
    total_applications: int = 0
    applications_processed: int = 0
    interviews_scheduled: int = 0
    interviews_completed: int = 0
    offers_extended: int = 0
    offers_accepted: int = 0
    hires_completed: int = 0
    average_time_to_hire_days: Optional[float] = None
    candidate_satisfaction_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    client_satisfaction_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    response_time_hours: Optional[float] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    activity_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    goal_completion_rate: Optional[float] = Field(None, ge=0.0, le=100.0)
    rank_in_team: Optional[int] = None
    total_team_members: Optional[int] = None
    improvement_suggestions: List[str] = []
    achievements: List[str] = []
    
    class Config:
        from_attributes = True

class PerformanceMetrics(BaseModel):
    """Performance metrics response schema."""
    recruiter_id: str
    period_start: date
    period_end: date
    metrics: Dict[PerformanceMetric, float] = {}
    summary: Dict[str, Any] = {}
    trends: Dict[str, str] = {}
    
    class Config:
        from_attributes = True

class PerformanceComparison(BaseModel):
    """Performance comparison schema."""
    current_period: RecruiterPerformanceMetrics
    previous_period: Optional[RecruiterPerformanceMetrics] = None
    team_average: Optional[Dict[PerformanceMetric, float]] = None
    company_average: Optional[Dict[PerformanceMetric, float]] = None
    percentile_rank: Optional[Dict[PerformanceMetric, float]] = None
    trends: Dict[PerformanceMetric, str] = {}  # "improving", "declining", "stable"
    
class TeamPerformanceOverview(BaseModel):
    """Team performance overview schema."""
    team_id: UUID
    team_name: str
    manager_id: str  # Clerk user ID
    period_start: date
    period_end: date
    total_recruiters: int
    active_recruiters: int
    team_metrics: Dict[PerformanceMetric, float] = {}
    top_performers: List[Dict[str, Any]] = []  # Top 3 performers
    underperformers: List[Dict[str, Any]] = []  # Bottom performers needing attention
    team_goals_progress: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    
    class Config:
        from_attributes = True

# Team Assignment Schemas
class TeamMember(BaseModel):
    """Team member schema."""
    user_id: str  # Clerk user ID
    name: str
    email: str
    role: str
    specializations: List[str] = []
    current_workload: int = 0
    max_workload: int = 100
    is_active: bool = True
    joined_team_at: datetime
    
    class Config:
        from_attributes = True

class TeamCreate(BaseModel):
    """Schema for creating teams."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    manager_id: str = Field(..., description="Clerk user ID of the manager")
    member_ids: List[str] = []  # Clerk user IDs
    specializations: List[str] = []  # Team specializations
    max_team_size: int = Field(20, ge=1, le=100)
    tenant_id: Optional[str] = None

class TeamUpdate(BaseModel):
    """Schema for updating teams."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    manager_id: Optional[str] = None
    specializations: Optional[List[str]] = None
    max_team_size: Optional[int] = Field(None, ge=1, le=100)
    is_active: Optional[bool] = None

class TeamResponse(BaseModel):
    """Team response schema."""
    id: UUID
    name: str
    description: Optional[str] = None
    manager_id: str
    manager_name: str
    members: List[TeamMember] = []
    specializations: List[str] = []
    current_size: int = 0
    max_team_size: int = 20
    is_active: bool = True
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TeamAssignmentCreate(BaseModel):
    """Team assignment creation schema."""
    team_id: UUID
    user_ids: List[str] = Field(..., min_items=1, max_items=50)
    role: Optional[str] = "recruiter"
    specializations: List[str] = []
    effective_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)

class TeamAssignmentResponse(BaseModel):
    """Team assignment response schema."""
    id: UUID
    team_id: UUID
    team_name: str
    user_id: str
    user_name: str
    role: str
    specializations: List[str] = []
    effective_date: date
    notes: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TeamAssignmentRequest(BaseModel):
    """Team assignment request schema."""
    team_id: UUID
    user_ids: List[str] = Field(..., min_items=1, max_items=50)
    role: Optional[str] = "recruiter"
    specializations: List[str] = []
    effective_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)

# Workload Management Schemas
class WorkloadMetrics(BaseModel):
    """Workload metrics schema."""
    user_id: str  # Clerk user ID
    user_name: str
    current_active_jobs: int = 0
    current_applications: int = 0
    scheduled_interviews: int = 0
    pending_tasks: int = 0
    overdue_tasks: int = 0
    workload_score: float = Field(0.0, ge=0.0, le=100.0)
    workload_status: WorkloadStatus
    capacity_utilization: float = Field(0.0, ge=0.0, le=100.0)
    estimated_hours_per_week: float = 0.0
    max_capacity_hours: float = 40.0
    burnout_risk_score: float = Field(0.0, ge=0.0, le=100.0)
    last_updated: datetime
    
    class Config:
        from_attributes = True

class WorkloadDistribution(BaseModel):
    """Workload distribution schema."""
    team_id: UUID
    team_name: str
    total_workload: float = 0.0
    average_workload: float = 0.0
    workload_variance: float = 0.0
    members: List[WorkloadMetrics] = []
    recommendations: List[str] = []
    rebalancing_suggestions: List[Dict[str, Any]] = []
    
class WorkloadDistributionResponse(BaseModel):
    """Workload distribution response schema."""
    team_id: UUID
    team_name: str
    total_workload: float = 0.0
    average_workload: float = 0.0
    workload_variance: float = 0.0
    members: List[WorkloadMetrics] = []
    recommendations: List[str] = []
    rebalancing_suggestions: List[Dict[str, Any]] = []
    
    class Config:
        from_attributes = True

class WorkloadAdjustment(BaseModel):
    """Workload adjustment schema."""
    team_id: UUID
    reassignments: List[Dict[str, Any]] = []  # Job/task reassignments
    reason: str = Field(..., min_length=1, max_length=500)
    effective_date: Optional[date] = None
    notify_affected_users: bool = True

class TeamMetrics(BaseModel):
    """Team metrics response schema."""
    team_id: UUID
    team_name: str
    period_start: date
    period_end: date
    total_members: int
    active_members: int
    metrics: Dict[PerformanceMetric, float] = {}
    performance_summary: Dict[str, Any] = {}
    trends: Dict[str, List[Dict[str, Any]]] = {}
    
    class Config:
        from_attributes = True

class WorkloadRebalanceRequest(BaseModel):
    """Workload rebalance request schema."""
    team_id: UUID
    reassignments: List[Dict[str, Any]] = []  # Job/task reassignments
    reason: str = Field(..., min_length=1, max_length=500)
    effective_date: Optional[date] = None
    notify_affected_users: bool = True

# Goal and Target Management Schemas
class RecruiterGoalCreate(BaseModel):
    """Recruiter goal creation schema."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    goal_type: GoalType
    target_value: float = Field(..., ge=0)
    target_metric: PerformanceMetric
    start_date: date
    end_date: date
    priority: str = Field("medium", pattern=r'^(low|medium|high|critical)$')
    is_public: bool = True
    milestones: List[Dict[str, Any]] = []

class RecruiterGoalUpdate(BaseModel):
    """Recruiter goal update schema."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    target_value: Optional[float] = Field(None, ge=0)
    end_date: Optional[date] = None
    priority: Optional[str] = Field(None, pattern=r'^(low|medium|high|critical)$')
    status: Optional[GoalStatus] = None
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    notes: Optional[str] = Field(None, max_length=1000)

class RecruiterGoalResponse(BaseModel):
    """Recruiter goal response schema."""
    id: UUID
    title: str
    description: Optional[str] = None
    goal_type: GoalType
    target_value: float
    current_value: float = 0.0
    target_metric: PerformanceMetric
    recruiter_id: str  # Clerk user ID
    recruiter_name: str
    start_date: date
    end_date: date
    status: GoalStatus
    priority: str
    progress_percentage: float = Field(0.0, ge=0.0, le=100.0)
    is_public: bool = True
    milestones: List[Dict[str, Any]] = []
    created_by: str  # Manager user ID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GoalCreate(BaseModel):
    """Schema for creating goals."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    goal_type: GoalType
    target_value: float = Field(..., ge=0)
    target_metric: PerformanceMetric
    assignee_ids: List[str] = Field(..., min_items=1)  # Clerk user IDs
    team_id: Optional[UUID] = None
    start_date: date
    end_date: date
    priority: str = Field("medium", pattern=r'^(low|medium|high|critical)$')
    is_public: bool = True
    parent_goal_id: Optional[UUID] = None
    milestones: List[Dict[str, Any]] = []
    
class GoalUpdate(BaseModel):
    """Schema for updating goals."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    target_value: Optional[float] = Field(None, ge=0)
    end_date: Optional[date] = None
    priority: Optional[str] = Field(None, pattern=r'^(low|medium|high|critical)$')
    status: Optional[GoalStatus] = None
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    notes: Optional[str] = Field(None, max_length=1000)
    
class GoalResponse(BaseModel):
    """Goal response schema."""
    id: UUID
    title: str
    description: Optional[str] = None
    goal_type: GoalType
    target_value: float
    current_value: float = 0.0
    target_metric: PerformanceMetric
    assignees: List[Dict[str, str]] = []  # [{"id": "123", "name": "John"}]
    team_id: Optional[UUID] = None
    team_name: Optional[str] = None
    start_date: date
    end_date: date
    status: GoalStatus
    priority: str
    progress_percentage: float = Field(0.0, ge=0.0, le=100.0)
    is_public: bool = True
    parent_goal_id: Optional[UUID] = None
    child_goals: List[UUID] = []
    milestones: List[Dict[str, Any]] = []
    created_by: str  # Manager user ID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GoalProgress(BaseModel):
    """Goal progress tracking schema."""
    goal_id: UUID
    current_value: float
    progress_percentage: float = Field(..., ge=0.0, le=100.0)
    notes: Optional[str] = Field(None, max_length=500)
    milestone_completed: Optional[str] = None
    updated_by: str  # User ID who updated progress
    updated_at: datetime
    
# Analytics and Reporting Schemas
class TeamAnalyticsRequest(BaseModel):
    """Team analytics request schema."""
    team_id: Optional[UUID] = None
    start_date: date
    end_date: date
    metrics: List[PerformanceMetric] = []
    include_individual_breakdown: bool = False
    include_trends: bool = True
    include_comparisons: bool = True
    
class TeamAnalyticsResponse(BaseModel):
    """Team analytics response schema."""
    team_id: Optional[UUID] = None
    team_name: Optional[str] = None
    period_start: date
    period_end: date
    summary_metrics: Dict[PerformanceMetric, float] = {}
    individual_performance: List[RecruiterPerformanceMetrics] = []
    trends: Dict[str, List[Dict[str, Any]]] = {}  # Time-series data
    comparisons: Dict[str, float] = {}  # vs previous period, vs company avg
    insights: List[str] = []
    recommendations: List[str] = []
    generated_at: datetime
    
class ManagerDashboard(BaseModel):
    """Manager dashboard data schema."""
    manager_id: str  # Clerk user ID
    teams_managed: List[TeamResponse] = []
    total_team_members: int = 0
    active_goals: int = 0
    overdue_goals: int = 0
    team_performance_summary: Dict[str, Any] = {}
    workload_alerts: List[Dict[str, Any]] = []
    recent_achievements: List[Dict[str, Any]] = []
    pending_approvals: int = 0
    upcoming_deadlines: List[Dict[str, Any]] = []
    key_metrics: Dict[PerformanceMetric, float] = {}
    last_updated: datetime