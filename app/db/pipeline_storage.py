from typing import Dict, Any, Optional
from datetime import datetime

# In-memory storage (replace with database in production)
pipeline_runs: Dict[str, Dict[str, Any]] = {}

def store_pipeline_run(run_id: str, pipeline_data: Dict[str, Any]) -> None:
    """Store pipeline run data."""
    pipeline_runs[run_id] = pipeline_data

def get_pipeline_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Get pipeline run data by ID."""
    return pipeline_runs.get(run_id)

def update_pipeline_status(
    run_id: str, 
    status: str,
    end_time: Optional[datetime] = None,
    error: Optional[str] = None
) -> None:
    """Update pipeline run status."""
    if run_id in pipeline_runs:
        pipeline_runs[run_id]["status"] = status
        if end_time:
            pipeline_runs[run_id]["end_time"] = end_time
        if error is not None:
            pipeline_runs[run_id]["error"] = error

def update_pipeline_metrics(
    run_id: str,
    jobs_scraped: Optional[int] = None,
    jobs_matched: Optional[int] = None,
    emails_sent: Optional[int] = None
) -> None:
    """Update pipeline metrics."""
    if run_id in pipeline_runs:
        if jobs_scraped is not None:
            pipeline_runs[run_id]["jobs_scraped"] = jobs_scraped
        if jobs_matched is not None:
            pipeline_runs[run_id]["jobs_matched"] = jobs_matched
        if emails_sent is not None:
            pipeline_runs[run_id]["emails_sent"] = emails_sent
