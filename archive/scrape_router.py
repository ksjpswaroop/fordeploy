from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os

# Import functions from the main pipeline script
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from job_application_pipeline import run_apify_job, save_jobs_to_json, init_database, upsert_jobs_into_db

router = APIRouter()

class ScrapeRequest(BaseModel):
    actor_id: str = "BHzefUZlZRKWxkTck"
    title: str = ""
    location: str = "United States"
    company_name: list[str] = []
    company_id: list[str] = []
    rows: int = 50
    output_json: str = ""
    database: str = "jobs.db"

class ScrapeResponse(BaseModel):
    jobs_count: int
    output_path: str
    message: str

@router.post("/scrape", response_model=ScrapeResponse)
def scrape_jobs(request: ScrapeRequest):
    """Scrape jobs from LinkedIn using Apify."""
    # Check if APIFY_TOKEN is set
    apify_token = os.getenv("APIFY_TOKEN", "").strip()
    if not apify_token:
        raise HTTPException(status_code=400, detail="APIFY_TOKEN environment variable not set.")
    
    # Prepare run input for Apify
    run_input = {
        "title": request.title or "",
        "location": request.location or "United States",
        "companyName": request.company_name or [],
        "companyId": request.company_id or [],
        "publishedAt": "",
        "rows": request.rows,
        "proxy": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
    }
    run_input = {k: v for k, v in run_input.items() if v}
    
    # Run the Apify job
    jobs = run_apify_job(apify_token, request.actor_id, run_input)
    if not jobs:
        return ScrapeResponse(
            jobs_count=0,
            output_path="",
            message="No jobs retrieved."
        )
    
    # Save to JSON
    json_path = save_jobs_to_json(jobs, request.output_json)
    
    # Save to database
    init_database(request.database)
    upsert_jobs_into_db(request.database, jobs)
    
    return ScrapeResponse(
        jobs_count=len(jobs),
        output_path=json_path,
        message=f"Successfully scraped {len(jobs)} jobs"
    )
