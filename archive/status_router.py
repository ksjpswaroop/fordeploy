from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os

# Import pipeline runs storage
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from routers.pipeline import pipeline_runs

router = APIRouter()

class PipelineStatusResponse(BaseModel):
    run_id: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    jobs_scraped: int
    jobs_matched: int
    emails_sent: int
    error: Optional[str] = None

@router.get("/status/{run_id}", response_model=PipelineStatusResponse)
def get_pipeline_status(run_id: str):
    """Get the status of a pipeline run."""
    if run_id not in pipeline_runs:
        raise HTTPException(status_code=404, detail=f"Pipeline run with ID {run_id} not found")
    
    run_data = pipeline_runs[run_id]
    
    return PipelineStatusResponse(
        run_id=run_id,
        status=run_data["status"],
        start_time=run_data["start_time"],
        end_time=run_data.get("end_time"),
        jobs_scraped=run_data.get("jobs_scraped", 0),
        jobs_matched=run_data.get("jobs_matched", 0),
        emails_sent=run_data.get("emails_sent", 0),
        error=run_data.get("error")
    )

@router.get("/status", response_model=List[PipelineStatusResponse])
def get_all_pipeline_runs():
    """Get status of all pipeline runs."""
    return [
        PipelineStatusResponse(
            run_id=run_id,
            status=data["status"],
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            jobs_scraped=data.get("jobs_scraped", 0),
            jobs_matched=data.get("jobs_matched", 0),
            emails_sent=data.get("emails_sent", 0),
            error=data.get("error")
        )
        for run_id, data in pipeline_runs.items()
    ]
