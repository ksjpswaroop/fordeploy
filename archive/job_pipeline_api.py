from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from typing import List, Optional, Dict, Any
import os
import json
import shutil
import tempfile
from job_application_pipeline import (
    get_user_parameters,
    run_apify_job,
    save_jobs_to_json,
    init_database,
    upsert_jobs_into_db,
    enrich_contacts,
    extract_resume_text,
    select_matching_jobs,
    select_matching_jobs_with_openai,
    generate_ats_optimized_resume,
    generate_optimized_cover_letter,
    send_email_via_sendgrid,
)
from dotenv import load_dotenv

app = FastAPI()

load_dotenv()

@app.post("/scrape-jobs")
def scrape_jobs(
    title: Optional[str] = Form(None),
    location: Optional[str] = Form("United States"),
    company_names: Optional[str] = Form(None),
    company_ids: Optional[str] = Form(None),
    rows: int = Form(50),
):
    apify_token = os.getenv("APIFY_TOKEN", "").strip()
    if not apify_token:
        raise HTTPException(status_code=400, detail="APIFY_TOKEN not set in environment.")
    run_input = {
        "title": title or "",
        "location": location or "United States",
        "companyName": [x.strip() for x in (company_names or '').split(",") if x.strip()] if company_names else [],
        "companyId": [x.strip() for x in (company_ids or '').split(",") if x.strip()] if company_ids else [],
        "publishedAt": "",
        "rows": rows,
        "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
    }
    jobs = run_apify_job(apify_token, "apify/linkedin-jobs-scraper", run_input)
    return {"jobs": jobs, "count": len(jobs)}

@app.post("/save-jobs")
def save_jobs(jobs: List[Dict[str, Any]], output_path: Optional[str] = None):
    json_path = save_jobs_to_json(jobs, output_path)
    db_path = "jobs.db"
    init_database(db_path)
    upsert_jobs_into_db(db_path, jobs)
    return {"json_path": json_path, "db_path": db_path}

@app.post("/enrich-contacts")
def enrich_contacts_api(db_path: str = Form(...)):
    enrich_contacts(db_path)
    return {"status": "enriched"}

@app.post("/match-jobs")
def match_jobs(
    db_path: str = Form(...),
    resume: UploadFile = File(...),
    threshold: float = Form(0.7),
    use_openai: bool = Form(False),
):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(resume.file, tmp)
        resume_path = tmp.name
    resume_text = extract_resume_text(resume_path)
    os.unlink(resume_path)
    if use_openai:
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        matches = select_matching_jobs_with_openai(db_path, resume_text, openai_api_key, threshold)
    else:
        matches = select_matching_jobs(db_path, resume_text, threshold)
    return {"matches": matches}

@app.post("/generate-documents")
def generate_documents(
    job_id: str = Form(...),
    db_path: str = Form(...),
    resume: UploadFile = File(...),
):
    # Fetch job info from DB
    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT company_name, job_title, description_html FROM jobs WHERE job_id=?", (job_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    company_name, job_title, description_html = row
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(resume.file, tmp)
        resume_path = tmp.name
    resume_text = extract_resume_text(resume_path)
    os.unlink(resume_path)
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    ats_resume = generate_ats_optimized_resume(resume_text, description_html, job_title, company_name, openai_api_key)
    cover_letter = generate_optimized_cover_letter(job_title, company_name, "", description_html, resume_text, openai_api_key)
    return {"ats_resume": ats_resume, "cover_letter": cover_letter}

@app.post("/send-application")
def send_application(
    to_email: str = Form(...),
    subject: str = Form(...),
    content: str = Form(...),
    resume_text: str = Form(...),
    dry_run: bool = Form(True),
):
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")
    send_email_via_sendgrid(
        sendgrid_api_key=sendgrid_api_key,
        to_email=to_email,
        subject=subject,
        content=content,
        resume_text=resume_text,
        dry_run=dry_run,
    )
    return {"status": "sent (or dry run)"}
