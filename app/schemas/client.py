from pydantic import BaseModel, Field, ConfigDict, validator, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from .base import (
    TimestampMixin, ClientType, ClientStatus, PaymentTerms
)

# Client Schemas
class ClientBase(BaseModel):
    """Base schema for clients"""
    company_name: str = Field(..., min_length=1, max_length=200)
    client_type: ClientType = Field(...)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=500)
    
    # Location
    headquarters_location: Optional[str] = Field(None, max_length=200)
    office_locations: Optional[List[str]] = Field(default=[])
    
    # Business Information
    description: Optional[str] = None
    specializations: Optional[List[str]] = Field(default=[])
    
    # Financial Terms
    payment_terms: PaymentTerms = Field(default=PaymentTerms.NET_30)
    preferred_markup_range_min: Optional[Decimal] = Field(None, ge=0, le=100)
    preferred_markup_range_max: Optional[Decimal] = Field(None, ge=0, le=100)
    
    # Preferences
    preferred_contract_types: Optional[List[str]] = Field(default=[])
    minimum_contract_duration: Optional[int] = Field(None, ge=1, le=60)
    maximum_contract_duration: Optional[int] = Field(None, ge=1, le=60)
    
    # Requirements
    required_work_authorization: Optional[List[str]] = Field(default=[])
    remote_work_policy: Optional[str] = Field(None, max_length=100)
    
    # Notes and Tags
    internal_notes: Optional[str] = None
    tags: Optional[List[str]] = Field(default=[])

class ClientCreate(ClientBase):
    """Schema for creating a client"""
    primary_contact_name: str = Field(..., min_length=1, max_length=200)
    primary_contact_email: EmailStr = Field(...)
    primary_contact_phone: Optional[str] = Field(None, max_length=20)
    primary_contact_title: Optional[str] = Field(None, max_length=100)

class ClientUpdate(BaseModel):
    """Schema for updating a client"""
    company_name: Optional[str] = Field(None, min_length=1, max_length=200)
    client_type: Optional[ClientType] = None
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=500)
    headquarters_location: Optional[str] = Field(None, max_length=200)
    office_locations: Optional[List[str]] = None
    description: Optional[str] = None
    specializations: Optional[List[str]] = None
    payment_terms: Optional[PaymentTerms] = None
    preferred_markup_range_min: Optional[Decimal] = Field(None, ge=0, le=100)
    preferred_markup_range_max: Optional[Decimal] = Field(None, ge=0, le=100)
    preferred_contract_types: Optional[List[str]] = None
    minimum_contract_duration: Optional[int] = Field(None, ge=1, le=60)
    maximum_contract_duration: Optional[int] = Field(None, ge=1, le=60)
    required_work_authorization: Optional[List[str]] = None
    remote_work_policy: Optional[str] = Field(None, max_length=100)
    status: Optional[ClientStatus] = None
    internal_notes: Optional[str] = None
    tags: Optional[List[str]] = None
    
    @validator('preferred_markup_range_max')
    def validate_markup_range(cls, v, values):
        if v is not None and 'preferred_markup_range_min' in values and values['preferred_markup_range_min'] is not None:
            if v < values['preferred_markup_range_min']:
                raise ValueError('preferred_markup_range_max must be greater than or equal to preferred_markup_range_min')
        return v
    
    @validator('maximum_contract_duration')
    def validate_contract_duration(cls, v, values):
        if v is not None and 'minimum_contract_duration' in values and values['minimum_contract_duration'] is not None:
            if v < values['minimum_contract_duration']:
                raise ValueError('maximum_contract_duration must be greater than or equal to minimum_contract_duration')
        return v

class ClientResponse(ClientBase, TimestampMixin):
    """Schema for client response"""
    id: int
    status: ClientStatus
    
    # Performance Metrics
    total_job_opportunities: int = 0
    active_job_opportunities: int = 0
    total_candidates_submitted: int = 0
    successful_placements: int = 0
    total_revenue_generated: Decimal = Decimal('0.00')
    average_time_to_fill: Optional[float] = None
    client_satisfaction_score: Optional[Decimal] = None
    
    # Calculated fields
    placement_success_rate: float = 0.0
    average_markup_percentage: Optional[Decimal] = None
    
    model_config = ConfigDict(from_attributes=True)

class ClientSummary(BaseModel):
    """Summary schema for client listings"""
    id: int
    company_name: str
    client_type: ClientType
    status: ClientStatus
    industry: Optional[str] = None
    headquarters_location: Optional[str] = None
    total_job_opportunities: int
    active_job_opportunities: int
    successful_placements: int
    total_revenue_generated: Decimal
    placement_success_rate: float
    
    model_config = ConfigDict(from_attributes=True)

# Client Contact Schemas
class ClientContactBase(BaseModel):
    """Base schema for client contacts"""
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr = Field(...)
    phone: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    is_primary: bool = Field(default=False)
    is_decision_maker: bool = Field(default=False)
    
    # Contact Preferences
    preferred_contact_method: str = Field(default="email", max_length=50)
    best_time_to_contact: Optional[str] = Field(None, max_length=100)
    timezone: str = Field(default="UTC", max_length=50)
    
    # Additional Information
    linkedin_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None

class ClientContactCreate(ClientContactBase):
    """Schema for creating client contact"""
    client_id: int = Field(..., gt=0)

class ClientContactUpdate(BaseModel):
    """Schema for updating client contact"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    is_primary: Optional[bool] = None
    is_decision_maker: Optional[bool] = None
    preferred_contact_method: Optional[str] = Field(None, max_length=50)
    best_time_to_contact: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class ClientContactResponse(ClientContactBase, TimestampMixin):
    """Schema for client contact response"""
    id: int
    client_id: int
    is_active: bool
    last_contacted: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Job Opportunity Schemas
class JobOpportunityBase(BaseModel):
    """Base schema for job opportunities"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    requirements: Optional[str] = None
    
    # Position Details
    experience_level: Optional[str] = Field(None, max_length=50)
    required_skills: Optional[List[str]] = Field(default=[])
    preferred_skills: Optional[List[str]] = Field(default=[])
    
    # Location and Work Arrangement
    location: Optional[str] = Field(None, max_length=200)
    remote_work_allowed: bool = Field(default=False)
    travel_required: Optional[str] = Field(None, max_length=100)
    
    # Contract Details
    contract_type: str = Field(..., max_length=50)
    duration_months: Optional[int] = Field(None, ge=1, le=60)
    hours_per_week: int = Field(default=40, ge=1, le=80)
    
    # Compensation
    hourly_rate_min: Optional[Decimal] = Field(None, gt=0)
    hourly_rate_max: Optional[Decimal] = Field(None, gt=0)
    currency: str = Field(default="USD", max_length=3)
    
    # Requirements
    work_authorization_required: Optional[List[str]] = Field(default=[])
    security_clearance_required: Optional[str] = Field(None, max_length=100)
    
    # Urgency and Priority
    priority_level: str = Field(default="medium", max_length=20)
    start_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    
    # Internal Information
    internal_notes: Optional[str] = None
    markup_percentage: Optional[Decimal] = Field(None, ge=0, le=100)

class JobOpportunityCreate(JobOpportunityBase):
    """Schema for creating job opportunity"""
    client_id: int = Field(..., gt=0)
    client_contact_id: Optional[int] = Field(None, gt=0)
    created_by: int = Field(..., gt=0)

class JobOpportunityUpdate(BaseModel):
    """Schema for updating job opportunity"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    requirements: Optional[str] = None
    experience_level: Optional[str] = Field(None, max_length=50)
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    location: Optional[str] = Field(None, max_length=200)
    remote_work_allowed: Optional[bool] = None
    travel_required: Optional[str] = Field(None, max_length=100)
    contract_type: Optional[str] = Field(None, max_length=50)
    duration_months: Optional[int] = Field(None, ge=1, le=60)
    hours_per_week: Optional[int] = Field(None, ge=1, le=80)
    hourly_rate_min: Optional[Decimal] = Field(None, gt=0)
    hourly_rate_max: Optional[Decimal] = Field(None, gt=0)
    work_authorization_required: Optional[List[str]] = None
    security_clearance_required: Optional[str] = Field(None, max_length=100)
    priority_level: Optional[str] = Field(None, max_length=20)
    start_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    status: Optional[str] = Field(None, max_length=50)
    internal_notes: Optional[str] = None
    markup_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    client_contact_id: Optional[int] = Field(None, gt=0)
    
    @validator('hourly_rate_max')
    def validate_rate_range(cls, v, values):
        if v is not None and 'hourly_rate_min' in values and values['hourly_rate_min'] is not None:
            if v < values['hourly_rate_min']:
                raise ValueError('hourly_rate_max must be greater than or equal to hourly_rate_min')
        return v

class JobOpportunityResponse(JobOpportunityBase, TimestampMixin):
    """Schema for job opportunity response"""
    id: int
    client_id: int
    client_contact_id: Optional[int] = None
    created_by: int
    status: str
    
    # Performance Metrics
    total_submissions: int = 0
    qualified_submissions: int = 0
    interviews_scheduled: int = 0
    successful_placements: int = 0
    
    # Calculated fields
    days_open: int
    submission_to_interview_rate: float = 0.0
    interview_to_placement_rate: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)

class JobOpportunitySummary(BaseModel):
    """Summary schema for job opportunity listings"""
    id: int
    title: str
    client_id: int
    client_name: str
    status: str
    contract_type: str
    location: Optional[str] = None
    hourly_rate_min: Optional[Decimal] = None
    hourly_rate_max: Optional[Decimal] = None
    priority_level: str
    start_date: Optional[datetime] = None
    total_submissions: int
    successful_placements: int
    days_open: int
    
    model_config = ConfigDict(from_attributes=True)

# Search and Filter Schemas
class ClientFilters(BaseModel):
    """Schema for filtering clients"""
    client_type: Optional[List[ClientType]] = None
    status: Optional[List[ClientStatus]] = None
    industry: Optional[List[str]] = None
    company_size: Optional[List[str]] = None
    payment_terms: Optional[List[PaymentTerms]] = None
    locations: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    has_active_opportunities: Optional[bool] = None
    min_revenue: Optional[Decimal] = Field(None, ge=0)
    max_revenue: Optional[Decimal] = Field(None, ge=0)
    min_placements: Optional[int] = Field(None, ge=0)
    max_placements: Optional[int] = Field(None, ge=0)
    
    @validator('max_revenue')
    def validate_revenue_range(cls, v, values):
        if v is not None and 'min_revenue' in values and values['min_revenue'] is not None:
            if v < values['min_revenue']:
                raise ValueError('max_revenue must be greater than or equal to min_revenue')
        return v
    
    @validator('max_placements')
    def validate_placements_range(cls, v, values):
        if v is not None and 'min_placements' in values and values['min_placements'] is not None:
            if v < values['min_placements']:
                raise ValueError('max_placements must be greater than or equal to min_placements')
        return v

class ClientSearch(BaseModel):
    """Schema for searching clients"""
    query: Optional[str] = Field(None, min_length=1, max_length=200)
    filters: Optional[ClientFilters] = None
    sort_by: Optional[str] = Field(default="created_at", max_length=50)
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")

class JobOpportunityFilters(BaseModel):
    """Schema for filtering job opportunities"""
    client_id: Optional[List[int]] = None
    status: Optional[List[str]] = None
    contract_type: Optional[List[str]] = None
    priority_level: Optional[List[str]] = None
    remote_work_allowed: Optional[bool] = None
    locations: Optional[List[str]] = None
    required_skills: Optional[List[str]] = None
    work_authorization_required: Optional[List[str]] = None
    hourly_rate_min: Optional[Decimal] = Field(None, gt=0)
    hourly_rate_max: Optional[Decimal] = Field(None, gt=0)
    duration_months_min: Optional[int] = Field(None, ge=1)
    duration_months_max: Optional[int] = Field(None, ge=1)
    start_date_from: Optional[datetime] = None
    start_date_to: Optional[datetime] = None
    
    @validator('hourly_rate_max')
    def validate_rate_range(cls, v, values):
        if v is not None and 'hourly_rate_min' in values and values['hourly_rate_min'] is not None:
            if v < values['hourly_rate_min']:
                raise ValueError('hourly_rate_max must be greater than or equal to hourly_rate_min')
        return v
    
    @validator('duration_months_max')
    def validate_duration_range(cls, v, values):
        if v is not None and 'duration_months_min' in values and values['duration_months_min'] is not None:
            if v < values['duration_months_min']:
                raise ValueError('duration_months_max must be greater than or equal to duration_months_min')
        return v

class JobOpportunitySearch(BaseModel):
    """Schema for searching job opportunities"""
    query: Optional[str] = Field(None, min_length=1, max_length=200)
    filters: Optional[JobOpportunityFilters] = None
    sort_by: Optional[str] = Field(default="created_at", max_length=50)
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")

# Analytics Schemas
class ClientAnalytics(BaseModel):
    """Schema for client analytics"""
    total_clients: int
    active_clients: int
    new_clients_this_month: int
    total_job_opportunities: int
    active_job_opportunities: int
    total_revenue: Decimal
    average_placement_time: Optional[float] = None
    top_industries: List[Dict[str, Any]]
    client_satisfaction_average: Optional[Decimal] = None
    
    model_config = ConfigDict(from_attributes=True)

class ClientPerformance(BaseModel):
    """Schema for individual client performance"""
    client_id: int
    company_name: str
    total_opportunities: int
    active_opportunities: int
    total_submissions: int
    successful_placements: int
    total_revenue: Decimal
    placement_success_rate: float
    average_time_to_fill: Optional[float] = None
    client_satisfaction_score: Optional[Decimal] = None
    
    model_config = ConfigDict(from_attributes=True)

# Bulk Operations Schemas
class BulkClientUpdate(BaseModel):
    """Schema for bulk client updates"""
    client_ids: List[int] = Field(..., min_items=1, max_items=100)
    updates: ClientUpdate = Field(...)

class BulkJobOpportunityUpdate(BaseModel):
    """Schema for bulk job opportunity updates"""
    opportunity_ids: List[int] = Field(..., min_items=1, max_items=100)
    updates: JobOpportunityUpdate = Field(...)

class BulkOperationResult(BaseModel):
    """Schema for bulk operation results"""
    total_requested: int
    successful_updates: int
    failed_updates: int
    errors: List[Dict[str, Any]] = Field(default=[])
    
    model_config = ConfigDict(from_attributes=True)