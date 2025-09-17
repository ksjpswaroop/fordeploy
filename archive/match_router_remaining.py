from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os

# Import functions from the main pipeline script
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from job_application_pipeline import select_matching_jobs_with_openai, extract_resume_text

router = APIRouter()

class MatchRequest(BaseModel):
    resume_path: str
    database: str = "jobs.db"
    threshold: float = 30.0

class JobMatch(BaseModel):
    job_id: str
    job_title: str
    company_name: str
    match_score: float

class MatchResponse(BaseModel):
    jobs_matched: int
    matches: List[JobMatch]

@router.post("/match", response_model=MatchResponse)
def match_jobs(request: MatchRequest):
    """Match jobs to a resume using AI analysis."""
    # Check if OpenAI API key is set
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY environment variable not set.")
    
    # Extract resume text
    resume_text = extract_resume_text(request.resume_path)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Could not extract text from resume file.")
    
    # Match jobs
    matching_jobs = select_matching_jobs_with_openai(request.database, resume_text, openai_api_key, request.threshold)
    
    # Format response
    matches = []
    for job in matching_jobs:
        matches.append(JobMatch(
            job_id=job["job_id"],
            job_title=job["job_title"],
            company_name=job["company_name"],
            match_score=job["analysis"]["overall_match_score"]
        ))
    
    return MatchResponse(
        jobs_matched=len(matches),
        matches=matches
    )
