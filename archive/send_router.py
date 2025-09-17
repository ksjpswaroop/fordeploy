from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os, sqlite3

# Import functions from the main pipeline script
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from job_application_pipeline import send_email_via_sendgrid

router = APIRouter()

class SendRequest(BaseModel):
    job_id: str
    resume_path: str
    cover_letter_path: str
    database: str = "jobs.db"
    dry_run: bool = False

class SendResponse(BaseModel):
    job_id: str
    email_sent: bool
    recipient: str
    message: str

@router.post("/send", response_model=SendResponse)
def send_application(request: SendRequest):
    """Send a job application email with resume and cover letter."""
    # Check if SendGrid API key is set
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "").strip()
    if not sendgrid_api_key:
        raise HTTPException(status_code=400, detail="SENDGRID_API_KEY environment variable not set.")
    
    # Get job and contact details from database
    conn = sqlite3.connect(request.database)
    c = conn.cursor()
    c.execute(
        "SELECT job_title, company_name, contact_name, contact_email FROM jobs WHERE job_id=?",
        (request.job_id,)
    )
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Job with ID {request.job_id} not found.")
    
    job_title, company_name, contact_name, contact_email = row
    conn.close()
    
    if not contact_email:
        return SendResponse(
            job_id=request.job_id,
            email_sent=False,
            recipient="",
            message="No contact email available for this job."
        )
    
    # Read resume and cover letter
    try:
        with open(request.resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()
        
        with open(request.cover_letter_path, "r", encoding="utf-8") as f:
            cover_letter_text = f.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading files: {str(e)}")
    
    # Send email
    subject = f"Application for {job_title} at {company_name}"
    try:
        send_email_via_sendgrid(
            sendgrid_api_key,
            contact_email,
            subject,
            cover_letter_text,
            resume_text,
            dry_run=request.dry_run
        )
        
        return SendResponse(
            job_id=request.job_id,
            email_sent=True,
            recipient=contact_email,
            message="Email sent successfully" if not request.dry_run else "Dry run - email not actually sent"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")
