"""
Pydantic schemas for job application pipeline API endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobSearchParams(BaseModel):
    """Parameters for job search via Apify."""
    title: Optional[str] = Field(None, description="Job title filter")
    location: str = Field("United States", description="Job location")
    company_name: List[str] = Field(default_factory=list, description="Company names to filter by")
    company_id: List[str] = Field(default_factory=list, description="Company IDs to filter by")
    rows: int = Field(50, description="Number of jobs to fetch", ge=1, le=1000)
    actor_id: str = Field("BHzefUZlZRKWxkTck", description="Apify actor ID")


class JobData(BaseModel):
    """Job data structure."""
    job_id: str
    job_title: str
    company_name: str
    location: str
    description_html: str
    poster_name: Optional[str] = None
    poster_profile_url: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_linkedin: Optional[str] = None


class JobSearchResponse(BaseModel):
    """Response for job search."""
    success: bool
    message: str
    total_jobs: int
    jobs: List[Dict[str, Any]]
    json_file_path: Optional[str] = None


class DatabaseInitRequest(BaseModel):
    """Request to initialize database."""
    db_path: str = Field("jobs.db", description="Path to SQLite database file")


class DatabaseResponse(BaseModel):
    """Response for database operations."""
    success: bool
    message: str
    inserted: Optional[int] = None
    updated: Optional[int] = None


class ResumeExtractionRequest(BaseModel):
    """Request to extract resume text."""
    resume_path: str = Field(..., description="Path to resume file")


class ResumeExtractionResponse(BaseModel):
    """Response for resume extraction."""
    success: bool
    message: str
    resume_text: str
    file_type: str


class JobMatchingRequest(BaseModel):
    """Request for job matching."""
    db_path: str = Field("jobs.db", description="Path to SQLite database")
    resume_text: str = Field(..., description="Resume text content")
    threshold: float = Field(40.0, description="Match threshold (0-100)", ge=0, le=100)
    use_openai: bool = Field(True, description="Use OpenAI for analysis")


class JobMatchingResponse(BaseModel):
    """Response for job matching."""
    success: bool
    message: str
    matching_jobs: List[Dict[str, Any]]
    total_matches: int


class ResumeOptimizationRequest(BaseModel):
    """Request for resume optimization."""
    resume_text: str = Field(..., description="Original resume text")
    job_description: str = Field(..., description="Job description")
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")
    use_analysis: bool = Field(False, description="Use detailed job analysis")


class ResumeOptimizationResponse(BaseModel):
    """Response for resume optimization."""
    success: bool
    message: str
    optimized_resume: str


class CoverLetterRequest(BaseModel):
    """Request for cover letter generation."""
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")
    recruiter_name: Optional[str] = Field(None, description="Recruiter name")
    job_description: str = Field(..., description="Job description")
    resume_text: str = Field(..., description="Resume text")


class CoverLetterResponse(BaseModel):
    """Response for cover letter generation."""
    success: bool
    message: str
    cover_letter: str


class EmailRequest(BaseModel):
    """Request to send email."""
    to_email: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    content: str = Field(..., description="Email content (cover letter)")
    resume_text: str = Field(..., description="Resume text to attach")
    dry_run: bool = Field(False, description="Skip sending, just log")


class EmailResponse(BaseModel):
    """Response for email sending."""
    success: bool
    message: str
    email_sent: bool


class ContactEnrichmentRequest(BaseModel):
    """Request for contact enrichment."""
    db_path: str = Field("jobs.db", description="Path to SQLite database")


class ContactEnrichmentResponse(BaseModel):
    """Response for contact enrichment."""
    success: bool
    message: str
    enriched_count: int


class JobAnalysisRequest(BaseModel):
    """Request for job analysis."""
    resume_text: str = Field(..., description="Resume text")
    job_description: str = Field(..., description="Job description")
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")
    job_id: str = Field(..., description="Job ID")


class JobAnalysisResponse(BaseModel):
    """Response for job analysis."""
    success: bool
    message: str
    analysis: Dict[str, Any]


class FilterJobsRequest(BaseModel):
    """Request to filter jobs by blacklist."""
    jobs: List[Dict[str, Any]] = Field(..., description="List of job dictionaries")


class FilterJobsResponse(BaseModel):
    """Response for job filtering."""
    success: bool
    message: str
    filtered_jobs: List[Dict[str, Any]]
    filtered_count: int
    total_count: int


class FullPipelineRequest(BaseModel):
    """Request for full pipeline execution."""
    job_search_params: JobSearchParams
    resume_path: Optional[str] = Field(None, description="Path to resume file")
    db_path: str = Field("jobs.db", description="Path to SQLite database")
    threshold: float = Field(40.0, description="Match threshold", ge=0, le=100)
    dry_run: bool = Field(False, description="Skip sending emails")
    enrich_contacts: bool = Field(True, description="Enrich with contact info")


class FullPipelineResponse(BaseModel):
    """Response for full pipeline execution."""
    success: bool
    message: str
    total_jobs_found: int
    matching_jobs: int
    emails_sent: int
    files_generated: List[str]
    pipeline_steps: List[str]
