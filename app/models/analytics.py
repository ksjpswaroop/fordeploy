from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric, Date, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy import JSON
from datetime import datetime, date
from .base import BaseModel, AuditMixin, MetadataMixin
from ..schemas.base import Priority

class RecruitmentMetric(BaseModel, AuditMixin):
    """Core recruitment metrics tracking"""
    __tablename__ = 'recruitment_metrics'
    
    # Time period
    date = Column(Date, nullable=False, index=True)
    period_type = Column(String(20), default='daily', nullable=False)  # daily, weekly, monthly, quarterly
    
    # Scope
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True, index=True)
    recruiter_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # Application metrics
    applications_received = Column(Integer, default=0, nullable=False)
    applications_screened = Column(Integer, default=0, nullable=False)
    applications_rejected = Column(Integer, default=0, nullable=False)
    applications_advanced = Column(Integer, default=0, nullable=False)
    
    # Interview metrics
    interviews_scheduled = Column(Integer, default=0, nullable=False)
    interviews_completed = Column(Integer, default=0, nullable=False)
    interviews_cancelled = Column(Integer, default=0, nullable=False)
    interviews_no_show = Column(Integer, default=0, nullable=False)
    
    # Hiring metrics
    offers_made = Column(Integer, default=0, nullable=False)
    offers_accepted = Column(Integer, default=0, nullable=False)
    offers_rejected = Column(Integer, default=0, nullable=False)
    hires_completed = Column(Integer, default=0, nullable=False)
    
    # Time metrics (in days)
    avg_time_to_screen = Column(Numeric(10, 2), nullable=True)
    avg_time_to_interview = Column(Numeric(10, 2), nullable=True)
    avg_time_to_offer = Column(Numeric(10, 2), nullable=True)
    avg_time_to_hire = Column(Numeric(10, 2), nullable=True)
    
    # Quality metrics
    avg_candidate_rating = Column(Numeric(3, 2), nullable=True)  # 1-10 scale
    avg_interview_rating = Column(Numeric(3, 2), nullable=True)
    candidate_satisfaction = Column(Numeric(3, 2), nullable=True)
    
    # Source metrics
    source_breakdown = Column(JSON, nullable=True, default={})  # Source -> count mapping
    
    # Cost metrics
    total_cost = Column(Numeric(12, 2), nullable=True)
    cost_per_hire = Column(Numeric(10, 2), nullable=True)
    cost_per_application = Column(Numeric(8, 2), nullable=True)
    
    # Relationships
    job = relationship('Job')
    department = relationship('Department')
    recruiter = relationship('User', foreign_keys=[recruiter_id])
    
    def __repr__(self):
        return f"<RecruitmentMetric(id={self.id}, date='{self.date}', period='{self.period_type}')>"
    
    @property
    def conversion_rate_screen_to_interview(self):
        """Calculate screen to interview conversion rate"""
        if self.applications_screened > 0:
            return (self.interviews_scheduled / self.applications_screened) * 100
        return 0
    
    @property
    def conversion_rate_interview_to_offer(self):
        """Calculate interview to offer conversion rate"""
        if self.interviews_completed > 0:
            return (self.offers_made / self.interviews_completed) * 100
        return 0
    
    @property
    def offer_acceptance_rate(self):
        """Calculate offer acceptance rate"""
        if self.offers_made > 0:
            return (self.offers_accepted / self.offers_made) * 100
        return 0
    
    @property
    def overall_conversion_rate(self):
        """Calculate overall application to hire conversion rate"""
        if self.applications_received > 0:
            return (self.hires_completed / self.applications_received) * 100
        return 0

class JobAnalytics(BaseModel, AuditMixin):
    """Job-specific analytics"""
    __tablename__ = 'job_analytics'
    
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False, unique=True, index=True)
    
    # View and engagement metrics
    total_views = Column(Integer, default=0, nullable=False)
    unique_views = Column(Integer, default=0, nullable=False)
    avg_time_on_page = Column(Integer, nullable=True)  # seconds
    bounce_rate = Column(Numeric(5, 2), nullable=True)  # percentage
    
    # Application metrics
    total_applications = Column(Integer, default=0, nullable=False)
    qualified_applications = Column(Integer, default=0, nullable=False)
    application_completion_rate = Column(Numeric(5, 2), nullable=True)
    
    # Source tracking
    traffic_sources = Column(JSON, nullable=True, default={})  # Source -> views mapping
    application_sources = Column(JSON, nullable=True, default={})  # Source -> applications mapping
    
    # Geographic data
    view_locations = Column(JSON, nullable=True, default={})  # Country/city -> count
    application_locations = Column(JSON, nullable=True, default={})  # Country/city -> count
    
    # Device and browser data
    device_breakdown = Column(JSON, nullable=True, default={})  # Device type -> count
    browser_breakdown = Column(JSON, nullable=True, default={})  # Browser -> count
    
    # Performance metrics
    search_ranking_avg = Column(Numeric(5, 2), nullable=True)
    click_through_rate = Column(Numeric(5, 2), nullable=True)
    
    # Time-based metrics
    peak_viewing_hours = Column(JSON, nullable=True, default={})  # Hour -> view count
    peak_application_days = Column(JSON, nullable=True, default={})  # Day -> application count
    
    # Competitive analysis
    similar_jobs_count = Column(Integer, nullable=True)
    market_competitiveness = Column(String(20), nullable=True)  # low, medium, high
    
    # Last updated
    last_calculated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    job = relationship('Job', back_populates='analytics')
    
    def __repr__(self):
        return f"<JobAnalytics(id={self.id}, job_id={self.job_id}, views={self.total_views})>"
    
    @property
    def view_to_application_rate(self):
        """Calculate view to application conversion rate"""
        if self.total_views > 0:
            return (self.total_applications / self.total_views) * 100
        return 0
    
    @property
    def qualification_rate(self):
        """Calculate application qualification rate"""
        if self.total_applications > 0:
            return (self.qualified_applications / self.total_applications) * 100
        return 0

class CandidateAnalytics(BaseModel, AuditMixin):
    """Candidate behavior and engagement analytics"""
    __tablename__ = 'candidate_analytics'
    
    candidate_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True, index=True)
    
    # Engagement metrics
    total_logins = Column(Integer, default=0, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    avg_session_duration = Column(Integer, nullable=True)  # minutes
    total_time_spent = Column(Integer, default=0, nullable=False)  # minutes
    
    # Job search behavior
    jobs_viewed = Column(Integer, default=0, nullable=False)
    jobs_saved = Column(Integer, default=0, nullable=False)
    searches_performed = Column(Integer, default=0, nullable=False)
    search_terms = Column(JSON, nullable=True, default=[])  # Most common search terms
    
    # Application behavior
    applications_started = Column(Integer, default=0, nullable=False)
    applications_completed = Column(Integer, default=0, nullable=False)
    applications_withdrawn = Column(Integer, default=0, nullable=False)
    avg_application_time = Column(Integer, nullable=True)  # minutes
    
    # Profile completeness
    profile_completion_score = Column(Integer, default=0, nullable=False)  # 0-100
    resume_uploaded = Column(Boolean, default=False, nullable=False)
    profile_views_by_recruiters = Column(Integer, default=0, nullable=False)
    
    # Communication metrics
    messages_sent = Column(Integer, default=0, nullable=False)
    messages_received = Column(Integer, default=0, nullable=False)
    response_rate = Column(Numeric(5, 2), nullable=True)  # percentage
    avg_response_time = Column(Integer, nullable=True)  # hours
    
    # Interview metrics
    interviews_attended = Column(Integer, default=0, nullable=False)
    interviews_missed = Column(Integer, default=0, nullable=False)
    avg_interview_rating = Column(Numeric(3, 2), nullable=True)
    
    # Preferences and behavior patterns
    preferred_job_types = Column(JSON, nullable=True, default=[])  # Most applied job types
    preferred_locations = Column(JSON, nullable=True, default=[])  # Most searched locations
    salary_expectations = Column(JSON, nullable=True, default={})  # Min/max/avg expectations
    
    # Device and access patterns
    device_usage = Column(JSON, nullable=True, default={})  # Device type usage
    access_times = Column(JSON, nullable=True, default={})  # Peak usage hours
    
    # Success metrics
    offers_received = Column(Integer, default=0, nullable=False)
    offers_accepted = Column(Integer, default=0, nullable=False)
    current_application_status = Column(String(50), nullable=True)
    
    # Relationships
    candidate = relationship('User', foreign_keys=[candidate_id])
    
    def __repr__(self):
        return f"<CandidateAnalytics(id={self.id}, candidate_id={self.candidate_id}, logins={self.total_logins})>"
    
    @property
    def application_completion_rate(self):
        """Calculate application completion rate"""
        if self.applications_started > 0:
            return (self.applications_completed / self.applications_started) * 100
        return 0
    
    @property
    def interview_attendance_rate(self):
        """Calculate interview attendance rate"""
        total_interviews = self.interviews_attended + self.interviews_missed
        if total_interviews > 0:
            return (self.interviews_attended / total_interviews) * 100
        return 0
    
    @property
    def engagement_score(self):
        """Calculate overall engagement score (0-100)"""
        score = 0
        
        # Login frequency (0-25 points)
        if self.total_logins > 0:
            score += min(25, self.total_logins * 2)
        
        # Profile completeness (0-25 points)
        score += (self.profile_completion_score * 25) / 100
        
        # Application activity (0-25 points)
        if self.applications_completed > 0:
            score += min(25, self.applications_completed * 5)
        
        # Communication activity (0-25 points)
        if self.response_rate:
            score += (self.response_rate * 25) / 100
        
        return min(100, score)

class RecruiterPerformance(BaseModel, AuditMixin):
    """Recruiter performance metrics"""
    __tablename__ = 'recruiter_performance'
    
    recruiter_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    period_type = Column(String(20), default='monthly', nullable=False)
    
    # Activity metrics
    jobs_posted = Column(Integer, default=0, nullable=False)
    applications_reviewed = Column(Integer, default=0, nullable=False)
    candidates_contacted = Column(Integer, default=0, nullable=False)
    interviews_conducted = Column(Integer, default=0, nullable=False)
    
    # Performance metrics
    hires_made = Column(Integer, default=0, nullable=False)
    positions_filled = Column(Integer, default=0, nullable=False)
    avg_time_to_fill = Column(Numeric(10, 2), nullable=True)  # days
    avg_cost_per_hire = Column(Numeric(10, 2), nullable=True)
    
    # Quality metrics
    candidate_satisfaction_avg = Column(Numeric(3, 2), nullable=True)
    hiring_manager_satisfaction_avg = Column(Numeric(3, 2), nullable=True)
    offer_acceptance_rate = Column(Numeric(5, 2), nullable=True)
    
    # Efficiency metrics
    applications_per_hire = Column(Numeric(8, 2), nullable=True)
    interviews_per_hire = Column(Numeric(6, 2), nullable=True)
    response_time_hours = Column(Numeric(8, 2), nullable=True)
    
    # Pipeline metrics
    pipeline_conversion_rate = Column(Numeric(5, 2), nullable=True)
    source_effectiveness = Column(JSON, nullable=True, default={})  # Source -> conversion rate
    
    # Goal tracking
    monthly_hire_goal = Column(Integer, nullable=True)
    goal_achievement_rate = Column(Numeric(5, 2), nullable=True)
    
    # Workload metrics
    active_positions = Column(Integer, default=0, nullable=False)
    avg_positions_per_month = Column(Numeric(6, 2), nullable=True)
    workload_score = Column(Integer, nullable=True)  # 1-10 scale
    
    # Relationships
    recruiter = relationship('User', foreign_keys=[recruiter_id])
    
    def __repr__(self):
        return f"<RecruiterPerformance(id={self.id}, recruiter_id={self.recruiter_id}, period='{self.period_start}' to '{self.period_end}')>"
    
    @property
    def hire_rate(self):
        """Calculate hire rate from applications"""
        if self.applications_reviewed > 0:
            return (self.hires_made / self.applications_reviewed) * 100
        return 0
    
    @property
    def productivity_score(self):
        """Calculate overall productivity score (0-100)"""
        score = 0
        
        # Hire achievement (0-40 points)
        if self.monthly_hire_goal and self.monthly_hire_goal > 0:
            achievement = min(100, (self.hires_made / self.monthly_hire_goal) * 100)
            score += (achievement * 40) / 100
        
        # Time efficiency (0-30 points)
        if self.avg_time_to_fill:
            # Assume 30 days is baseline, less is better
            efficiency = max(0, 100 - ((self.avg_time_to_fill - 30) * 2))
            score += (efficiency * 30) / 100
        
        # Quality metrics (0-30 points)
        if self.offer_acceptance_rate:
            score += (self.offer_acceptance_rate * 30) / 100
        
        return min(100, score)

class PipelineAnalytics(BaseModel, AuditMixin):
    """Recruitment pipeline analytics"""
    __tablename__ = 'pipeline_analytics'
    
    # Time period
    date = Column(Date, nullable=False, index=True)
    
    # Scope
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True, index=True)
    
    # Pipeline stage counts
    stage_applied = Column(Integer, default=0, nullable=False)
    stage_screening = Column(Integer, default=0, nullable=False)
    stage_phone_screen = Column(Integer, default=0, nullable=False)
    stage_technical_interview = Column(Integer, default=0, nullable=False)
    stage_onsite_interview = Column(Integer, default=0, nullable=False)
    stage_final_interview = Column(Integer, default=0, nullable=False)
    stage_reference_check = Column(Integer, default=0, nullable=False)
    stage_offer = Column(Integer, default=0, nullable=False)
    stage_hired = Column(Integer, default=0, nullable=False)
    stage_rejected = Column(Integer, default=0, nullable=False)
    stage_withdrawn = Column(Integer, default=0, nullable=False)
    
    # Stage conversion rates
    conversion_applied_to_screening = Column(Numeric(5, 2), nullable=True)
    conversion_screening_to_phone = Column(Numeric(5, 2), nullable=True)
    conversion_phone_to_technical = Column(Numeric(5, 2), nullable=True)
    conversion_technical_to_onsite = Column(Numeric(5, 2), nullable=True)
    conversion_onsite_to_final = Column(Numeric(5, 2), nullable=True)
    conversion_final_to_offer = Column(Numeric(5, 2), nullable=True)
    conversion_offer_to_hire = Column(Numeric(5, 2), nullable=True)
    
    # Time in stage (average days)
    time_in_screening = Column(Numeric(8, 2), nullable=True)
    time_in_phone_screen = Column(Numeric(8, 2), nullable=True)
    time_in_technical = Column(Numeric(8, 2), nullable=True)
    time_in_onsite = Column(Numeric(8, 2), nullable=True)
    time_in_final = Column(Numeric(8, 2), nullable=True)
    time_in_reference = Column(Numeric(8, 2), nullable=True)
    time_in_offer = Column(Numeric(8, 2), nullable=True)
    
    # Bottleneck analysis
    bottleneck_stage = Column(String(50), nullable=True)
    bottleneck_severity = Column(String(20), nullable=True)  # low, medium, high, critical
    
    # Relationships
    job = relationship('Job')
    department = relationship('Department')
    
    def __repr__(self):
        return f"<PipelineAnalytics(id={self.id}, date='{self.date}', job_id={self.job_id})>"
    
    @property
    def total_active_candidates(self):
        """Get total candidates in pipeline"""
        return (self.stage_applied + self.stage_screening + self.stage_phone_screen +
                self.stage_technical_interview + self.stage_onsite_interview +
                self.stage_final_interview + self.stage_reference_check + self.stage_offer)
    
    @property
    def overall_conversion_rate(self):
        """Calculate overall pipeline conversion rate"""
        if self.stage_applied > 0:
            return (self.stage_hired / self.stage_applied) * 100
        return 0

class DiversityMetrics(BaseModel, AuditMixin):
    """Diversity and inclusion metrics"""
    __tablename__ = 'diversity_metrics'
    
    # Time period
    date = Column(Date, nullable=False, index=True)
    period_type = Column(String(20), default='monthly', nullable=False)
    
    # Scope
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True, index=True)
    
    # Gender metrics
    applications_male = Column(Integer, default=0, nullable=False)
    applications_female = Column(Integer, default=0, nullable=False)
    applications_non_binary = Column(Integer, default=0, nullable=False)
    applications_undisclosed_gender = Column(Integer, default=0, nullable=False)
    
    hires_male = Column(Integer, default=0, nullable=False)
    hires_female = Column(Integer, default=0, nullable=False)
    hires_non_binary = Column(Integer, default=0, nullable=False)
    hires_undisclosed_gender = Column(Integer, default=0, nullable=False)
    
    # Ethnicity metrics (following EEOC categories)
    applications_by_ethnicity = Column(JSON, nullable=True, default={})
    hires_by_ethnicity = Column(JSON, nullable=True, default={})
    
    # Age group metrics
    applications_by_age_group = Column(JSON, nullable=True, default={})
    hires_by_age_group = Column(JSON, nullable=True, default={})
    
    # Education background
    applications_by_education = Column(JSON, nullable=True, default={})
    hires_by_education = Column(JSON, nullable=True, default={})
    
    # Geographic diversity
    applications_by_location = Column(JSON, nullable=True, default={})
    hires_by_location = Column(JSON, nullable=True, default={})
    
    # Veteran status
    applications_veterans = Column(Integer, default=0, nullable=False)
    hires_veterans = Column(Integer, default=0, nullable=False)
    
    # Disability status
    applications_with_disabilities = Column(Integer, default=0, nullable=False)
    hires_with_disabilities = Column(Integer, default=0, nullable=False)
    
    # Diversity scores (0-100)
    gender_diversity_score = Column(Numeric(5, 2), nullable=True)
    ethnic_diversity_score = Column(Numeric(5, 2), nullable=True)
    overall_diversity_score = Column(Numeric(5, 2), nullable=True)
    
    # Inclusion metrics
    avg_interview_rating_by_gender = Column(JSON, nullable=True, default={})
    avg_interview_rating_by_ethnicity = Column(JSON, nullable=True, default={})
    
    # Relationships
    job = relationship('Job')
    department = relationship('Department')
    
    def __repr__(self):
        return f"<DiversityMetrics(id={self.id}, date='{self.date}', period='{self.period_type}')>"
    
    @property
    def total_applications(self):
        """Get total applications"""
        return (self.applications_male + self.applications_female + 
                self.applications_non_binary + self.applications_undisclosed_gender)
    
    @property
    def total_hires(self):
        """Get total hires"""
        return (self.hires_male + self.hires_female + 
                self.hires_non_binary + self.hires_undisclosed_gender)
    
    @property
    def female_hire_rate(self):
        """Calculate female hire rate"""
        if self.applications_female > 0:
            return (self.hires_female / self.applications_female) * 100
        return 0
    
    @property
    def male_hire_rate(self):
        """Calculate male hire rate"""
        if self.applications_male > 0:
            return (self.hires_male / self.applications_male) * 100
        return 0

class CustomMetric(BaseModel, AuditMixin, MetadataMixin):
    """Custom metrics defined by users"""
    __tablename__ = 'custom_metrics'
    
    # Metric definition
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    metric_type = Column(String(50), nullable=False)  # count, percentage, average, sum
    
    # Calculation
    calculation_formula = Column(Text, nullable=False)  # SQL or formula
    data_source = Column(String(100), nullable=False)  # Table or view name
    filters = Column(JSON, nullable=True, default={})  # Additional filters
    
    # Display
    display_format = Column(String(50), default='number', nullable=False)  # number, percentage, currency
    decimal_places = Column(Integer, default=2, nullable=False)
    
    # Categorization
    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)  # Store as JSON array
    
    # Access control
    is_public = Column(Boolean, default=False, nullable=False)
    allowed_roles = Column(JSON, nullable=True)  # Store as JSON array
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_calculated_at = Column(DateTime(timezone=True), nullable=True)
    calculation_frequency = Column(String(20), default='daily', nullable=False)
    
    def __repr__(self):
        return f"<CustomMetric(id={self.id}, name='{self.name}', type='{self.metric_type}')>"

class MetricValue(BaseModel):
    """Calculated values for custom metrics"""
    __tablename__ = 'metric_values'
    
    metric_id = Column(Integer, ForeignKey('custom_metrics.id'), nullable=False, index=True)
    
    # Time and scope
    date = Column(Date, nullable=False, index=True)
    scope_type = Column(String(50), nullable=True)  # global, job, department, recruiter
    scope_id = Column(Integer, nullable=True)  # ID of the scoped entity
    
    # Value
    value = Column(Numeric(20, 6), nullable=False)
    formatted_value = Column(String(100), nullable=True)  # Formatted for display
    
    # Context
    calculation_context = Column(JSON, nullable=True, default={})  # Additional context data
    
    # Relationships
    metric = relationship('CustomMetric')
    
    def __repr__(self):
        return f"<MetricValue(id={self.id}, metric_id={self.metric_id}, date='{self.date}', value={self.value})>"

class Report(BaseModel, AuditMixin, MetadataMixin):
    """Generated reports"""
    __tablename__ = 'reports'
    
    # Report details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(String(100), nullable=False)  # recruitment_summary, diversity_report, etc.
    
    # Generation
    generated_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    generated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Scope and filters
    filters = Column(JSON, nullable=True, default={})
    scope = Column(JSON, nullable=True, default={})  # Jobs, departments, etc.
    
    # Content
    data = Column(JSON, nullable=False, default={})  # Report data
    charts = Column(JSON, nullable=True, default=[])  # Chart configurations
    
    # File output
    file_path = Column(String(500), nullable=True)
    file_format = Column(String(20), nullable=True)  # pdf, excel, csv
    file_size_bytes = Column(Integer, nullable=True)
    
    # Status
    status = Column(String(50), default='completed', nullable=False)  # generating, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Sharing and access
    is_public = Column(Boolean, default=False, nullable=False)
    shared_with = Column(JSON, nullable=True)  # User IDs as JSON array
    access_token = Column(String(255), nullable=True)  # For public sharing
    
    # Scheduling
    is_scheduled = Column(Boolean, default=False, nullable=False)
    schedule_frequency = Column(String(20), nullable=True)  # daily, weekly, monthly
    next_generation_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    generator = relationship('User', foreign_keys=[generated_by])
    
    def __repr__(self):
        return f"<Report(id={self.id}, name='{self.name}', type='{self.report_type}', status='{self.status}')>"
    
    @property
    def file_size_display(self):
        """Get formatted file size"""
        if self.file_size_bytes:
            if self.file_size_bytes < 1024:
                return f"{self.file_size_bytes} B"
            elif self.file_size_bytes < 1024 * 1024:
                return f"{self.file_size_bytes / 1024:.1f} KB"
            else:
                return f"{self.file_size_bytes / (1024 * 1024):.1f} MB"
        return "Unknown"