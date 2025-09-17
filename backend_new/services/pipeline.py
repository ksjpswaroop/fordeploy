import json
import os
from typing import Dict, List, Any, Tuple, Optional

# Reuse existing functions from the original script
from job_application_pipeline import (
    get_user_parameters,
    run_apify_job, 
    save_jobs_to_json, 
    init_database, 
    upsert_jobs_into_db,
    enrich_contacts,
    extract_resume_text,
    clean_html,
    select_matching_jobs_with_openai,
    analyze_job_match_with_openai,
    generate_ats_optimized_resume_with_analysis,
    generate_optimized_cover_letter,
    send_email_via_sendgrid,
    filter_jobs
)

from app.core.config import settings

class PipelineService:
    @staticmethod
    def scrape_jobs(
        actor_id: str,
        title: str,
        location: str,
        company_name: List[str],
        company_id: List[str],
        rows: int,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Scrape jobs from LinkedIn using Apify"""
        # Create run_input for Apify
        run_input = {
            "title": title or "",
            "location": location or "United States",
            "companyName": company_name or [],
            "companyId": company_id or [],
            "publishedAt": "",
            "rows": rows,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
        }
        run_input = {k: v for k, v in run_input.items() if v}
        
        # Run Apify job
        jobs = run_apify_job(settings.APIFY_TOKEN, actor_id, run_input)
        
        # Save jobs to JSON
        if jobs:
            json_path = save_jobs_to_json(jobs, output_path)
            
            # Initialize and update database
            init_database("jobs.db")
            upsert_jobs_into_db("jobs.db", jobs)
            
            return {
                "jobs_scraped": len(jobs),
                "output_path": json_path,
                "message": f"Successfully scraped {len(jobs)} jobs"
            }
        else:
            return {
                "jobs_scraped": 0,
                "output_path": "",
                "message": "No jobs retrieved"
            }
    
    @staticmethod
    def enrich_jobs(database_path: str) -> Dict[str, Any]:
        """Enrich job contacts using Apollo API"""
        # First ensure database exists
        if not os.path.exists(database_path):
            init_database(database_path)
        
        # Run enrichment
        try:
            # This function updates the database and returns None
            enrich_contacts(database_path)
            
            # We need to count how many records were enriched
            # This requires checking the database
            import sqlite3
            conn = sqlite3.connect(database_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM jobs WHERE contact_name IS NOT NULL")
            enriched_count = c.fetchone()[0]
            conn.close()
            
            return {
                "enriched_count": enriched_count,
                "message": f"Successfully enriched {enriched_count} job contacts"
            }
        except Exception as e:
            return {
                "enriched_count": 0,
                "message": f"Error enriching contacts: {str(e)}"
            }
    
    @staticmethod
    def match_jobs(resume_path: str, database_path: str, threshold: float) -> Dict[str, Any]:
        """Match resume to jobs using OpenAI"""
        # Ensure database exists
        if not os.path.exists(database_path):
            return {
                "matches_found": 0,
                "jobs": [],
                "message": f"Database not found: {database_path}"
            }
        
        # Extract resume text
        resume_text = extract_resume_text(resume_path)
        if not resume_text:
            return {
                "matches_found": 0,
                "jobs": [],
                "message": f"Could not extract text from resume: {resume_path}"
            }
        
        # Find matching jobs with OpenAI analysis
        matching_jobs = select_matching_jobs_with_openai(
            database_path, 
            resume_text, 
            settings.OPENAI_API_KEY,
            threshold
        )
        
        # Filter out blacklisted companies
        filtered_jobs = filter_jobs(matching_jobs)
        
        return {
            "matches_found": len(filtered_jobs),
            "jobs": filtered_jobs,
            "message": f"Found {len(filtered_jobs)} matching jobs"
        }
    
    @staticmethod
    def send_applications(
        job_ids: List[str], 
        resume_path: str, 
        database_path: str, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """Send job applications with customized resume and cover letter"""
        # Validate inputs
        if not os.path.exists(database_path):
            return {
                "emails_sent": 0,
                "jobs_processed": 0,
                "message": f"Database not found: {database_path}"
            }
        
        if not os.path.exists(resume_path):
            return {
                "emails_sent": 0,
                "jobs_processed": 0,
                "message": f"Resume not found: {resume_path}"
            }
        
        # Extract resume text
        resume_text = extract_resume_text(resume_path)
        if not resume_text:
            return {
                "emails_sent": 0,
                "jobs_processed": 0,
                "message": f"Could not extract text from resume: {resume_path}"
            }
        
        # Get job details from database
        import sqlite3
        conn = sqlite3.connect(database_path)
        c = conn.cursor()
        
        emails_sent = 0
        jobs_processed = 0
        
        for job_id in job_ids:
            c.execute(
                "SELECT job_title, company_name, contact_name, contact_email, description_html "
                "FROM jobs WHERE job_id=?",
                (job_id,)
            )
            row = c.fetchone()
            
            if not row:
                continue
                
            job_title, company_name, contact_name, contact_email, desc_html = row
            
            # Skip if no email
            if not contact_email:
                continue
            
            # Get job description
            plain_desc = clean_html(desc_html or "")
            
            # Analyze job match (needed for optimized resume)
            job_analysis = analyze_job_match_with_openai(
                resume_text, 
                plain_desc, 
                job_title, 
                company_name, 
                job_id, 
                settings.OPENAI_API_KEY
            )
            
            # Generate optimized resume
            optimized_resume = generate_ats_optimized_resume_with_analysis(
                resume_text, job_analysis, settings.OPENAI_API_KEY
            )
            
            # Generate cover letter
            cover_letter = generate_optimized_cover_letter(
                job_title, 
                company_name, 
                contact_name, 
                plain_desc, 
                resume_text, 
                settings.OPENAI_API_KEY
            )
            
            # Save files
            resume_filename = f"resume_{job_id}.txt"
            cover_letter_filename = f"cover_letter_{job_id}.txt"
            
            try:
                with open(resume_filename, "w", encoding="utf-8") as f:
                    f.write(optimized_resume)
                
                with open(cover_letter_filename, "w", encoding="utf-8") as f:
                    f.write(cover_letter)
                
                # Convert to DOCX if conversion modules available
                try:
                    from resume_convertion import convert_resume
                    from coverletter_convertion import convert_cover_letter
                    
                    convert_resume(resume_filename, resume_filename.replace(".txt", ".docx"))
                    convert_cover_letter(cover_letter_filename, cover_letter_filename.replace(".txt", ".docx"))
                except ImportError:
                    pass  # Conversion modules not available
                
                # Send email
                subject = f"Application for {job_title} at {company_name}"
                send_email_via_sendgrid(
                    settings.SENDGRID_API_KEY,
                    contact_email,
                    subject,
                    cover_letter,
                    optimized_resume,
                    dry_run=dry_run
                )
                
                if not dry_run:
                    emails_sent += 1
                jobs_processed += 1
                
            except Exception as e:
                continue
        
        conn.close()
        
        return {
            "emails_sent": emails_sent,
            "jobs_processed": jobs_processed,
            "message": f"Processed {jobs_processed} jobs, sent {emails_sent} emails"
        }

    @staticmethod
    def check_health() -> Dict[str, Any]:
        """Check health of all services"""
        # Check database connection
        db_connection = False
        try:
            conn = sqlite3.connect("jobs.db")
            c = conn.cursor()
            c.execute("SELECT 1")
            db_connection = True
            conn.close()
        except:
            pass
        
        # Check API connections
        api_connections = {
            "apify": False,
            "apollo": False,
            "sendgrid": False,
            "openai": False
        }
        
        # Check Apify
        if settings.APIFY_TOKEN:
            try:
                import requests
                response = requests.get(
                    "https://api.apify.com/v2/user/me",
                    headers={"Authorization": f"Bearer {settings.APIFY_TOKEN}"},
                    timeout=5
                )
                api_connections["apify"] = response.status_code == 200
            except:
                pass
        
        # Check OpenAI
        if settings.OPENAI_API_KEY:
            try:
                import openai
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.models.list()
                api_connections["openai"] = True
            except:
                pass
        
        # We'll skip checking Apollo and SendGrid to avoid unnecessary API calls
        
        return {
            "status": "healthy",
            "version": "1.0.0",
            "database_connection": db_connection,
            "api_connections": api_connections
        }
