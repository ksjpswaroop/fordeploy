from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from app.core.database import get_db
from app.api.dependencies import get_current_user, require_candidate, require_password_fresh
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.interview import Interview
from app.models.upload import Document
from app.schemas.user import UserResponse, UserUpdate, CandidateProfileUpdate
from app.schemas.job import JobResponse, JobListResponse
from app.schemas.application import (
    ApplicationCreate, ApplicationResponse, ApplicationListResponse,
    ApplicationUpdate
)
from app.schemas.interview import (
    InterviewResponse, InterviewListResponse, InterviewUpdate
)
from app.schemas.upload import DocumentResponse, DocumentListResponse
from app.schemas.candidate import (
    CandidateProfileResponse, CandidateApplicationHistory,
    CandidateInterviewHistory, CandidateJobRecommendations
)

router = APIRouter(prefix="/candidate", tags=["candidate"], dependencies=[Depends(require_password_fresh)])

# Profile Management
@router.get("/profile", response_model=CandidateProfileResponse)
async def get_my_profile(
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Get current candidate's profile
    """
    return CandidateProfileResponse.model_validate(current_user)

@router.put("/profile", response_model=CandidateProfileResponse)
async def update_my_profile(
    profile_data: CandidateProfileUpdate,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Update current candidate's profile
    """
    for field, value in profile_data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return CandidateProfileResponse.model_validate(current_user)

# Job Search and Browsing
@router.get("/jobs", response_model=JobListResponse)
async def browse_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    experience_level: Optional[str] = Query(None),
    salary_min: Optional[int] = Query(None),
    salary_max: Optional[int] = Query(None),
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Browse available jobs with filters
    """
    query = db.query(Job).filter(Job.status == "active")
    
    if search:
        query = query.filter(
            Job.title.ilike(f"%{search}%") |
            Job.description.ilike(f"%{search}%") |
            Job.requirements.ilike(f"%{search}%")
        )
    
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    
    if job_type:
        query = query.filter(Job.job_type == job_type)
    
    if experience_level:
        query = query.filter(Job.experience_level == experience_level)
    
    if salary_min:
        query = query.filter(Job.salary_min >= salary_min)
    
    if salary_max:
        query = query.filter(Job.salary_max <= salary_max)
    
    total = query.count()
    jobs = query.offset(skip).limit(limit).all()
    
    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_details(
    job_id: int,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific job
    """
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.status == "active"
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not available"
        )
    
    return JobResponse.model_validate(job)

@router.get("/jobs/recommendations", response_model=CandidateJobRecommendations)
async def get_job_recommendations(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Get personalized job recommendations for the candidate
    """
    # This would typically involve ML algorithms to match candidate profile with jobs
    # For now, returning basic recommendations based on candidate's skills/experience
    
    recommended_jobs = db.query(Job).filter(
        Job.status == "active"
    ).limit(limit).all()
    
    return CandidateJobRecommendations(
        recommended_jobs=[JobResponse.model_validate(job) for job in recommended_jobs],
        match_reasons=["Skills match", "Experience level", "Location preference"],
        total_recommendations=len(recommended_jobs)
    )

# Application Management
@router.get("/applications", response_model=ApplicationListResponse)
async def get_my_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Get candidate's job applications
    """
    query = db.query(Application).filter(Application.candidate_id == current_user.id)
    
    if status:
        query = query.filter(Application.status == status)
    
    total = query.count()
    applications = query.offset(skip).limit(limit).all()
    
    return ApplicationListResponse(
        applications=[ApplicationResponse.model_validate(app) for app in applications],
        total=total,
        skip=skip,
        limit=limit
    )

@router.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_for_job(
    application_data: ApplicationCreate,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Apply for a job
    """
    # Check if job exists and is active
    job = db.query(Job).filter(
        Job.id == application_data.job_id,
        Job.status == "active"
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not available"
        )
    
    # Check if candidate has already applied
    existing_application = db.query(Application).filter(
        Application.job_id == application_data.job_id,
        Application.candidate_id == current_user.id
    ).first()
    
    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied for this job"
        )
    
    application = Application(
        **application_data.model_dump(),
        candidate_id=current_user.id,
        status="submitted"
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return ApplicationResponse.model_validate(application)

@router.get("/applications/{application_id}", response_model=ApplicationResponse)
async def get_application_details(
    application_id: int,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific application
    """
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.candidate_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    return ApplicationResponse.model_validate(application)

@router.put("/applications/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: int,
    application_data: ApplicationUpdate,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Update an application (only if still in draft or submitted status)
    """
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.candidate_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status not in ["draft", "submitted"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update application in current status"
        )
    
    for field, value in application_data.model_dump(exclude_unset=True).items():
        setattr(application, field, value)
    
    application.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(application)
    return ApplicationResponse.model_validate(application)

@router.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_application(
    application_id: int,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Withdraw an application
    """
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.candidate_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status in ["hired", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot withdraw application in current status"
        )
    
    application.status = "withdrawn"
    application.updated_at = datetime.utcnow()
    db.commit()

# Interview Management
@router.get("/interviews", response_model=InterviewListResponse)
async def get_my_interviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    upcoming_only: bool = Query(False),
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Get candidate's interviews
    """
    # Get interviews through applications
    query = db.query(Interview).join(Application).filter(
        Application.candidate_id == current_user.id
    )
    
    if status:
        query = query.filter(Interview.status == status)
    
    if upcoming_only:
        query = query.filter(Interview.scheduled_at > datetime.utcnow())
    
    total = query.count()
    interviews = query.offset(skip).limit(limit).all()
    
    return InterviewListResponse(
        interviews=[InterviewResponse.model_validate(interview) for interview in interviews],
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/interviews/{interview_id}", response_model=InterviewResponse)
async def get_interview_details(
    interview_id: int,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific interview
    """
    interview = db.query(Interview).join(Application).filter(
        Interview.id == interview_id,
        Application.candidate_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    return InterviewResponse.model_validate(interview)

@router.put("/interviews/{interview_id}/confirm", response_model=InterviewResponse)
async def confirm_interview(
    interview_id: int,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Confirm attendance for an interview
    """
    interview = db.query(Interview).join(Application).filter(
        Interview.id == interview_id,
        Application.candidate_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    if interview.status != "scheduled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview cannot be confirmed in current status"
        )
    
    interview.status = "confirmed"
    interview.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(interview)
    return InterviewResponse.model_validate(interview)

@router.put("/interviews/{interview_id}/reschedule", response_model=InterviewResponse)
async def request_interview_reschedule(
    interview_id: int,
    reschedule_data: InterviewUpdate,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Request to reschedule an interview
    """
    interview = db.query(Interview).join(Application).filter(
        Interview.id == interview_id,
        Application.candidate_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    if interview.status not in ["scheduled", "confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview cannot be rescheduled in current status"
        )
    
    # Update interview with reschedule request
    if reschedule_data.notes:
        interview.notes = reschedule_data.notes
    interview.status = "reschedule_requested"
    interview.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(interview)
    return InterviewResponse.model_validate(interview)

# Document Management
@router.get("/documents", response_model=DocumentListResponse)
async def get_my_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    document_type: Optional[str] = Query(None),
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Get candidate's uploaded documents
    """
    query = db.query(Document).filter(Document.uploaded_by == current_user.id)
    
    if document_type:
        query = query.filter(Document.document_type == document_type)
    
    total = query.count()
    documents = query.offset(skip).limit(limit).all()
    
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
        skip=skip,
        limit=limit
    )

@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Query(...),
    description: Optional[str] = Query(None),
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Upload a document (resume, cover letter, portfolio, etc.)
    """
    # This would typically involve file validation and storage
    # For now, creating a basic document record
    
    document = Document(
        filename=file.filename,
        original_filename=file.filename,
        file_path=f"/uploads/candidates/{current_user.id}/{file.filename}",
        file_size=0,  # Would be calculated from actual file
        mime_type=file.content_type,
        document_type=document_type,
        description=description,
        uploaded_by=current_user.id
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    return DocumentResponse.model_validate(document)

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Delete a document
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.uploaded_by == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    db.delete(document)
    db.commit()

# Application History and Analytics
@router.get("/history/applications", response_model=CandidateApplicationHistory)
async def get_application_history(
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Get candidate's application history with analytics
    """
    applications = db.query(Application).filter(
        Application.candidate_id == current_user.id
    ).all()
    
    # Calculate basic statistics
    total_applications = len(applications)
    status_counts = {}
    for app in applications:
        status_counts[app.status] = status_counts.get(app.status, 0) + 1
    
    return CandidateApplicationHistory(
        applications=[ApplicationResponse.model_validate(app) for app in applications],
        total_applications=total_applications,
        applications_by_status=status_counts,
        success_rate=status_counts.get("hired", 0) / total_applications if total_applications > 0 else 0.0,
        avg_response_time_days=0.0  # Would calculate from actual data
    )

@router.get("/history/interviews", response_model=CandidateInterviewHistory)
async def get_interview_history(
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db)
):
    """
    Get candidate's interview history
    """
    interviews = db.query(Interview).join(Application).filter(
        Application.candidate_id == current_user.id
    ).all()
    
    return CandidateInterviewHistory(
        interviews=[InterviewResponse.model_validate(interview) for interview in interviews],
        total_interviews=len(interviews),
        completed_interviews=len([i for i in interviews if i.status == "completed"]),
        avg_rating=0.0,  # Would calculate from actual ratings
        upcoming_interviews=len([i for i in interviews if i.scheduled_at > datetime.utcnow()])
    )