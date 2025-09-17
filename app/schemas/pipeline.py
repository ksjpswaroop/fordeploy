from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ScrapeRequest(BaseModel):
    actor_id: str = "BHzefUZlZRKWxkTck"
    title: str = ""
    location: str = "United States"
    company_name: List[str] = []
    company_id: List[str] = []
    rows: int = Field(default=50, ge=1, le=1000)
    output_path: Optional[str] = None

class ScrapeResponse(BaseModel):
    jobs_scraped: int
    output_path: str
    message: str

class EnrichRequest(BaseModel):
    database_path: str = Field(default="jobs.db", min_length=1)

class EnrichResponse(BaseModel):
    enriched_count: int
    message: str

class MatchRequest(BaseModel):
    resume_path: str = Field(..., min_length=1)
    database_path: str = Field(default="jobs.db", min_length=1)
    threshold: float = Field(default=30.0, ge=0, le=100)

class MatchingCriteria(BaseModel):
    skills: List[str] = []
    experience: List[str] = []
    education: List[str] = []
    tools: List[str] = []

class MissingCriteria(BaseModel):
    skills: List[str] = []
    experience: List[str] = []
    certifications: List[str] = []
    domain_knowledge: List[str] = []

class Recommendations(BaseModel):
    resume_updates: List[str] = []
    keywords_to_add: List[str] = []
    sections_to_enhance: List[str] = []

class JobAnalysis(BaseModel):
    overall_match_score: float
    match_threshold_met: bool
    matching_criteria: MatchingCriteria
    missing_criteria: MissingCriteria
    recommendations: Recommendations

class JobMatch(BaseModel):
    job_id: str
    job_title: str
    company_name: str
    analysis: JobAnalysis

class MatchResponse(BaseModel):
    matches_found: int
    jobs: List[JobMatch]
    message: str

class SendRequest(BaseModel):
    job_ids: List[str] = Field(..., min_length=1)
    resume_path: str = Field(..., min_length=1)
    database_path: str = Field(default="jobs.db", min_length=1)
    dry_run: bool = False

class SendResponse(BaseModel):
    emails_sent: int
    jobs_processed: int
    message: str

class HealthResponse(BaseModel):
    status: str
    version: str
    database_connection: bool
    api_connections: Dict[str, bool]
