from typing import Dict, List, Any
import asyncio
from datetime import datetime

from app.models.pipeline import PipelineRequest, PipelineStatus
from app.services.apify_service import scrape_jobs
from app.services.db_service import save_jobs, get_jobs
from app.services.apollo_service import enrich_job_contacts
from app.services.matching_service import match_jobs_to_resume
from app.services.generation_service import generate_optimized_materials
from app.services.email_service import send_job_applications
from app.db.pipeline_storage import update_pipeline_status, update_pipeline_metrics

async def run_full_pipeline(run_id: str, request: PipelineRequest):
    """Run the full job application pipeline."""
    try:
        # Update status to scraping
        update_pipeline_status(run_id, PipelineStatus.SCRAPING)
        
        # Step 1: Scrape jobs from LinkedIn
        jobs = await scrape_jobs(
            apify_token=get_api_key("APIFY_TOKEN"),
            actor_id=request.actor_id,
            job_title=request.title,
            location=request.location,
            company_names=request.company_name,
            company_ids=request.company_id,
            rows=request.rows
        )
        
        # Update job count
        update_pipeline_metrics(run_id, jobs_scraped=len(jobs))
        
        # Step 2: Save jobs to database
        await save_jobs(jobs, request.database)
        
        # Step 3: Match jobs to resume
        update_pipeline_status(run_id, PipelineStatus.MATCHING)
        matched_jobs = await match_jobs_to_resume(
            resume_path=request.resume_path,
            jobs=jobs,
            openai_api_key=get_api_key("OPENAI_API_KEY"),
            threshold=request.threshold
        )
        
        # Update matched job count
        update_pipeline_metrics(run_id, jobs_matched=len(matched_jobs))
        
        # Step 4: Enrich with contact info
        update_pipeline_status(run_id, PipelineStatus.ENRICHING)
        enriched_jobs = await enrich_job_contacts(
            jobs=matched_jobs,
            apollo_api_key=get_api_key("APOLLO_API_KEY")
        )
        
        # Step 5: Generate custom materials
        update_pipeline_status(run_id, PipelineStatus.GENERATING)
        applications = await generate_optimized_materials(
            jobs=enriched_jobs,
            resume_path=request.resume_path,
            openai_api_key=get_api_key("OPENAI_API_KEY")
        )
        
        # Step 6: Send emails
        update_pipeline_status(run_id, PipelineStatus.SENDING)
        emails_sent = 0
        if not request.dry_run:
            emails_sent = await send_job_applications(
                applications=applications,
                sendgrid_api_key=get_api_key("SENDGRID_API_KEY")
            )
        
        # Update email count
        update_pipeline_metrics(run_id, emails_sent=emails_sent)
        
        # Mark as completed
        update_pipeline_status(
            run_id, 
            PipelineStatus.COMPLETED,
            end_time=datetime.now()
        )
        
    except Exception as e:
        # Mark as failed
        update_pipeline_status(
            run_id, 
            PipelineStatus.FAILED,
            end_time=datetime.now(),
            error=str(e)
        )
        raise

def get_api_key(key_name: str) -> str:
    """Get API key from environment variables."""
    import os
    return os.getenv(key_name, "")
