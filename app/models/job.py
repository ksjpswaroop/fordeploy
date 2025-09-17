from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Table, Numeric, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy import JSON
from datetime import datetime
from .base import BaseModel as SQLBaseModel, AuditMixin, MetadataMixin, Base
from ..schemas.base import JobStatus, ExperienceLevel, SkillLevel
from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional

# Association table for job skills (many-to-many)
job_skills = Table(
    'job_skills',
    Base.metadata,
    Column('job_id', Integer, ForeignKey('jobs.id'), primary_key=True),
    Column('skill_id', Integer, ForeignKey('skills.id'), primary_key=True),
    Column('skill_level', SQLEnum(SkillLevel), nullable=False),
    Column('is_required', Boolean, default=True),
    Column('weight', Integer, default=1)  # Importance weight for matching
)

# Association table for job departments (many-to-many)
job_departments = Table(
    'job_departments',
    Base.metadata,
    Column('job_id', Integer, ForeignKey('jobs.id'), primary_key=True),
    Column('department_id', Integer, ForeignKey('departments.id'), primary_key=True),
    Column('is_primary', Boolean, default=False)
)

# Association table for saved jobs by candidates
saved_jobs = Table(
    'saved_jobs',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('job_id', Integer, ForeignKey('jobs.id'), primary_key=True),
    Column('saved_at', DateTime(timezone=True), default=datetime.utcnow),
    Column('notes', Text, nullable=True)
)

class Job(SQLBaseModel, AuditMixin, MetadataMixin):
    """Job model"""
    __tablename__ = 'jobs'
    
    # Basic information
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)  # Short summary for listings
    
    # Job details
    job_type = Column(String(50), nullable=False)  # full-time, part-time, contract, internship
    work_mode = Column(String(50), nullable=False)  # remote, hybrid, onsite
    experience_level = Column(SQLEnum(ExperienceLevel), nullable=False)
    
    # Location
    location_city = Column(String(100), nullable=True)
    location_state = Column(String(100), nullable=True)
    location_country = Column(String(100), nullable=False)
    is_remote = Column(Boolean, default=False, nullable=False)
    remote_policy = Column(String(100), nullable=True)  # fully-remote, hybrid, occasional
    
    # Compensation
    salary_min = Column(Numeric(12, 2), nullable=True)
    salary_max = Column(Numeric(12, 2), nullable=True)
    salary_currency = Column(String(3), default='USD', nullable=False)
    salary_period = Column(String(20), default='yearly', nullable=False)  # yearly, monthly, hourly
    
    # Benefits and perks
    benefits = Column(JSON, nullable=True, default=[])  # List of benefits
    perks = Column(JSON, nullable=True, default=[])  # List of perks
    
    # Requirements
    requirements = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    qualifications = Column(Text, nullable=True)
    
    # Education requirements
    education_level = Column(String(50), nullable=True)  # high-school, bachelor, master, phd
    education_field = Column(String(100), nullable=True)
    
    # Experience requirements
    min_experience_years = Column(Integer, default=0, nullable=False)
    max_experience_years = Column(Integer, nullable=True)
    
    # Job status and lifecycle
    status = Column(SQLEnum(JobStatus), default=JobStatus.DRAFT, nullable=False)
    priority = Column(String(20), default='medium', nullable=False)  # low, medium, high, urgent
    
    # Publishing and visibility
    is_published = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Application settings
    application_deadline = Column(DateTime(timezone=True), nullable=True)
    max_applications = Column(Integer, nullable=True)
    auto_reject_after_deadline = Column(Boolean, default=False, nullable=False)
    
    # Screening questions
    screening_questions = Column(JSON, nullable=True, default=[])  # List of questions
    
    # SEO and marketing
    seo_title = Column(String(200), nullable=True)
    seo_description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # SEO keywords - store as JSON array
    
    # Analytics and tracking
    view_count = Column(Integer, default=0, nullable=False)
    application_count = Column(Integer, default=0, nullable=False)
    
    # Hiring process
    hiring_process = Column(JSON, nullable=True, default={})  # Custom hiring workflow
    interview_process = Column(JSON, nullable=True, default=[])  # Interview stages
    
    # External integrations
    external_job_id = Column(String(100), nullable=True)  # For job board integrations
    source = Column(String(100), nullable=True)  # Where the job was created from
    
    # Relationships
    creator = relationship(
        'User',
        primaryjoin="User.id==Job.created_by",
        foreign_keys="Job.created_by",
        back_populates='created_jobs'
    )
    recruiter = relationship('User', foreign_keys='Job.recruiter_id')
    hiring_manager = relationship('User', foreign_keys='Job.hiring_manager_id')
    
    # Job-specific foreign keys
    recruiter_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    hiring_manager_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True, index=True)
    
    # Many-to-many relationships
    skills = relationship('Skill', secondary=job_skills, back_populates='jobs')
    departments = relationship('Department', secondary=job_departments, back_populates='jobs')
    saved_by_users = relationship('User', secondary=saved_jobs)
    
    # One-to-many relationships
    applications = relationship('Application', back_populates='job', cascade='all, delete-orphan')
    interviews = relationship('Interview', back_populates='job')
    # Backref for analytics (defined in JobAnalytics)
    analytics = relationship('JobAnalytics', back_populates='job', uselist=False)
    
    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', status='{self.status}')>"
    
    @property
    def is_active(self):
        """Check if job is active and accepting applications"""
        if not self.is_published or self.status != JobStatus.ACTIVE:
            return False
        
        now = datetime.utcnow()
        if self.expires_at and now > self.expires_at:
            return False
        
        if self.application_deadline and now > self.application_deadline:
            return False
        
        if self.max_applications and self.application_count >= self.max_applications:
            return False
        
        return True
    
    @property
    def salary_range_display(self):
        """Get formatted salary range"""
        if self.salary_min and self.salary_max:
            return f"{self.salary_currency} {self.salary_min:,.0f} - {self.salary_max:,.0f} {self.salary_period}"
        elif self.salary_min:
            return f"{self.salary_currency} {self.salary_min:,.0f}+ {self.salary_period}"
        elif self.salary_max:
            return f"Up to {self.salary_currency} {self.salary_max:,.0f} {self.salary_period}"
        return "Salary not specified"
    
    @property
    def location_display(self):
        """Get formatted location"""
        if self.is_remote:
            return "Remote"
        
        parts = []
        if self.location_city:
            parts.append(self.location_city)
        if self.location_state:
            parts.append(self.location_state)
        if self.location_country:
            parts.append(self.location_country)
        
        return ", ".join(parts) if parts else "Location not specified"
    
    def increment_view_count(self):
        """Increment job view count"""
        self.view_count += 1
    
    def increment_application_count(self):
        """Increment application count"""
        self.application_count += 1

class Department(SQLBaseModel, AuditMixin):
    """Department model"""
    __tablename__ = 'departments'
    
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    code = Column(String(20), unique=True, nullable=True)  # Department code
    
    # Hierarchy
    parent_id = Column(Integer, ForeignKey('departments.id', use_alter=True), nullable=True)
    level = Column(Integer, default=0, nullable=False)
    
    # Department head
    head_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    budget = Column(Numeric(12, 2), nullable=True)
    
    # Relationships
    parent = relationship('Department', remote_side='Department.id', back_populates='children')
    children = relationship('Department', back_populates='parent')
    head = relationship('User', foreign_keys=[head_id])
    jobs = relationship('Job', secondary=job_departments, back_populates='departments')
    
    def __repr__(self):
        return f"<Department(id={self.id}, name='{self.name}')>"

class Skill(SQLBaseModel, AuditMixin):
    """Skill model"""
    __tablename__ = 'skills'
    
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # technical, soft, language, etc.
    
    # Skill metadata
    is_verified = Column(Boolean, default=False, nullable=False)
    popularity_score = Column(Integer, default=0, nullable=False)
    
    # External references
    external_id = Column(String(100), nullable=True)  # For skill databases
    synonyms = Column(JSON, nullable=True)  # Alternative names - store as JSON array
    
    # Relationships
    jobs = relationship('Job', secondary=job_skills, back_populates='skills')
    
    def __repr__(self):
        return f"<Skill(id={self.id}, name='{self.name}')>"

class JobTemplate(SQLBaseModel, AuditMixin):
    """Job template model for reusable job postings"""
    __tablename__ = 'job_templates'
    
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Template data (JSON structure matching Job model)
    template_data = Column(JSON, nullable=False)
    
    # Template metadata
    category = Column(String(100), nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    
    def __repr__(self):
        return f"<JobTemplate(id={self.id}, name='{self.name}')>"
    
    def create_job_from_template(self, **overrides):
        """Create a new job from this template"""
        job_data = self.template_data.copy()
        job_data.update(overrides)
        return Job(**job_data)

class JobView(SQLBaseModel):
    """Job view tracking model"""
    __tablename__ = 'job_views'
    
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # Null for anonymous views
    
    # View metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    referrer = Column(String(500), nullable=True)
    
    # Geographic data
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Session data
    session_id = Column(String(255), nullable=True)
    view_duration = Column(Integer, nullable=True)  # Seconds spent viewing
    
    # Relationships
    job = relationship('Job')
    user = relationship('User')
    
    def __repr__(self):
        return f"<JobView(id={self.id}, job_id={self.job_id}, user_id={self.user_id})>"

class JobBase(PydanticBaseModel):
    """Base job model with common fields."""
    job_id: str
    job_title: str 
    company_name: str
    location: Optional[str] = None
    description_html: Optional[str] = None
    
class JobCreate(JobBase):
    """Job data for creating a new job record."""
    poster_name: Optional[str] = None
    poster_profile_url: Optional[str] = None
    raw_json: Dict[str, Any] = {}

class JobEnriched(JobBase):
    """Job with enriched contact information."""
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_linkedin: Optional[str] = None
class JobAnalysis(PydanticBaseModel):
    """OpenAI analysis of job match."""
    overall_match_score: float
    match_threshold_met: bool
    matching_criteria: Dict[str, List[str]]
    missing_criteria: Dict[str, List[str]]
    recommendations: Dict[str, List[str]]
class JobWithAnalysis(JobBase):
    """Job with matching analysis."""
    analysis: JobAnalysis

class JobSchema(PydanticBaseModel):
    """Job schema for API responses."""
    title: str
    # ...other fields...
    analysis: JobAnalysis
    
    # Pydantic v2 config
    model_config = ConfigDict(from_attributes=True)