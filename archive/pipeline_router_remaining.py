from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import os, uuid
from datetime import datetime

# Import functions from the main pipeline script
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from job_application_pipeline import run_pipeline_api

router = APIRouter()

# In-memory storage for pipeline runs
pipeline_runs = {}

class PipelineRequest(BaseModel):
    actor_id: str = "BHzefUZlZRKWxkTck"
    title: str = ""
    location: str = "United States"
    company_name: list[str] = []
    company_id: list[str] = []
    rows: int = 50
    resume: str = ""
    database: str = "jobs.db"
    output_json: str = ""
    threshold: float = 30.0
    dry_run: bool = False
    interactive: bool = False

class PipelineResponse(BaseModel):
    run_id: str
    status: str
    message: str

@router.post("/pipeline", response_model=PipelineResponse)
def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    """Start a full pipeline run as a background task."""
    # Generate a unique run ID
    run_id = str(uuid.uuid4())
    
    # Store initial pipeline state
    pipeline_runs[run_id] = {
        "status": "pending",
        "start_time": datetime.now().isoformat(),
        "request": request.dict(),
        "jobs_scraped": 0,
        "jobs_matched": 0,
        "emails_sent": 0,
        "error": None,
        "end_time": None
    }
    
    # Start the pipeline in background
    background_tasks.add_task(
        _run_pipeline_background,
        run_id=run_id,
        request=request
    )
    
    return PipelineResponse(
        run_id=run_id,
        status="pending",
        message="Pipeline started in background"
    )

async def _run_pipeline_background(run_id: str, request: PipelineRequest):
    """Run the pipeline in background and update status."""
    try:
        # Update status to running
        pipeline_runs[run_id]["status"] = "running"
        
        # Run the pipeline
        result = run_pipeline_api(request)
        
        # Update the pipeline state with results
        pipeline_runs[run_id].update({
            "status": "completed",
            "jobs_scraped": result.jobs_scraped,
            "jobs_matched": result.jobs_matched,
            "emails_sent": result.emails_sent,
            "message": result.message,
            "end_time": datetime.now().isoformat()
        })
    except Exception as e:
        # Update state with error
        pipeline_runs[run_id].update({
            "status": "failed",
            "error": str(e),
            "end_time": datetime.now().isoformat()
        })
