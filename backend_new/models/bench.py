from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric, Enum as SQLEnum, Table
from sqlalchemy.orm import relationship
from sqlalchemy import JSON
from datetime import datetime
from .base import BaseModel, AuditMixin, MetadataMixin
from .tenant import TenantAwareMixin
from ..schemas.base import BenchStatus, AvailabilityStatus, SalesStatus
from enum import Enum

# Association table for candidate skills on bench
candidate_bench_skills = Table(
    'candidate_bench_skills',
    BaseModel.metadata,
    Column('candidate_bench_id', Integer, ForeignKey('candidate_bench.id'), primary_key=True),
    Column('skill_id', Integer, ForeignKey('skills.id'), primary_key=True),
    Column('skill_level', String(20), nullable=False),  # beginner, intermediate, advanced, expert
    Column('years_experience', Integer, nullable=True),
    Column('is_primary', Boolean, default=False),
    Column('verified', Boolean, default=False)
)

# Association table for candidate certifications
candidate_certifications = Table(
    'candidate_certifications',
    BaseModel.metadata,
    Column('candidate_bench_id', Integer, ForeignKey('candidate_bench.id'), primary_key=True),
    Column('certification_id', Integer, ForeignKey('certifications.id'), primary_key=True),
    Column('obtained_date', DateTime, nullable=True),
    Column('expiry_date', DateTime, nullable=True),
    Column('is_active', Boolean, default=True)
)

class CandidateBench(BaseModel, AuditMixin, MetadataMixin, TenantAwareMixin):
    """Enhanced candidate model for bench management"""
    __tablename__ = 'candidate_bench'
    
    # Basic Information
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    profile_manager_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # Professional Details
    current_title = Column(String(200), nullable=False)
    experience_years = Column(Integer, nullable=False)
    current_salary = Column(Numeric(12, 2), nullable=True)
    expected_salary = Column(Numeric(12, 2), nullable=True)
    salary_currency = Column(String(3), default='USD', nullable=False)
    
    # Location and Availability
    current_location = Column(String(200), nullable=False)
    willing_to_relocate = Column(Boolean, default=False, nullable=False)
    preferred_locations = Column(JSON, nullable=True, default=[])  # List of preferred cities/states
    remote_work_preference = Column(String(50), nullable=False)  # remote, hybrid, onsite, flexible
    
    # Availability Status
    availability_status = Column(String(50), nullable=False, default='available')  # available, engaged, unavailable
    available_from = Column(DateTime, nullable=True)
    notice_period_days = Column(Integer, default=0, nullable=False)
    
    # Bench Status
    bench_status = Column(String(50), nullable=False, default='active')  # active, inactive, sold, archived
    bench_start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    bench_end_date = Column(DateTime, nullable=True)
    
    # Work Authorization
    work_authorization = Column(String(100), nullable=False)  # citizen, green_card, h1b, opt, etc.
    visa_status = Column(String(100), nullable=True)
    visa_expiry = Column(DateTime, nullable=True)
    
    # Education
    highest_education = Column(String(100), nullable=True)
    education_field = Column(String(200), nullable=True)
    university = Column(String(200), nullable=True)
    graduation_year = Column(Integer, nullable=True)
    
    # Professional Summary
    professional_summary = Column(Text, nullable=True)
    key_achievements = Column(JSON, nullable=True, default=[])  # List of achievements
    
    # Documents
    resume_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    
    # Sales Information
    hourly_rate = Column(Numeric(10, 2), nullable=True)
    markup_percentage = Column(Numeric(5, 2), nullable=True)  # Company markup
    client_rate = Column(Numeric(10, 2), nullable=True)  # Rate charged to client
    
    # Performance Metrics
    interview_success_rate = Column(Numeric(5, 2), nullable=True)  # Percentage
    placement_success_rate = Column(Numeric(5, 2), nullable=True)  # Percentage
    client_satisfaction_score = Column(Numeric(3, 2), nullable=True)  # 1-5 scale
    
    # Marketing Information
    marketing_approved = Column(Boolean, default=False, nullable=False)
    marketing_notes = Column(Text, nullable=True)
    unique_selling_points = Column(JSON, nullable=True, default=[])  # List of USPs
    
    # Internal Notes
    internal_notes = Column(Text, nullable=True)
    strengths = Column(JSON, nullable=True, default=[])  # List of strengths
    areas_for_improvement = Column(JSON, nullable=True, default=[])  # List of areas
    
    # Contact Preferences
    preferred_contact_method = Column(String(50), default='email', nullable=False)
    best_time_to_contact = Column(String(100), nullable=True)
    timezone = Column(String(50), default='UTC', nullable=False)
    
    # Relationships
    user = relationship('User', foreign_keys=[user_id], back_populates='candidate_bench_profile')
    profile_manager = relationship('User', foreign_keys=[profile_manager_id])
    skills = relationship('Skill', secondary=candidate_bench_skills, backref='bench_candidates')
    certifications = relationship('Certification', secondary=candidate_certifications, back_populates='candidates')
    
    # Sales and submissions
    submissions = relationship('CandidateSubmission', back_populates='candidate', cascade='all, delete-orphan')
    sales = relationship('CandidateSale', back_populates='candidate', cascade='all, delete-orphan')
    interviews = relationship('CandidateInterview', back_populates='candidate', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<CandidateBench(id={self.id}, user_id={self.user_id}, title='{self.current_title}', status='{self.bench_status}')>"
    
    @property
    def is_available(self):
        """Check if candidate is available for new opportunities"""
        return self.availability_status == 'available' and self.bench_status == 'active'
    
    @property
    def years_on_bench(self):
        """Calculate years on bench"""
        if self.bench_end_date:
            delta = self.bench_end_date - self.bench_start_date
        else:
            delta = datetime.utcnow() - self.bench_start_date
        return round(delta.days / 365.25, 2)
    
    @property
    def total_submissions(self):
        """Get total number of submissions"""
        return len(self.submissions)
    
    @property
    def successful_placements(self):
        """Get number of successful placements"""
        return len([s for s in self.sales if s.status == 'closed_won'])

class Certification(BaseModel, AuditMixin):
    """Certification model"""
    __tablename__ = 'certifications'
    
    name = Column(String(200), nullable=False, index=True)
    issuing_organization = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # technical, project_management, etc.
    
    # Validity
    is_active = Column(Boolean, default=True, nullable=False)
    requires_renewal = Column(Boolean, default=False, nullable=False)
    validity_period_months = Column(Integer, nullable=True)
    
    # External references
    external_id = Column(String(100), nullable=True)
    verification_url = Column(String(500), nullable=True)
    
    # Relationships
    candidates = relationship('CandidateBench', secondary=candidate_certifications, back_populates='certifications')
    
    def __repr__(self):
        return f"<Certification(id={self.id}, name='{self.name}', organization='{self.issuing_organization}')>"

class CandidateSubmission(BaseModel, AuditMixin, MetadataMixin):
    """Track candidate submissions to clients"""
    __tablename__ = 'candidate_submissions'
    
    # Foreign Keys
    candidate_id = Column(Integer, ForeignKey('candidate_bench.id'), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False, index=True)
    job_opportunity_id = Column(Integer, ForeignKey('job_opportunities.id'), nullable=True, index=True)
    submitted_by = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Submission Details
    submission_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    position_title = Column(String(200), nullable=False)
    client_rate = Column(Numeric(10, 2), nullable=True)
    duration_months = Column(Integer, nullable=True)
    
    # Status Tracking
    status = Column(String(50), nullable=False, default='submitted')  # submitted, shortlisted, interviewed, selected, rejected
    status_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Client Feedback
    client_feedback = Column(Text, nullable=True)
    rejection_reason = Column(String(200), nullable=True)
    
    # Interview Information
    interview_scheduled = Column(Boolean, default=False, nullable=False)
    interview_date = Column(DateTime, nullable=True)
    interview_feedback = Column(Text, nullable=True)
    
    # Internal Notes
    submission_notes = Column(Text, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)
    
    # Relationships
    candidate = relationship('CandidateBench', back_populates='submissions')
    client = relationship('Client', back_populates='submissions')
    job_opportunity = relationship('JobOpportunity', back_populates='submissions')
    submitter = relationship('User', foreign_keys=[submitted_by])
    
    def __repr__(self):
        return f"<CandidateSubmission(id={self.id}, candidate_id={self.candidate_id}, client_id={self.client_id}, status='{self.status}')>"

class CandidateSale(BaseModel, AuditMixin, MetadataMixin):
    """Track successful candidate sales/placements"""
    __tablename__ = 'candidate_sales'
    
    # Foreign Keys
    candidate_id = Column(Integer, ForeignKey('candidate_bench.id'), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey('candidate_submissions.id'), nullable=True, index=True)
    sales_person_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Sale Details
    sale_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # For contract positions
    
    # Financial Details
    hourly_rate = Column(Numeric(10, 2), nullable=False)
    markup_percentage = Column(Numeric(5, 2), nullable=False)
    gross_margin = Column(Numeric(10, 2), nullable=False)  # Calculated margin
    
    # Contract Details
    contract_type = Column(String(50), nullable=False)  # contract, permanent, contract_to_hire
    duration_months = Column(Integer, nullable=True)
    hours_per_week = Column(Integer, default=40, nullable=False)
    
    # Status
    status = Column(String(50), nullable=False, default='active')  # active, completed, terminated, extended
    
    # Performance Tracking
    client_satisfaction_score = Column(Numeric(3, 2), nullable=True)  # 1-5 scale
    renewal_probability = Column(Numeric(3, 2), nullable=True)  # 0-1 scale
    
    # Revenue Tracking
    total_revenue = Column(Numeric(12, 2), nullable=True)  # Total revenue generated
    commission_percentage = Column(Numeric(5, 2), nullable=True)
    commission_amount = Column(Numeric(10, 2), nullable=True)
    
    # Relationships
    candidate = relationship('CandidateBench', back_populates='sales')
    client = relationship('Client', back_populates='sales')
    submission = relationship('CandidateSubmission')
    sales_person = relationship('User', foreign_keys=[sales_person_id])
    
    def __repr__(self):
        return f"<CandidateSale(id={self.id}, candidate_id={self.candidate_id}, client_id={self.client_id}, status='{self.status}')>"
    
    @property
    def monthly_revenue(self):
        """Calculate monthly revenue"""
        if self.hourly_rate and self.hours_per_week:
            weekly_revenue = self.hourly_rate * self.hours_per_week
            return weekly_revenue * 4.33  # Average weeks per month
        return 0

class CandidateInterview(BaseModel, AuditMixin):
    """Track candidate interviews"""
    __tablename__ = 'candidate_interviews'
    
    # Foreign Keys
    candidate_id = Column(Integer, ForeignKey('candidate_bench.id'), nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey('candidate_submissions.id'), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False, index=True)
    
    # Interview Details
    interview_date = Column(DateTime, nullable=False)
    interview_type = Column(String(50), nullable=False)  # phone, video, in_person, technical
    duration_minutes = Column(Integer, nullable=True)
    
    # Participants
    interviewer_name = Column(String(200), nullable=True)
    interviewer_title = Column(String(200), nullable=True)
    interviewer_email = Column(String(255), nullable=True)
    
    # Feedback
    overall_rating = Column(Integer, nullable=True)  # 1-10 scale
    technical_rating = Column(Integer, nullable=True)
    communication_rating = Column(Integer, nullable=True)
    cultural_fit_rating = Column(Integer, nullable=True)
    
    # Detailed Feedback
    strengths = Column(JSON, nullable=True, default=[])
    weaknesses = Column(JSON, nullable=True, default=[])
    detailed_feedback = Column(Text, nullable=True)
    
    # Outcome
    recommendation = Column(String(50), nullable=True)  # hire, reject, maybe, next_round
    next_steps = Column(Text, nullable=True)
    
    # Status
    status = Column(String(50), nullable=False, default='scheduled')  # scheduled, completed, cancelled, rescheduled
    
    # Relationships
    candidate = relationship('CandidateBench', back_populates='interviews')
    submission = relationship('CandidateSubmission')
    client = relationship('Client')
    
    def __repr__(self):
        return f"<CandidateInterview(id={self.id}, candidate_id={self.candidate_id}, date={self.interview_date}, status='{self.status}')>"