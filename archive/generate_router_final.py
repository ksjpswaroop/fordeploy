from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os, sqlite3

# Import functions from the main pipeline script
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from job_application_pipeline import (
    extract_resume_text, 
    generate_ats_optimized_resume_with_analysis,
    generate_optimized_cover_letter,
    clean_html
)

router = APIRouter()

class GenerateRequest(BaseModel):
    job_id: str
    resume_path: str
    database: str = "jobs.db"
    job_analysis: Dict[str, Any] = None

class GenerateResponse(BaseModel):
    job_id: str
    job_title: str
    company_name: str
    resume_path: str
    cover_letter_path: str

@router.post("/generate", response_model=GenerateResponse)
def generate_materials(request: GenerateRequest):
    """Generate optimized resume and cover letter for a job."""
    # Check if OpenAI API key is set
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY environment variable not set.")
    
    # Extract resume text
    resume_text = extract_resume_text(request.resume_path)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Could not extract text from resume file.")
    
    # Get job details from database
    conn = sqlite3.connect(request.database)
    c = conn.cursor()
    c.execute(
        "SELECT job_title, company_name, description_html, contact_name FROM jobs WHERE job_id=?",
        (request.job_id,)
    )
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Job with ID {request.job_id} not found.")
    
    job_title, company_name, desc_html, contact_name = row
    conn.close()
    
    # Generate materials
    if request.job_analysis:
        # Use provided job analysis
        optimized_resume = generate_ats_optimized_resume_with_analysis(
            resume_text, request.job_analysis, openai_api_key
        )
    else:
        # Use basic job description
        from job_application_pipeline import generate_ats_optimized_resume
        plain_desc = clean_html(desc_html or "")
        optimized_resume = generate_ats_optimized_resume(
            resume_text, plain_desc, job_title, company_name, openai_api_key
        )
    
    # Generate cover letter
    plain_job_desc = clean_html(desc_html or "")
    optimized_cover_letter = generate_optimized_cover_letter(
        job_title, company_name, contact_name, plain_job_desc, resume_text, openai_api_key
    )
    
    # Save files
    resume_filename = f"resume_{request.job_id}.txt"
    cover_letter_filename = f"cover_letter_{request.job_id}.txt"
    
    try:
        with open(resume_filename, "w", encoding="utf-8") as f:
            f.write(optimized_resume)
        
        with open(cover_letter_filename, "w", encoding="utf-8") as f:
            f.write(optimized_cover_letter)
        
        # Convert to DOCX (would happen here)
        
        return GenerateResponse(
            job_id=request.job_id,
            job_title=job_title,
            company_name=company_name,
            resume_path=resume_filename,
            cover_letter_path=cover_letter_filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving generated materials: {str(e)}")
