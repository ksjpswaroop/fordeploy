from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid

class PipelineStatus(str, Enum):
    """Status of a pipeline run."""
    PENDING = "pending"
    SCRAPING = "scraping"
    MATCHING = "matching"
    ENRICHING = "enriching" 
    GENERATING = "generating"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"

class PipelineRequest(BaseModel):
    """Input for starting a pipeline run."""
    actor_id: str = "BHzefUZlZRKWxkTck"
    title: str = ""
    location: str = "United States"
    company_name: List[str] = Field(default_factory=list)
    company_id: List[str] = Field(default_factory=list)
    rows: int = 50
    resume_path: str = ""
    database: str = "jobs.db"
    output_json: str = ""
    threshold: float = 30.0
    dry_run: bool = False

class PipelineRun(BaseModel):
    """Pipeline run state."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: PipelineStatus = PipelineStatus.PENDING
    request: PipelineRequest
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    jobs_scraped: int = 0
    jobs_matched: int = 0
    emails_sent: int = 0
    error: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PipelineResponse(BaseModel):
    """Response after starting a pipeline."""
    run_id: str
    status: PipelineStatus
    
class PipelineStatusResponse(BaseModel):
    """Detailed status of a pipeline run."""
    run_id: str
    status: PipelineStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    jobs_scraped: int
    jobs_matched: int
    emails_sent: int
    error: Optional[str] = None
    progress_percent: float = 0
