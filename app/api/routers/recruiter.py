from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from app.core.database import get_db
from app.api.dependencies import get_current_user, require_recruiter, require_password_fresh
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.interview import Interview
from app.schemas.job import JobCreate, JobUpdate, JobResponse, JobListResponse
from app.schemas.application import (
    ApplicationResponse, ApplicationUpdate, ApplicationListResponse,
    ApplicationStatusUpdate
)
from app.schemas.interview import (
    InterviewCreate, InterviewUpdate, InterviewResponse, InterviewListResponse,
    InterviewSchedule, InterviewFeedback
)
from app.schemas.analytics import (
    RecruitmentMetrics, JobAnalytics, RecruiterPerformance,
    PipelineAnalytics, AnalyticsFilter
)
from app.schemas.communication import (
    MessageCreate, MessageResponse, MessageListResponse,
    EmailTemplateResponse, CommunicationHistory
)

router = APIRouter(prefix="/recruiter", tags=["recruiter"], dependencies=[Depends(require_password_fresh)])

# Job Management
@router.get("/jobs", response_model=JobListResponse)
async def get_my_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Get jobs assigned to the current recruiter
    """
    query = db.query(Job).filter(Job.recruiter_id == current_user.id)
    
    if status:
        query = query.filter(Job.status == status)
    
    if search:
        query = query.filter(
            Job.title.ilike(f"%{search}%") |
            Job.description.ilike(f"%{search}%")
        )
    
    total = query.count()
    jobs = query.offset(skip).limit(limit).all()
    
    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        skip=skip,
        limit=limit
    )

@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Create a new job posting
    """
    job = Job(
        **job_data.model_dump(),
        recruiter_id=current_user.id,
        created_by=current_user.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobResponse.model_validate(job)

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Get a specific job by ID (only if assigned to recruiter)
    """
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not assigned to you"
        )
    
    return JobResponse.model_validate(job)

@router.put("/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdate,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Update a job posting
    """
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not assigned to you"
        )
    
    for field, value in job_data.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return JobResponse.model_validate(job)

# Application Management
@router.get("/applications", response_model=ApplicationListResponse)
async def get_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    job_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Get applications for jobs assigned to the current recruiter
    """
    # Get job IDs assigned to this recruiter
    recruiter_job_ids = db.query(Job.id).filter(Job.recruiter_id == current_user.id).subquery()
    
    query = db.query(Application).filter(
        Application.job_id.in_(recruiter_job_ids)
    )
    
    if job_id:
        query = query.filter(Application.job_id == job_id)
    
    if status:
        query = query.filter(Application.status == status)
    
    if search:
        query = query.join(User).filter(
            User.first_name.ilike(f"%{search}%") |
            User.last_name.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%")
        )
    
    total = query.count()
    applications = query.offset(skip).limit(limit).all()
    
    return ApplicationListResponse(
        applications=[ApplicationResponse.model_validate(app) for app in applications],
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/applications/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: int,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Get a specific application
    """
    # Verify the application belongs to a job assigned to this recruiter
    application = db.query(Application).join(Job).filter(
        Application.id == application_id,
        Job.recruiter_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or not accessible"
        )
    
    return ApplicationResponse.model_validate(application)

@router.put("/applications/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: int,
    status_data: ApplicationStatusUpdate,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Update application status
    """
    application = db.query(Application).join(Job).filter(
        Application.id == application_id,
        Job.recruiter_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or not accessible"
        )
    
    application.status = status_data.status
    if status_data.notes:
        application.notes = status_data.notes
    application.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(application)
    return ApplicationResponse.model_validate(application)

## Note: Removed deprecated notes update endpoint referencing missing ApplicationNotes schema

# Interview Management
@router.get("/interviews", response_model=InterviewListResponse)
async def get_interviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Get interviews for the current recruiter
    """
    query = db.query(Interview).filter(Interview.interviewer_id == current_user.id)
    
    if status:
        query = query.filter(Interview.status == status)
    
    if date_from:
        query = query.filter(Interview.scheduled_at >= date_from)
    
    if date_to:
        query = query.filter(Interview.scheduled_at <= date_to)
    
    total = query.count()
    interviews = query.offset(skip).limit(limit).all()
    
    return InterviewListResponse(
        interviews=[InterviewResponse.model_validate(interview) for interview in interviews],
        total=total,
        skip=skip,
        limit=limit
    )

@router.post("/interviews", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def schedule_interview(
    interview_data: InterviewCreate,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Schedule a new interview
    """
    # Verify the application belongs to a job assigned to this recruiter
    application = db.query(Application).join(Job).filter(
        Application.id == interview_data.application_id,
        Job.recruiter_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or not accessible"
        )
    
    interview = Interview(
        **interview_data.model_dump(),
        interviewer_id=current_user.id,
        created_by=current_user.id
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return InterviewResponse.model_validate(interview)

@router.put("/interviews/{interview_id}", response_model=InterviewResponse)
async def update_interview(
    interview_id: int,
    interview_data: InterviewUpdate,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Update an interview
    """
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.interviewer_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found or not accessible"
        )
    
    for field, value in interview_data.model_dump(exclude_unset=True).items():
        setattr(interview, field, value)
    
    interview.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(interview)
    return InterviewResponse.model_validate(interview)

@router.put("/interviews/{interview_id}/feedback", response_model=InterviewResponse)
async def submit_interview_feedback(
    interview_id: int,
    feedback_data: InterviewFeedback,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Submit interview feedback
    """
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.interviewer_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found or not accessible"
        )
    
    interview.feedback = feedback_data.feedback
    interview.rating = feedback_data.rating
    interview.recommendation = feedback_data.recommendation
    interview.status = "completed"
    interview.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(interview)
    return InterviewResponse.model_validate(interview)

# Analytics
@router.get("/analytics/performance", response_model=RecruiterPerformance)
async def get_my_performance(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Get performance analytics for the current recruiter
    """
    # This would typically involve complex queries to calculate metrics
    # For now, returning a basic structure
    return RecruiterPerformance(
        recruiter_id=current_user.id,
        recruiter_name=f"{current_user.first_name} {current_user.last_name}",
        jobs_managed=0,  # Calculate from database
        applications_reviewed=0,  # Calculate from database
        interviews_conducted=0,  # Calculate from database
        offers_made=0,  # Calculate from database
        hires_made=0,  # Calculate from database
        avg_time_to_hire_days=0.0,  # Calculate from database
        candidate_satisfaction_score=0.0  # Calculate from database
    )

@router.get("/analytics/jobs", response_model=List[JobAnalytics])
async def get_job_analytics(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Get analytics for jobs managed by the current recruiter
    """
    jobs = db.query(Job).filter(Job.recruiter_id == current_user.id).all()
    
    job_analytics = []
    for job in jobs:
        # Calculate metrics for each job
        analytics = JobAnalytics(
            job_id=job.id,
            job_title=job.title,
            total_applications=0,  # Calculate from database
            qualified_applications=0,  # Calculate from database
            interviews_scheduled=0,  # Calculate from database
            offers_made=0,  # Calculate from database
            hires_made=0,  # Calculate from database
            avg_time_to_fill_days=0.0,  # Calculate from database
            application_sources={},  # Calculate from database
            top_skills_required=[],  # Extract from job requirements
            salary_range_applications={}  # Calculate from database
        )
        job_analytics.append(analytics)
    
    return job_analytics

@router.get("/analytics/pipeline", response_model=PipelineAnalytics)
async def get_pipeline_analytics(
    job_id: Optional[int] = Query(None),
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Get pipeline analytics for the current recruiter
    """
    # This would involve complex queries to analyze the recruitment pipeline
    # For now, returning a basic structure
    return PipelineAnalytics(
        total_candidates_in_pipeline=0,  # Calculate from database
        stages=[],  # Calculate stage-wise metrics
        bottlenecks=[],  # Identify bottlenecks
        avg_pipeline_duration_days=0.0  # Calculate average duration
    )

# Communication
@router.get("/communications", response_model=MessageListResponse)
async def get_communications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    candidate_id: Optional[int] = Query(None),
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Get communication history
    """
    # This would query a messages/communications table
    # For now, returning empty list
    return MessageListResponse(
        messages=[],
        total=0,
        skip=skip,
        limit=limit
    )

@router.post("/communications", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Send a message to a candidate
    """
    # This would create a new message record
    # For now, returning a mock response
    return MessageResponse(
        id=1,
        sender_id=current_user.id,
        recipient_id=message_data.recipient_id,
        subject=message_data.subject,
        content=message_data.content,
        sent_at=datetime.utcnow(),
        read_at=None
    )

@router.get("/email-templates", response_model=List[EmailTemplateResponse])
async def get_email_templates(
    template_type: Optional[str] = Query(None),
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """
    Get available email templates
    """
    # This would query email templates from database
    # For now, returning empty list
    return []