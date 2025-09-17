from fastapi import APIRouter, HTTPException

from app.schemas.pipeline import (
    ScrapeRequest, ScrapeResponse,
    EnrichRequest, EnrichResponse,
    MatchRequest, MatchResponse,
    SendRequest, SendResponse
)
from app.services.pipeline import PipelineService

router = APIRouter()

@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_jobs(request: ScrapeRequest):
    """
    Scrape jobs from LinkedIn using Apify
    """
    try:
        result = PipelineService.scrape_jobs(
            actor_id=request.actor_id,
            title=request.title,
            location=request.location,
            company_name=request.company_name,
            company_id=request.company_id,
            rows=request.rows,
            output_path=request.output_path
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scraping jobs: {str(e)}")

@router.post("/enrich", response_model=EnrichResponse)
async def enrich_jobs(request: EnrichRequest):
    """
    Enrich job entries with contact information
    """
    try:
        result = PipelineService.enrich_jobs(request.database_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enriching jobs: {str(e)}")

@router.post("/match", response_model=MatchResponse)
async def match_jobs(request: MatchRequest):
    """
    Match resume to jobs and provide analysis
    """
    try:
        result = PipelineService.match_jobs(
            resume_path=request.resume_path,
            database_path=request.database_path,
            threshold=request.threshold
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error matching jobs: {str(e)}")

@router.post("/send", response_model=SendResponse)
async def send_applications(request: SendRequest):
    """
    Send job applications with customized resume and cover letter
    """
    try:
        result = PipelineService.send_applications(
            job_ids=request.job_ids,
            resume_path=request.resume_path,
            database_path=request.database_path,
            dry_run=request.dry_run
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending applications: {str(e)}")
