from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy import JSON
from datetime import datetime
from .base import BaseModel, AuditMixin, MetadataMixin
from .tenant import TenantAwareMixin
from enum import Enum

class ClientType(str, Enum):
    DIRECT = "direct"  # Direct client
    VENDOR = "vendor"  # Vendor/Partner
    PRIME = "prime"    # Prime contractor
    SUBCONTRACTOR = "subcontractor"

class ClientStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"
    BLACKLISTED = "blacklisted"
    PREFERRED = "preferred"

class PaymentTerms(str, Enum):
    NET_15 = "net_15"
    NET_30 = "net_30"
    NET_45 = "net_45"
    NET_60 = "net_60"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"

class Client(BaseModel, AuditMixin, MetadataMixin, TenantAwareMixin):
    """Client/Company model for managing hiring companies"""
    __tablename__ = 'clients'
    
    # Basic Information
    company_name = Column(String(200), nullable=False, index=True)
    legal_name = Column(String(200), nullable=True)
    dba_name = Column(String(200), nullable=True)  # Doing Business As
    
    # Company Details
    industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)  # startup, small, medium, large, enterprise
    founded_year = Column(Integer, nullable=True)
    
    # Contact Information
    primary_email = Column(String(255), nullable=True)
    primary_phone = Column(String(20), nullable=True)
    website = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    
    # Address
    headquarters_address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    country = Column(String(50), nullable=False, default='USA')
    postal_code = Column(String(20), nullable=True)
    
    # Business Information
    tax_id = Column(String(50), nullable=True)  # EIN/TIN
    duns_number = Column(String(20), nullable=True)
    
    # Client Classification
    client_type = Column(String(50), nullable=False, default=ClientType.DIRECT)
    client_status = Column(String(50), nullable=False, default=ClientStatus.PROSPECT)
    
    # Relationship Management
    account_manager_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    sales_rep_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # Business Terms
    payment_terms = Column(String(50), nullable=False, default=PaymentTerms.NET_30)
    credit_limit = Column(Numeric(12, 2), nullable=True)
    markup_percentage = Column(Numeric(5, 2), nullable=True)  # Standard markup for this client
    
    # Performance Metrics
    total_placements = Column(Integer, default=0, nullable=False)
    total_revenue = Column(Numeric(15, 2), default=0, nullable=False)
    average_placement_duration = Column(Integer, nullable=True)  # Days
    
    # Ratings and Feedback
    payment_rating = Column(Integer, nullable=True)  # 1-5 scale
    communication_rating = Column(Integer, nullable=True)  # 1-5 scale
    overall_rating = Column(Numeric(3, 2), nullable=True)  # 1-5 scale with decimals
    
    # Preferences
    preferred_skills = Column(JSON, nullable=True, default=[])  # List of skill IDs
    preferred_locations = Column(JSON, nullable=True, default=[])  # List of locations
    budget_range_min = Column(Numeric(10, 2), nullable=True)
    budget_range_max = Column(Numeric(10, 2), nullable=True)
    
    # Contract Information
    msa_signed = Column(Boolean, default=False, nullable=False)  # Master Service Agreement
    msa_expiry_date = Column(DateTime, nullable=True)
    w9_received = Column(Boolean, default=False, nullable=False)
    insurance_verified = Column(Boolean, default=False, nullable=False)
    
    # Internal Notes
    notes = Column(Text, nullable=True)
    strengths = Column(JSON, nullable=True, default=[])  # What they're good at
    challenges = Column(JSON, nullable=True, default=[])  # Challenges working with them
    
    # Marketing and Sales
    lead_source = Column(String(100), nullable=True)  # How we found them
    first_contact_date = Column(DateTime, nullable=True)
    last_activity_date = Column(DateTime, nullable=True)
    
    # Compliance and Risk
    background_check_required = Column(Boolean, default=False, nullable=False)
    drug_test_required = Column(Boolean, default=False, nullable=False)
    security_clearance_required = Column(Boolean, default=False, nullable=False)
    
    # Financial Information
    annual_revenue = Column(Numeric(15, 2), nullable=True)
    employee_count = Column(Integer, nullable=True)
    
    # Relationships
    account_manager = relationship('User', foreign_keys=[account_manager_id])
    sales_rep = relationship('User', foreign_keys=[sales_rep_id])
    
    # Business relationships
    contacts = relationship('ClientContact', back_populates='client', cascade='all, delete-orphan')
    job_opportunities = relationship('JobOpportunity', back_populates='client', cascade='all, delete-orphan')
    submissions = relationship('CandidateSubmission', back_populates='client')
    sales = relationship('CandidateSale', back_populates='client')
    
    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.company_name}', status='{self.client_status}')>"
    
    @property
    def is_active(self):
        """Check if client is active for new business"""
        return self.client_status == ClientStatus.ACTIVE
    
    @property
    def placement_success_rate(self):
        """Calculate placement success rate"""
        if not self.submissions:
            return 0
        successful = len([s for s in self.sales if s.status in ['active', 'completed']])
        total = len(self.submissions)
        return round((successful / total) * 100, 2) if total > 0 else 0
    
    @property
    def average_time_to_fill(self):
        """Calculate average time from submission to placement"""
        successful_sales = [s for s in self.sales if s.status in ['active', 'completed']]
        if not successful_sales:
            return None
        
        total_days = 0
        count = 0
        for sale in successful_sales:
            if sale.submission and sale.submission.submission_date:
                days = (sale.start_date - sale.submission.submission_date).days
                total_days += days
                count += 1
        
        return round(total_days / count, 1) if count > 0 else None

class ClientContact(BaseModel, AuditMixin, TenantAwareMixin):
    """Contact persons at client companies"""
    __tablename__ = 'client_contacts'
    
    # Foreign Key
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False, index=True)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(200), nullable=True)
    department = Column(String(100), nullable=True)
    
    # Contact Information
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    mobile = Column(String(20), nullable=True)
    
    # Role and Authority
    is_primary_contact = Column(Boolean, default=False, nullable=False)
    is_decision_maker = Column(Boolean, default=False, nullable=False)
    can_approve_hires = Column(Boolean, default=False, nullable=False)
    
    # Communication Preferences
    preferred_contact_method = Column(String(50), default='email', nullable=False)
    best_time_to_contact = Column(String(100), nullable=True)
    timezone = Column(String(50), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationship tracking
    last_contact_date = Column(DateTime, nullable=True)
    next_follow_up_date = Column(DateTime, nullable=True)
    
    # Relationships
    client = relationship('Client', back_populates='contacts')
    
    def __repr__(self):
        return f"<ClientContact(id={self.id}, name='{self.first_name} {self.last_name}', client_id={self.client_id})>"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class JobOpportunity(BaseModel, AuditMixin, MetadataMixin, TenantAwareMixin):
    """Job opportunities from clients"""
    __tablename__ = 'job_opportunities'
    
    # Foreign Keys
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False, index=True)
    client_contact_id = Column(Integer, ForeignKey('client_contacts.id'), nullable=True, index=True)
    assigned_recruiter_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # Job Details
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    
    # Location
    location = Column(String(200), nullable=True)
    remote_allowed = Column(Boolean, default=False, nullable=False)
    travel_required = Column(String(50), nullable=True)  # none, minimal, frequent
    
    # Employment Details
    employment_type = Column(String(50), nullable=False)  # contract, permanent, contract_to_hire
    duration_months = Column(Integer, nullable=True)  # For contract positions
    hours_per_week = Column(Integer, default=40, nullable=False)
    
    # Compensation
    budget_min = Column(Numeric(10, 2), nullable=True)
    budget_max = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default='USD', nullable=False)
    rate_type = Column(String(20), nullable=False, default='hourly')  # hourly, daily, monthly, annual
    
    # Requirements
    experience_years_min = Column(Integer, nullable=True)
    experience_years_max = Column(Integer, nullable=True)
    education_required = Column(String(100), nullable=True)
    
    # Skills (JSON array of skill requirements)
    required_skills = Column(JSON, nullable=True, default=[])
    preferred_skills = Column(JSON, nullable=True, default=[])
    
    # Status and Timeline
    status = Column(String(50), nullable=False, default='open')  # open, on_hold, filled, cancelled
    priority = Column(String(20), nullable=False, default='medium')  # low, medium, high, urgent
    
    # Important Dates
    start_date = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    
    # Submission Requirements
    max_submissions = Column(Integer, default=5, nullable=False)
    current_submissions = Column(Integer, default=0, nullable=False)
    
    # Internal Information
    internal_notes = Column(Text, nullable=True)
    client_urgency = Column(String(20), nullable=True)  # low, medium, high
    
    # Performance Tracking
    views_count = Column(Integer, default=0, nullable=False)
    applications_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    client = relationship('Client', back_populates='job_opportunities')
    client_contact = relationship('ClientContact')
    assigned_recruiter = relationship('User', foreign_keys=[assigned_recruiter_id])
    submissions = relationship('CandidateSubmission', back_populates='job_opportunity')
    
    def __repr__(self):
        return f"<JobOpportunity(id={self.id}, title='{self.title}', client_id={self.client_id}, status='{self.status}')>"
    
    @property
    def is_active(self):
        """Check if job is still accepting submissions"""
        return (self.status == 'open' and 
                self.current_submissions < self.max_submissions and
                (not self.deadline or self.deadline > datetime.utcnow()))
    
    @property
    def submission_rate(self):
        """Calculate submission rate as percentage of max"""
        return round((self.current_submissions / self.max_submissions) * 100, 1) if self.max_submissions > 0 else 0
    
    @property
    def days_until_deadline(self):
        """Calculate days until deadline"""
        if not self.deadline:
            return None
        delta = self.deadline - datetime.utcnow()
        return delta.days if delta.days >= 0 else 0