from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from typing import Dict, List
import uuid
from datetime import datetime

from app.models.pipeline import (
    PipelineRequest, 
    PipelineResponse, 
    PipelineStatusResponse,
    PipelineStatus
)
from app.services.pipeline_service import run_full_pipeline
from app.db.pipeline_storage import get_pipeline_run, store_pipeline_run, update_pipeline_status

router = APIRouter()

# In-memory storage for demo purposes (replace with database in production)
pipeline_runs: Dict[str, Dict] = {}

@router.post("/pipeline", response_model=PipelineResponse)
async def start_pipeline(
    request: PipelineRequest, 
    background_tasks: BackgroundTasks
):
    """Start a full pipeline run as a background task."""
    run_id = str(uuid.uuid4())
    
    # Create initial pipeline state
    pipeline_run = {
        "run_id": run_id,
        "status": PipelineStatus.PENDING,
        "request": request.dict(),
        "start_time": datetime.now(),
        "jobs_scraped": 0,
        "jobs_matched": 0,
        "emails_sent": 0,
        "error": None
    }
    
    # Store pipeline state
    store_pipeline_run(run_id, pipeline_run)
    
    # Start the pipeline in background
    background_tasks.add_task(
        run_full_pipeline,
        run_id=run_id,
        request=request
    )
    
    return PipelineResponse(run_id=run_id, status=PipelineStatus.PENDING)

@router.get("/pipeline/{run_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(run_id: str):
    """Get the status of a pipeline run."""
    pipeline_run = get_pipeline_run(run_id)
    
    if not pipeline_run:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")
    
    # Calculate progress percentage based on status
    status_weights = {
        PipelineStatus.PENDING: 0,
        PipelineStatus.SCRAPING: 20,
        PipelineStatus.MATCHING: 40,
        PipelineStatus.ENRICHING: 60,
        PipelineStatus.GENERATING: 80,
        PipelineStatus.SENDING: 90,
        PipelineStatus.COMPLETED: 100,
        PipelineStatus.FAILED: 100
    }
    
    progress = status_weights.get(pipeline_run["status"], 0)
    
    return PipelineStatusResponse(
        run_id=pipeline_run["run_id"],
        status=pipeline_run["status"],
        start_time=pipeline_run["start_time"],
        end_time=pipeline_run.get("end_time"),
        jobs_scraped=pipeline_run["jobs_scraped"],
        jobs_matched=pipeline_run["jobs_matched"],
        emails_sent=pipeline_run["emails_sent"],
        error=pipeline_run.get("error"),
        progress_percent=progress
    )
