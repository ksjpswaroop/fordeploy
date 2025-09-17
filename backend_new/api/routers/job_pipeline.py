"""
FastAPI router for job application pipeline endpoints.
Converts all functions from job_application_pipeline.py into REST API endpoints.
"""

import os
import json
import sqlite3
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse

# Import the original pipeline functions
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from job_application_pipeline import (
    get_user_parameters,
    run_apify_job,
    save_jobs_to_json,
    init_database,
    upsert_jobs_into_db,
    enrich_contacts,
    extract_resume_text,
    clean_html,
    analyze_job_match_with_openai,
    similarity_score,
    select_matching_jobs_with_openai,
    select_matching_jobs,
    generate_ats_optimized_resume_with_analysis,
    generate_ats_optimized_resume,
    generate_optimized_cover_letter,
    send_email_via_sendgrid,
    filter_jobs,
    look_people
)

from app.schemas.job_pipeline import (
    JobSearchParams,
    JobSearchResponse,
    DatabaseInitRequest,
    DatabaseResponse,
    ResumeExtractionRequest,
    ResumeExtractionResponse,
    JobMatchingRequest,
    JobMatchingResponse,
    ResumeOptimizationRequest,
    ResumeOptimizationResponse,
    CoverLetterRequest,
    CoverLetterResponse,
    EmailRequest,
    EmailResponse,
    ContactEnrichmentRequest,
    ContactEnrichmentResponse,
    JobAnalysisRequest,
    JobAnalysisResponse,
    FilterJobsRequest,
    FilterJobsResponse,
    FullPipelineRequest,
    FullPipelineResponse
)

router = APIRouter(prefix="/job-pipeline", tags=["job-pipeline"])


def get_apify_token() -> str:
    """Get Apify token from environment variables."""
    token = os.getenv("APIFY_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="APIFY_TOKEN environment variable not set")
    return token


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment variables."""
    return os.getenv("OPENAI_API_KEY", "").strip()


def get_sendgrid_api_key() -> str:
    """Get SendGrid API key from environment variables."""
    return os.getenv("SENDGRID_API_KEY", "").strip()


@router.post("/search-jobs", response_model=JobSearchResponse)
async def search_jobs(
    params: JobSearchParams,
    apify_token: str = Depends(get_apify_token)
):
    """
    Search for jobs using Apify LinkedIn scraper.
    
    This endpoint runs the Apify actor to scrape LinkedIn jobs based on the provided parameters.
    """
    try:
        # Convert params to run_input format
        run_input = {
            "title": params.title or "",
            "location": params.location,
            "companyName": params.company_name,
            "companyId": params.company_id,
            "publishedAt": "",
            "rows": params.rows,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
        }
        
        # Remove empty values
        run_input = {k: v for k, v in run_input.items() if v}
        
        # Run Apify job
        jobs = run_apify_job(apify_token, params.actor_id, run_input)
        
        if not jobs:
            return JobSearchResponse(
                success=False,
                message="No jobs found with the given parameters",
                total_jobs=0,
                jobs=[]
            )
        
        # Save to JSON
        json_path = save_jobs_to_json(jobs)
        
        return JobSearchResponse(
            success=True,
            message=f"Successfully found {len(jobs)} jobs",
            total_jobs=len(jobs),
            jobs=jobs,
            json_file_path=json_path
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job search failed: {str(e)}")


@router.post("/init-database", response_model=DatabaseResponse)
async def initialize_database(request: DatabaseInitRequest):
    """
    Initialize SQLite database for storing jobs.
    
    Creates the jobs table if it doesn't exist.
    """
    try:
        init_database(request.db_path)
        return DatabaseResponse(
            success=True,
            message=f"Database initialized successfully at {request.db_path}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")


@router.post("/save-jobs-to-db", response_model=DatabaseResponse)
async def save_jobs_to_database(
    jobs: List[Dict[str, Any]],
    db_path: str = "jobs.db"
):
    """
    Save scraped jobs to SQLite database.
    
    Performs upsert operation (insert or update) based on job_id.
    """
    try:
        # Initialize database first
        init_database(db_path)
        
        # Save jobs
        upsert_jobs_into_db(db_path, jobs)
        
        return DatabaseResponse(
            success=True,
            message=f"Successfully saved {len(jobs)} jobs to database"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save jobs to database: {str(e)}")


@router.post("/enrich-contacts", response_model=ContactEnrichmentResponse)
async def enrich_job_contacts(request: ContactEnrichmentRequest):
    """
    Enrich job entries with recruiter contact information using Apollo API.
    
    Updates jobs that are missing contact information.
    """
    try:
        # Count jobs before enrichment
        conn = sqlite3.connect(request.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM jobs WHERE contact_name IS NOT NULL")
        before_count = c.fetchone()[0]
        conn.close()
        
        # Perform enrichment
        enrich_contacts(request.db_path)
        
        # Count jobs after enrichment
        conn = sqlite3.connect(request.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM jobs WHERE contact_name IS NOT NULL")
        after_count = c.fetchone()[0]
        conn.close()
        
        enriched_count = after_count - before_count
        
        return ContactEnrichmentResponse(
            success=True,
            message=f"Contact enrichment completed. {enriched_count} jobs enriched.",
            enriched_count=enriched_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Contact enrichment failed: {str(e)}")


@router.post("/extract-resume", response_model=ResumeExtractionResponse)
async def extract_resume_text_endpoint(request: ResumeExtractionRequest):
    """
    Extract text content from resume file.
    
    Supports .txt, .md, .pdf, and .docx files.
    """
    try:
        if not os.path.isfile(request.resume_path):
            raise HTTPException(status_code=404, detail=f"Resume file not found: {request.resume_path}")
        
        resume_text = extract_resume_text(request.resume_path)
        file_type = os.path.splitext(request.resume_path)[1].lower()
        
        if not resume_text:
            return ResumeExtractionResponse(
                success=False,
                message="Failed to extract text from resume file",
                resume_text="",
                file_type=file_type
            )
        
        return ResumeExtractionResponse(
            success=True,
            message="Resume text extracted successfully",
            resume_text=resume_text,
            file_type=file_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume extraction failed: {str(e)}")


@router.post("/analyze-job-match", response_model=JobAnalysisResponse)
async def analyze_job_match(request: JobAnalysisRequest):
    """
    Analyze job match using OpenAI API.
    
    Returns detailed analysis of how well the resume matches the job description.
    """
    try:
        openai_api_key = get_openai_api_key()
        if not openai_api_key:
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY environment variable not set")
        
        analysis = analyze_job_match_with_openai(
            request.resume_text,
            request.job_description,
            request.job_title,
            request.company_name,
            request.job_id,
            openai_api_key
        )
        
        return JobAnalysisResponse(
            success=True,
            message="Job analysis completed successfully",
            analysis=analysis
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job analysis failed: {str(e)}")


@router.post("/match-jobs", response_model=JobMatchingResponse)
async def match_jobs_with_resume(request: JobMatchingRequest):
    """
    Find jobs that match the resume based on similarity threshold.
    
    Can use either OpenAI analysis or simple similarity scoring.
    """
    try:
        if request.use_openai:
            openai_api_key = get_openai_api_key()
            if not openai_api_key:
                raise HTTPException(status_code=400, detail="OPENAI_API_KEY environment variable not set")
            
            matching_jobs = select_matching_jobs_with_openai(
                request.db_path,
                request.resume_text,
                openai_api_key,
                request.threshold
            )
        else:
            # Convert threshold from percentage to ratio
            threshold_ratio = request.threshold / 100.0
            job_matches = select_matching_jobs(
                request.db_path,
                request.resume_text,
                threshold_ratio
            )
            
            # Convert to analysis format for consistency
            matching_jobs = []
            for job_id, company in job_matches:
                matching_jobs.append({
                    "job_id": job_id,
                    "company_name": company,
                    "analysis": {
                        "overall_match_score": request.threshold,
                        "match_threshold_met": True
                    }
                })
        
        return JobMatchingResponse(
            success=True,
            message=f"Found {len(matching_jobs)} matching jobs",
            matching_jobs=matching_jobs,
            total_matches=len(matching_jobs)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job matching failed: {str(e)}")


@router.post("/filter-jobs", response_model=FilterJobsResponse)
async def filter_jobs_by_blacklist(request: FilterJobsRequest):
    """
    Filter out jobs from blacklisted companies.
    
    Uses the blacklist from users.json file.
    """
    try:
        filtered_jobs = filter_jobs(request.jobs)
        
        return FilterJobsResponse(
            success=True,
            message=f"Filtered {len(request.jobs) - len(filtered_jobs)} jobs from blacklisted companies",
            filtered_jobs=filtered_jobs,
            filtered_count=len(filtered_jobs),
            total_count=len(request.jobs)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job filtering failed: {str(e)}")


@router.post("/optimize-resume", response_model=ResumeOptimizationResponse)
async def optimize_resume(request: ResumeOptimizationRequest):
    """
    Generate ATS-optimized resume using OpenAI API.
    
    Optimizes the resume to match the job description and improve ATS compatibility.
    """
    try:
        openai_api_key = get_openai_api_key()
        if not openai_api_key:
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY environment variable not set")
        
        if request.use_analysis:
            # This would require a job analysis object, which we don't have in this endpoint
            # For now, use the regular optimization
            optimized_resume = generate_ats_optimized_resume(
                request.resume_text,
                request.job_description,
                request.job_title,
                request.company_name,
                openai_api_key
            )
        else:
            optimized_resume = generate_ats_optimized_resume(
                request.resume_text,
                request.job_description,
                request.job_title,
                request.company_name,
                openai_api_key
            )
        
        return ResumeOptimizationResponse(
            success=True,
            message="Resume optimized successfully",
            optimized_resume=optimized_resume
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume optimization failed: {str(e)}")


@router.post("/generate-cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter_endpoint(request: CoverLetterRequest):
    """
    Generate optimized cover letter using OpenAI API.
    
    Creates a personalized cover letter for the specific job and recruiter.
    """
    try:
        openai_api_key = get_openai_api_key()
        if not openai_api_key:
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY environment variable not set")
        
        cover_letter = generate_optimized_cover_letter(
            request.job_title,
            request.company_name,
            request.recruiter_name,
            request.job_description,
            request.resume_text,
            openai_api_key
        )
        
        return CoverLetterResponse(
            success=True,
            message="Cover letter generated successfully",
            cover_letter=cover_letter
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cover letter generation failed: {str(e)}")


@router.post("/send-email", response_model=EmailResponse)
async def send_email_endpoint(request: EmailRequest):
    """
    Send email with resume and cover letter via SendGrid.
    
    Can be used in dry-run mode to preview without sending.
    """
    try:
        sendgrid_api_key = get_sendgrid_api_key()
        if not sendgrid_api_key:
            raise HTTPException(status_code=400, detail="SENDGRID_API_KEY environment variable not set")
        
        send_email_via_sendgrid(
            sendgrid_api_key,
            request.to_email,
            request.subject,
            request.content,
            request.resume_text,
            request.dry_run
        )
        
        return EmailResponse(
            success=True,
            message="Email sent successfully" if not request.dry_run else "Email preview generated (dry run)",
            email_sent=not request.dry_run
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")


@router.post("/full-pipeline", response_model=FullPipelineResponse)
async def run_full_pipeline(
    request: FullPipelineRequest,
    background_tasks: BackgroundTasks,
    apify_token: str = Depends(get_apify_token)
):
    """
    Run the complete job application pipeline.
    
    This endpoint executes the entire workflow:
    1. Search for jobs
    2. Save to database
    3. Enrich contacts
    4. Match with resume
    5. Generate optimized materials
    6. Send emails
    """
    try:
        pipeline_steps = []
        files_generated = []
        emails_sent = 0
        
        # Step 1: Search for jobs
        pipeline_steps.append("Job search initiated")
        run_input = {
            "title": request.job_search_params.title or "",
            "location": request.job_search_params.location,
            "companyName": request.job_search_params.company_name,
            "companyId": request.job_search_params.company_id,
            "publishedAt": "",
            "rows": request.job_search_params.rows,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
        }
        run_input = {k: v for k, v in run_input.items() if v}
        
        jobs = run_apify_job(apify_token, request.job_search_params.actor_id, run_input)
        if not jobs:
            return FullPipelineResponse(
                success=False,
                message="No jobs found with the given parameters",
                total_jobs_found=0,
                matching_jobs=0,
                emails_sent=0,
                files_generated=[],
                pipeline_steps=["Job search completed - no jobs found"]
            )
        
        pipeline_steps.append(f"Found {len(jobs)} jobs")
        
        # Step 2: Save to database
        init_database(request.db_path)
        upsert_jobs_into_db(request.db_path, jobs)
        pipeline_steps.append("Jobs saved to database")
        
        # Step 3: Enrich contacts
        if request.enrich_contacts:
            enrich_contacts(request.db_path)
            pipeline_steps.append("Contact information enriched")
        
        # Step 4: Resume matching (if resume provided)
        matching_jobs = []
        if request.resume_path:
            resume_text = extract_resume_text(request.resume_path)
            if resume_text:
                openai_api_key = get_openai_api_key()
                if openai_api_key:
                    matching_jobs = select_matching_jobs_with_openai(
                        request.db_path, resume_text, openai_api_key, request.threshold
                    )
                else:
                    # Fallback to simple matching
                    threshold_ratio = request.threshold / 100.0
                    job_matches = select_matching_jobs(request.db_path, resume_text, threshold_ratio)
                    matching_jobs = [{"job_id": job_id, "company_name": company} for job_id, company in job_matches]
                
                # Filter blacklisted companies
                matching_jobs = filter_jobs(matching_jobs)
                pipeline_steps.append(f"Found {len(matching_jobs)} matching jobs")
                
                # Step 5: Generate materials and send emails
                if matching_jobs and not request.dry_run:
                    sendgrid_api_key = get_sendgrid_api_key()
                    if sendgrid_api_key:
                        conn = sqlite3.connect(request.db_path)
                        c = conn.cursor()
                        
                        for job_analysis in matching_jobs:
                            job_id = job_analysis["job_id"]
                            job_title = job_analysis.get("job_title", "Unknown Position")
                            company_name = job_analysis["company_name"]
                            
                            # Get contact info
                            c.execute(
                                "SELECT contact_name, contact_email, description_html FROM jobs WHERE job_id=?",
                                (job_id,)
                            )
                            row = c.fetchone()
                            if not row or not row[1]:  # No email
                                continue
                            
                            contact_name, contact_email, desc_html = row
                            
                            # Generate optimized resume
                            if openai_api_key:
                                optimized_resume = generate_ats_optimized_resume_with_analysis(
                                    resume_text, job_analysis, openai_api_key
                                )
                            else:
                                optimized_resume = generate_ats_optimized_resume(
                                    resume_text, clean_html(desc_html or ""), job_title, company_name, ""
                                )
                            
                            # Generate cover letter
                            if openai_api_key:
                                cover_letter = generate_optimized_cover_letter(
                                    job_title, company_name, contact_name, clean_html(desc_html or ""), resume_text, openai_api_key
                                )
                            else:
                                cover_letter = f"Dear {contact_name or 'Hiring Manager'},\n\nI am interested in the {job_title} position at {company_name}.\n\nBest regards"
                            
                            # Save files
                            resume_filename = f"resume_{job_id}.txt"
                            cover_letter_filename = f"cover_letter_{job_id}.txt"
                            
                            with open(resume_filename, "w", encoding="utf-8") as f:
                                f.write(optimized_resume)
                            files_generated.append(resume_filename)
                            
                            with open(cover_letter_filename, "w", encoding="utf-8") as f:
                                f.write(cover_letter)
                            files_generated.append(cover_letter_filename)
                            
                            # Send email
                            subject = f"Application for {job_title} at {company_name}"
                            send_email_via_sendgrid(
                                sendgrid_api_key, contact_email, subject, cover_letter, optimized_resume, False
                            )
                            emails_sent += 1
                        
                        conn.close()
                        pipeline_steps.append(f"Sent {emails_sent} emails")
                    else:
                        pipeline_steps.append("SENDGRID_API_KEY not set - emails not sent")
        
        return FullPipelineResponse(
            success=True,
            message="Pipeline completed successfully",
            total_jobs_found=len(jobs),
            matching_jobs=len(matching_jobs),
            emails_sent=emails_sent,
            files_generated=files_generated,
            pipeline_steps=pipeline_steps
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@router.get("/jobs/{job_id}")
async def get_job_details(job_id: str, db_path: str = "jobs.db"):
    """
    Get detailed information about a specific job.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Convert row to dictionary
        columns = [description[0] for description in c.description]
        job_data = dict(zip(columns, row))
        
        return {"success": True, "job": job_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve job details: {str(e)}")


@router.get("/jobs")
async def list_jobs(
    db_path: str = "jobs.db",
    limit: int = 50,
    offset: int = 0
):
    """
    List all jobs in the database with pagination.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Get total count
        c.execute("SELECT COUNT(*) FROM jobs")
        total_count = c.fetchone()[0]
        
        # Get jobs with pagination
        c.execute("SELECT * FROM jobs LIMIT ? OFFSET ?", (limit, offset))
        rows = c.fetchall()
        conn.close()
        
        # Convert rows to dictionaries
        columns = [description[0] for description in c.description]
        jobs = [dict(zip(columns, row)) for row in rows]
        
        return {
            "success": True,
            "jobs": jobs,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download generated files (resumes, cover letters, etc.).
    """
    try:
        if not os.path.exists(filename):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            filename,
            media_type='application/octet-stream',
            filename=filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")
