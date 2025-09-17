from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.dependencies import get_current_user, require_manager
from app.models.user import User, Role
from app.models.job import Job
from app.models.application import Application
from app.models.interview import Interview
from app.models.analytics import RecruiterPerformance, JobAnalytics
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.job import JobResponse, JobCreate, JobUpdate
from app.schemas.application import ApplicationResponse
from app.schemas.interview import InterviewResponse
from app.schemas.analytics import RecruiterPerformanceResponse, JobAnalyticsResponse

router = APIRouter(prefix="/manager", tags=["manager"])

# Team Management
@router.get("/team/recruiters", response_model=List[UserResponse])
async def get_team_recruiters(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Get all recruiters in the manager's team"""
    query = db.query(User).filter(
        User.role_id.in_(
            db.query(Role.id).filter(Role.name == "recruiter")
        )
    )
    
    if active_only:
        query = query.filter(User.is_active == True)
    
    recruiters = query.offset(skip).limit(limit).all()
    return recruiters

@router.get("/team/recruiters/{recruiter_id}", response_model=UserResponse)
async def get_recruiter_details(
    recruiter_id: int,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific recruiter"""
    recruiter = db.query(User).filter(
        User.id == recruiter_id,
        User.role_id.in_(
            db.query(Role.id).filter(Role.name == "recruiter")
        )
    ).first()
    
    if not recruiter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recruiter not found"
        )
    
    return recruiter

@router.put("/team/recruiters/{recruiter_id}", response_model=UserResponse)
async def update_recruiter(
    recruiter_id: int,
    recruiter_update: UserUpdate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Update recruiter information"""
    recruiter = db.query(User).filter(
        User.id == recruiter_id,
        User.role_id.in_(
            db.query(Role.id).filter(Role.name == "recruiter")
        )
    ).first()
    
    if not recruiter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recruiter not found"
        )
    
    # Update recruiter fields
    for field, value in recruiter_update.dict(exclude_unset=True).items():
        setattr(recruiter, field, value)
    
    recruiter.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(recruiter)
    
    return recruiter

# Job Assignments
@router.get("/jobs", response_model=List[JobResponse])
async def get_managed_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    recruiter_id: Optional[int] = Query(None),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Get all jobs managed by the manager's team"""
    query = db.query(Job).join(User, Job.recruiter_id == User.id).filter(
        User.role_id.in_(
            db.query(Role.id).filter(Role.name == "recruiter")
        )
    )
    
    if status:
        query = query.filter(Job.status == status)
    
    if recruiter_id:
        query = query.filter(Job.recruiter_id == recruiter_id)
    
    jobs = query.offset(skip).limit(limit).all()
    return jobs

@router.post("/jobs/{job_id}/assign", response_model=JobResponse)
async def assign_job_to_recruiter(
    job_id: int,
    recruiter_id: int,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Assign a job to a specific recruiter"""
    # Verify job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Verify recruiter exists and is a recruiter
    recruiter = db.query(User).filter(
        User.id == recruiter_id,
        User.role_id.in_(
            db.query(Role.id).filter(Role.name == "recruiter")
        ),
        User.is_active == True
    ).first()
    
    if not recruiter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active recruiter not found"
        )
    
    # Assign job
    job.recruiter_id = recruiter_id
    job.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(job)
    
    return job

# Performance Analytics
@router.get("/analytics/recruiters", response_model=List[RecruiterPerformanceResponse])
async def get_recruiters_performance(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    recruiter_id: Optional[int] = Query(None),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Get performance analytics for recruiters"""
    # Default to last 30 days if no dates provided
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    query = db.query(RecruiterPerformance).filter(
        RecruiterPerformance.period_start >= start_date,
        RecruiterPerformance.period_end <= end_date
    )
    
    if recruiter_id:
        query = query.filter(RecruiterPerformance.recruiter_id == recruiter_id)
    
    performance_data = query.all()
    return performance_data

@router.get("/analytics/jobs", response_model=List[JobAnalyticsResponse])
async def get_jobs_analytics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    job_id: Optional[int] = Query(None),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Get analytics for jobs managed by the team"""
    # Default to last 30 days if no dates provided
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    query = db.query(JobAnalytics).filter(
        JobAnalytics.date >= start_date.date(),
        JobAnalytics.date <= end_date.date()
    )
    
    if job_id:
        query = query.filter(JobAnalytics.job_id == job_id)
    
    analytics_data = query.all()
    return analytics_data

# Application Oversight
@router.get("/applications", response_model=List[ApplicationResponse])
async def get_team_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    recruiter_id: Optional[int] = Query(None),
    job_id: Optional[int] = Query(None),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Get applications managed by the team"""
    query = db.query(Application).join(Job, Application.job_id == Job.id).join(
        User, Job.recruiter_id == User.id
    ).filter(
        User.role_id.in_(
            db.query(Role.id).filter(Role.name == "recruiter")
        )
    )
    
    if status:
        query = query.filter(Application.status == status)
    
    if recruiter_id:
        query = query.filter(Job.recruiter_id == recruiter_id)
    
    if job_id:
        query = query.filter(Application.job_id == job_id)
    
    applications = query.offset(skip).limit(limit).all()
    return applications

# Interview Oversight
@router.get("/interviews", response_model=List[InterviewResponse])
async def get_team_interviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    recruiter_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Get interviews scheduled by the team"""
    query = db.query(Interview).join(Application, Interview.application_id == Application.id).join(
        Job, Application.job_id == Job.id
    ).join(User, Job.recruiter_id == User.id).filter(
        User.role_id.in_(
            db.query(Role.id).filter(Role.name == "recruiter")
        )
    )
    
    if status:
        query = query.filter(Interview.status == status)
    
    if recruiter_id:
        query = query.filter(Job.recruiter_id == recruiter_id)
    
    if start_date:
        query = query.filter(Interview.scheduled_at >= start_date)
    
    if end_date:
        query = query.filter(Interview.scheduled_at <= end_date)
    
    interviews = query.offset(skip).limit(limit).all()
    return interviews

# Feedback and Reviews
@router.post("/feedback/recruiter/{recruiter_id}")
async def provide_recruiter_feedback(
    recruiter_id: int,
    feedback_data: dict,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Provide feedback to a recruiter"""
    # Verify recruiter exists
    recruiter = db.query(User).filter(
        User.id == recruiter_id,
        User.role_id.in_(
            db.query(Role.id).filter(Role.name == "recruiter")
        )
    ).first()
    
    if not recruiter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recruiter not found"
        )
    
    # Create feedback record (this would typically be a separate model)
    # For now, we'll return a success message
    return {
        "message": "Feedback provided successfully",
        "recruiter_id": recruiter_id,
        "feedback": feedback_data,
        "provided_by": current_user.id,
        "provided_at": datetime.utcnow()
    }

# Team Statistics
@router.get("/statistics/team")
async def get_team_statistics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Get overall team statistics"""
    # Default to last 30 days if no dates provided
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Get team recruiters
    team_recruiters = db.query(User).filter(
        User.role_id.in_(
            db.query(Role.id).filter(Role.name == "recruiter")
        ),
        User.is_active == True
    ).all()
    
    recruiter_ids = [r.id for r in team_recruiters]
    
    # Get statistics
    total_jobs = db.query(Job).filter(
        Job.recruiter_id.in_(recruiter_ids),
        Job.created_at >= start_date,
        Job.created_at <= end_date
    ).count()
    
    total_applications = db.query(Application).join(Job, Application.job_id == Job.id).filter(
        Job.recruiter_id.in_(recruiter_ids),
        Application.created_at >= start_date,
        Application.created_at <= end_date
    ).count()
    
    total_interviews = db.query(Interview).join(
        Application, Interview.application_id == Application.id
    ).join(Job, Application.job_id == Job.id).filter(
        Job.recruiter_id.in_(recruiter_ids),
        Interview.created_at >= start_date,
        Interview.created_at <= end_date
    ).count()
    
    hired_count = db.query(Application).join(Job, Application.job_id == Job.id).filter(
        Job.recruiter_id.in_(recruiter_ids),
        Application.status == "hired",
        Application.updated_at >= start_date,
        Application.updated_at <= end_date
    ).count()
    
    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "team_size": len(team_recruiters),
        "total_jobs": total_jobs,
        "total_applications": total_applications,
        "total_interviews": total_interviews,
        "total_hires": hired_count,
        "hire_rate": hired_count / total_applications if total_applications > 0 else 0,
        "applications_per_job": total_applications / total_jobs if total_jobs > 0 else 0
    }