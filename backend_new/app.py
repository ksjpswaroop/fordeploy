"""
AI-Driven Recruitment Backend API
FastAPI application for job automation and recruitment management
"""

import os
import logging
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import uvicorn
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configuration from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recruitment_mvp.db")
APP_NAME = os.getenv("APP_NAME", "Apify Job Automation")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Database setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class JobApplication(Base):
    __tablename__ = "job_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String, index=True)
    company = Column(String, index=True)
    job_url = Column(String)
    status = Column(String, default="pending")
    applied_at = Column(DateTime, default=datetime.utcnow)
    match_score = Column(String)
    email_sent = Column(Boolean, default=False)

class EmailEvent(Base):
    __tablename__ = "email_events"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    event_type = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    message_id = Column(String)
    data = Column(Text)

# Pydantic models
class JobApplicationCreate(BaseModel):
    job_title: str
    company: str
    job_url: str
    match_score: Optional[str] = None

class JobApplicationResponse(BaseModel):
    id: int
    job_title: str
    company: str
    job_url: str
    status: str
    applied_at: datetime
    match_score: Optional[str]
    email_sent: bool

    class Config:
        from_attributes = True

class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    timestamp: datetime
    database: str
    supabase: Optional[str] = None

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    logging.info(f"Starting {APP_NAME} v{APP_VERSION}")
    yield
    # Shutdown
    logging.info("Shutting down application")

# FastAPI app
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="AI-Driven Recruitment Backend API",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {APP_NAME}",
        "version": APP_VERSION,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check Supabase if configured
    supabase_status = None
    if os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        supabase_status = "configured"
    
    return HealthResponse(
        status="healthy",
        app_name=APP_NAME,
        version=APP_VERSION,
        timestamp=datetime.utcnow(),
        database=db_status,
        supabase=supabase_status
    )

@app.get("/api/jobs", response_model=List[JobApplicationResponse])
async def get_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get job applications"""
    jobs = db.query(JobApplication).offset(skip).limit(limit).all()
    return jobs

@app.post("/api/jobs", response_model=JobApplicationResponse)
async def create_job(job: JobApplicationCreate, db: Session = Depends(get_db)):
    """Create a new job application"""
    db_job = JobApplication(**job.dict())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

@app.get("/api/jobs/{job_id}", response_model=JobApplicationResponse)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a specific job application"""
    job = db.query(JobApplication).filter(JobApplication.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.put("/api/jobs/{job_id}/status")
async def update_job_status(job_id: int, status: str, db: Session = Depends(get_db)):
    """Update job application status"""
    job = db.query(JobApplication).filter(JobApplication.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.status = status
    db.commit()
    return {"message": "Status updated successfully"}

@app.post("/api/jobs/{job_id}/apply")
async def apply_to_job(job_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Apply to a job (simulate email sending)"""
    job = db.query(JobApplication).filter(JobApplication.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Simulate background email sending
    def send_application_email():
        # This would integrate with SendGrid/email service
        logging.info(f"Sending application email for job {job_id}: {job.job_title} at {job.company}")
        job.email_sent = True
        job.status = "applied"
        db.commit()
    
    background_tasks.add_task(send_application_email)
    return {"message": "Application submitted successfully"}

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get application statistics"""
    total_jobs = db.query(JobApplication).count()
    applied_jobs = db.query(JobApplication).filter(JobApplication.status == "applied").count()
    pending_jobs = db.query(JobApplication).filter(JobApplication.status == "pending").count()
    
    return {
        "total_jobs": total_jobs,
        "applied_jobs": applied_jobs,
        "pending_jobs": pending_jobs,
        "application_rate": round((applied_jobs / total_jobs * 100) if total_jobs > 0 else 0, 2)
    }

# Email webhook endpoints (for SendGrid integration)
@app.post("/webhooks/sendgrid")
async def sendgrid_webhook(events: List[dict], db: Session = Depends(get_db)):
    """Handle SendGrid webhook events"""
    for event in events:
        email_event = EmailEvent(
            email=event.get("email"),
            event_type=event.get("event"),
            message_id=event.get("sg_message_id"),
            data=str(event)
        )
        db.add(email_event)
    
    db.commit()
    return {"message": "Events processed"}

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug"
    )