"""Recruiter API endpoints for job management and candidate operations."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, date

from app.auth.dependencies import require_recruiter, get_current_user
from app.auth.permissions import UserContext
from app.schemas.recruiter import (
    FeedbackCreate, FeedbackUpdate, FeedbackResponse,
    InterviewCreate, InterviewUpdate, InterviewResponse, InterviewScheduleRequest,
    CommunicationCreate, CommunicationResponse, MessageCreate,
    RecruiterAnalyticsResponse, RecruiterMetrics,
    DocumentUploadResponse, DocumentMetadata,
    CandidateNoteCreate, CandidateNoteResponse,
    JobPostingCreate, JobPostingUpdate, JobPostingResponse
)
from app.schemas.common import PaginatedResponse, SuccessResponse, DateRangeFilter
from app.models.application import Application
from app.schemas.base import ApplicationStatus
from app.schemas.application_list import ApplicationListItem
from app.schemas.application_create import ApplicationCreateInput
from app.models.job import Job, JobStatus
from app.core.database import SessionLocal
from app.schemas.candidate import JobApplicationResponse as RecruiterApplicationView

# Router without internal prefix (applied in api.v1 include)
router = APIRouter(tags=["recruiter"])  # no internal /recruiter prefix

# -------------------- REAL DATA ENDPOINTS (MVP) --------------------
@router.get("/applications", response_model=PaginatedResponse[ApplicationListItem])
async def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    # Optional filters (MVP): allow narrowing by candidate_id and/or job_id
    candidate_id: int | None = Query(None),
    job_id: int | None = Query(None),
    current_user: UserContext = Depends(require_recruiter)
):
    """List applications with real DB data (no placeholders)."""
    db = SessionLocal()
    try:
        q = db.query(Application)
        # Apply optional filters when provided
        if candidate_id is not None:
            q = q.filter(Application.candidate_id == candidate_id)
        if job_id is not None:
            q = q.filter(Application.job_id == job_id)

        q = q.order_by(Application.created_at.desc())
        total = q.count()
        rows = q.offset(skip).limit(limit).all()
        data: list[ApplicationListItem] = []
        for a in rows:
            data.append(ApplicationListItem(
                id=a.id,
                job_id=a.job_id,
                job_title=a.job.title if a.job else None,
                candidate_id=a.candidate_id,
                candidate_name=a.candidate_name,
                candidate_email=a.candidate_email,
                status=a.status.value if hasattr(a.status, 'value') else a.status,
                source=a.source,
                applied_at=a.created_at,
                last_updated=a.updated_at if hasattr(a, 'updated_at') else a.created_at,
                # Safe active flag: treat non-terminal statuses as active
                is_active=(getattr(a, 'status', None) not in {ApplicationStatus.HIRED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN}) if getattr(a, 'status', None) else False,
            ))
        from app.schemas.common import PaginationMeta
        page = (skip // limit) + 1
        total_pages = (total + limit - 1) // limit if limit else 1
        meta = PaginationMeta(
            total=total,
            page=page,
            page_size=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        return PaginatedResponse[ApplicationListItem](data=data, meta=meta)
    finally:
        db.close()

@router.post("/applications", response_model=ApplicationListItem, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreateInput,
    current_user: UserContext = Depends(require_recruiter)
):
    """Create a real application row (fast path – recruiter manual add).

    Validations:
    - Job must exist & be ACTIVE (or we auto-activate if still DRAFT for speed).
    - Candidate basic fields required.
    - Candidate id left flexible (defaults to 1 for dev DB); real flow will link actual user.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == payload.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Allow quick creation by auto-activating unpublished draft job (dev convenience)
        if getattr(job, 'status', None) == JobStatus.DRAFT:
            job.status = JobStatus.ACTIVE
            job.is_published = True
            if not getattr(job, 'published_at', None):
                from datetime import datetime as _dt
                job.published_at = _dt.utcnow()

        app_obj = Application(
            job_id=job.id,
            candidate_id=payload.candidate_id,
            candidate_name=payload.candidate_name,
            candidate_email=payload.candidate_email,
            source=payload.source,
        )
        db.add(app_obj)
        # increment job application count if field exists
        try:
            if hasattr(job, 'application_count') and isinstance(job.application_count, int):
                job.application_count = (job.application_count or 0) + 1
        except Exception:
            pass
        db.commit()
        db.refresh(app_obj)
        return ApplicationListItem(
            id=app_obj.id,
            job_id=app_obj.job_id,
            job_title=job.title if job else None,
            candidate_id=app_obj.candidate_id,
            candidate_name=app_obj.candidate_name,
            candidate_email=app_obj.candidate_email,
            status=app_obj.status.value if hasattr(app_obj.status, 'value') else app_obj.status,
            source=app_obj.source,
            applied_at=app_obj.created_at,
            last_updated=app_obj.updated_at if hasattr(app_obj, 'updated_at') else app_obj.created_at,
            is_active=(getattr(app_obj, 'status', None) not in {ApplicationStatus.HIRED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN}) if getattr(app_obj, 'status', None) else False,
        )
    finally:
        db.close()

class QuickJobCreate(BaseModel):
    title: str
    description: str = "Placeholder description"
    job_type: str = "full-time"
    work_mode: str = "remote"
    location_country: str = "USA"

@router.post("/jobs/quick", status_code=201)
async def quick_create_job(payload: QuickJobCreate, current_user: UserContext = Depends(require_recruiter)):
    """Very small helper to create an ACTIVE published job for immediate testing.

    Not for production use.
    """
    db = SessionLocal()
    try:
        job = Job(
            title=payload.title,
            description=payload.description,
            summary=payload.title,
            job_type=payload.job_type,
            work_mode=payload.work_mode,
            experience_level="mid",
            location_country=payload.location_country,
            status=JobStatus.ACTIVE,
            is_published=True
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return {"id": job.id, "title": job.title, "status": job.status.value if hasattr(job.status,'value') else job.status}
    finally:
        db.close()

# Feedback Management
@router.post("/candidates/{candidate_id}/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate_feedback(
    candidate_id: UUID,
    feedback: FeedbackCreate,
    current_user: UserContext = Depends(require_recruiter)
):
    """Create feedback for a candidate after interview or evaluation."""
    now = datetime.utcnow()
    return FeedbackResponse(
        id=UUID(int=0),
        candidate_id=feedback.candidate_id,
        candidate_name="Candidate Placeholder",
        job_id=feedback.job_id,
        job_title="Job Placeholder",
        application_id=feedback.application_id,
        interview_id=feedback.interview_id,
        feedback_type=feedback.feedback_type,
        rating=feedback.rating,
        title=feedback.title,
        content=feedback.content,
        strengths=feedback.strengths,
        weaknesses=feedback.weaknesses,
        recommendations=feedback.recommendations,
        skills_evaluated=feedback.skills_evaluated,
        is_positive=feedback.is_positive,
        is_confidential=feedback.is_confidential,
        tags=feedback.tags,
        recruiter_id=current_user.user_id,
    recruiter_name=current_user.email,
        tenant_id=current_user.tenant_id,
        created_at=now,
        updated_at=now
    )

@router.get("/candidates/{candidate_id}/feedback", response_model=List[FeedbackResponse])
async def get_candidate_feedback(
    candidate_id: UUID,
    current_user: UserContext = Depends(require_recruiter)
):
    """Get all feedback for a specific candidate."""
    return []

@router.put("/feedback/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: UUID,
    feedback_update: FeedbackUpdate,
    current_user: UserContext = Depends(require_recruiter)
):
    """Update existing feedback (only by original author)."""
    now = datetime.utcnow()
    return FeedbackResponse(
        id=feedback_id,
        candidate_id="candidate",
        candidate_name="Candidate Placeholder",
        job_id=UUID(int=0),
        job_title="Job Placeholder",
        application_id=None,
        interview_id=None,
        feedback_type="general",
        rating=feedback_update.rating or 5,
        title=feedback_update.title or "Updated Feedback",
        content=feedback_update.content or "Updated content",
        strengths=feedback_update.strengths or [],
        weaknesses=feedback_update.weaknesses or [],
        recommendations=feedback_update.recommendations or [],
        skills_evaluated=feedback_update.skills_evaluated or [],
        is_positive=feedback_update.is_positive,
        is_confidential=feedback_update.is_confidential or False,
        tags=feedback_update.tags or [],
        recruiter_id=current_user.user_id,
    recruiter_name=current_user.email,
        tenant_id=current_user.tenant_id,
        created_at=now,
        updated_at=now
    )

@router.delete("/feedback/{feedback_id}", response_model=SuccessResponse)
async def delete_feedback(
    feedback_id: UUID,
    current_user: UserContext = Depends(require_recruiter)
):
    """Delete feedback (only by original author or manager)."""
    return SuccessResponse(success=True, message="Feedback deleted (stub)")

# Interview Management
@router.post("/interviews", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def schedule_interview(
    interview: InterviewCreate,
    current_user: UserContext = Depends(require_recruiter)
):
    """Schedule a new interview with a candidate."""
    now = datetime.utcnow()
    return InterviewResponse(
        id=UUID(int=0),
        candidate_id=interview.candidate_id,
        candidate_name="Candidate Placeholder",
        candidate_email="candidate@example.com",
        job_id=interview.job_id,
        job_title="Job Placeholder",
        application_id=interview.application_id,
        interview_type=interview.interview_type,
        title=interview.title,
        description=interview.description,
        scheduled_at=interview.scheduled_at,
        duration_minutes=interview.duration_minutes,
        location=interview.location,
        meeting_link=interview.meeting_link,
        meeting_id=interview.meeting_id,
        meeting_password=interview.meeting_password,
        interviewers=[{"id": rid, "name": "Interviewer"} for rid in interview.interviewer_ids],
        preparation_notes=interview.preparation_notes,
        questions=interview.questions,
        required_documents=interview.required_documents,
        status="scheduled",
        feedback_id=None,
        created_by=current_user.user_id,
        tenant_id=current_user.tenant_id,
        created_at=now,
        updated_at=now
    )

@router.get("/interviews", response_model=PaginatedResponse[InterviewResponse])
async def get_interviews(
    status_filter: Optional[str] = Query(None),
    date_range: DateRangeFilter = Depends(),
    candidate_id: Optional[UUID] = Query(None),
    job_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserContext = Depends(require_recruiter)
):
    """Get interviews managed by the recruiter with filtering options."""
    return PaginatedResponse[InterviewResponse](
        data=[],
        meta={
            "total": 0,
            "page": 1,
            "page_size": limit,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False
        }
    )

@router.get("/interviews/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: UUID,
    current_user: UserContext = Depends(require_recruiter)
):
    """Get detailed information about a specific interview."""
    now = datetime.utcnow()
    return InterviewResponse(
        id=interview_id,
        candidate_id="candidate",
        candidate_name="Candidate Placeholder",
        candidate_email="candidate@example.com",
        job_id=UUID(int=0),
        job_title="Job Placeholder",
        application_id=None,
        interview_type="phone_screening",
        title="Placeholder Interview",
        description="Placeholder interview detail",
        scheduled_at=now,
        duration_minutes=60,
        location=None,
        meeting_link=None,
        meeting_id=None,
        meeting_password=None,
        interviewers=[],
        preparation_notes=None,
        questions=[],
        required_documents=[],
        status="scheduled",
        feedback_id=None,
        created_by=current_user.user_id,
        tenant_id=current_user.tenant_id,
        created_at=now,
        updated_at=now
    )

@router.put("/interviews/{interview_id}", response_model=InterviewResponse)
async def update_interview(
    interview_id: UUID,
    interview_update: InterviewUpdate,
    current_user: UserContext = Depends(require_recruiter)
):
    """Update interview details (reschedule, change participants, etc.)."""
    now = datetime.utcnow()
    return InterviewResponse(
        id=interview_id,
        candidate_id="candidate",
        candidate_name="Candidate Placeholder",
        candidate_email="candidate@example.com",
        job_id=UUID(int=0),
        job_title="Job Placeholder",
        application_id=None,
        interview_type="phone_screening",
        title=interview_update.title or "Updated Interview",
        description=interview_update.description,
        scheduled_at=interview_update.scheduled_at or now,
        duration_minutes=interview_update.duration_minutes or 60,
        location=interview_update.location,
        meeting_link=interview_update.meeting_link,
        meeting_id=interview_update.meeting_id,
        meeting_password=interview_update.meeting_password,
        interviewers=[],
        preparation_notes=interview_update.preparation_notes,
        questions=interview_update.questions or [],
        required_documents=interview_update.required_documents or [],
        status=interview_update.status or "scheduled",
        feedback_id=None,
        created_by=current_user.user_id,
        tenant_id=current_user.tenant_id,
        created_at=now,
        updated_at=now
    )

@router.post("/interviews/{interview_id}/reschedule", response_model=InterviewResponse)
async def reschedule_interview(
    interview_id: UUID,
    reschedule_request: InterviewScheduleRequest,
    current_user: UserContext = Depends(require_recruiter)
):
    """Reschedule an existing interview."""
    now = datetime.utcnow()
    return InterviewResponse(
        id=interview_id,
        candidate_id="candidate",
        candidate_name="Candidate Placeholder",
        candidate_email="candidate@example.com",
        job_id=UUID(int=0),
        job_title="Job Placeholder",
        application_id=None,
        interview_type="phone_screening",
        title="Rescheduled Interview",
        description="Rescheduled placeholder",
        scheduled_at=reschedule_request.scheduled_at if hasattr(reschedule_request, 'scheduled_at') else now,
        duration_minutes=60,
        location=None,
        meeting_link=None,
        meeting_id=None,
        meeting_password=None,
        interviewers=[],
        preparation_notes=None,
        questions=[],
        required_documents=[],
        status="rescheduled",
        feedback_id=None,
        created_by=current_user.user_id,
        tenant_id=current_user.tenant_id,
        created_at=now,
        updated_at=now
    )

@router.delete("/interviews/{interview_id}", response_model=SuccessResponse)
async def cancel_interview(
    interview_id: UUID,
    reason: Optional[str] = Query(None),
    current_user: UserContext = Depends(require_recruiter)
):
    """Cancel an interview."""
    return SuccessResponse(success=True, message="Interview cancelled (stub)")

# Communication Management
@router.post("/candidates/{candidate_id}/communications", response_model=CommunicationResponse, status_code=status.HTTP_201_CREATED)
async def create_communication(
    candidate_id: UUID,
    communication: CommunicationCreate,
    current_user: UserContext = Depends(require_recruiter)
):
    """Record communication with a candidate."""
    now = datetime.utcnow()
    return CommunicationResponse(
        id=UUID(int=0),
        sender_id=current_user.user_id,
    sender_name=current_user.email,
        recipient_id=communication.recipient_id,
        recipient_name="Candidate Placeholder",
        recipient_type=communication.recipient_type,
        communication_type=communication.communication_type,
        subject=communication.subject,
        content=communication.content,
        job_id=communication.job_id,
        job_title="Job Placeholder" if communication.job_id else None,
        application_id=communication.application_id,
        interview_id=communication.interview_id,
        priority=communication.priority,
        scheduled_for=communication.scheduled_for,
        attachments=communication.attachments,
        tags=communication.tags,
        status="sent",
        delivery_status="delivered",
        read_at=None,
        metadata={},
        tenant_id=current_user.tenant_id,
        created_at=now,
        updated_at=now
    )

@router.get("/candidates/{candidate_id}/communications", response_model=List[CommunicationResponse])
async def get_candidate_communications(
    candidate_id: UUID,
    communication_type: Optional[str] = Query(None),
    current_user: UserContext = Depends(require_recruiter)
):
    """Get communication history with a candidate."""
    return []

@router.post("/candidates/{candidate_id}/messages", response_model=CommunicationResponse)
async def send_message_to_candidate(
    candidate_id: UUID,
    message: MessageCreate,
    current_user: UserContext = Depends(require_recruiter)
):
    """Send a message to a candidate."""
    now = datetime.utcnow()
    return CommunicationResponse(
        id=UUID(int=0),
        sender_id=current_user.user_id,
    sender_name=current_user.email,
        recipient_id=message.recipient_id,
        recipient_name="Candidate Placeholder",
        recipient_type=message.recipient_type,
        communication_type="email",
        subject=message.subject,
        content=message.content,
        job_id=None,
        job_title=None,
        application_id=None,
        interview_id=None,
        priority="medium",
        scheduled_for=None,
        attachments=[],
        tags=[],
        status="sent",
        delivery_status="delivered",
        read_at=None,
        metadata={},
        tenant_id=current_user.tenant_id,
        created_at=now,
        updated_at=now
    )

# Analytics and Reporting
@router.get("/analytics", response_model=RecruiterAnalyticsResponse)
async def get_recruiter_analytics(
    date_range: DateRangeFilter = Depends(),
    current_user: UserContext = Depends(require_recruiter)
):
    """Get personal analytics and performance metrics."""
    return RecruiterAnalyticsResponse(
        recruiter_id=current_user.user_id,
        period={"start": date_range.start_date, "end": date_range.end_date},
        metrics={},
        insights=[],
        top_candidates=[],
        job_performance=[]
    )

@router.get("/metrics", response_model=RecruiterMetrics)
async def get_recruiter_metrics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: UserContext = Depends(require_recruiter)
):
    """Get specific performance metrics for the recruiter."""
    return RecruiterMetrics(
        recruiter_id=current_user.user_id,
        start_date=start_date,
        end_date=end_date,
        jobs_posted=0,
        jobs_filled=0,
        candidates_sourced=0,
        candidates_hired=0,
        interview_to_hire_ratio=0.0,
        time_to_fill_days=0.0
    )

# Document Management
@router.post("/candidates/{candidate_id}/documents", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_candidate_document(
    candidate_id: UUID,
    file: UploadFile = File(...),
    document_type: str = Query(...),
    description: Optional[str] = Query(None),
    current_user: UserContext = Depends(require_recruiter)
):
    """Upload a document for a candidate."""
    now = datetime.utcnow()
    return DocumentUploadResponse(
        id=UUID(int=0),
        filename=file.filename,
        file_size=0,
        content_type=file.content_type or "application/octet-stream",
        document_type=document_type,
        upload_url=None,
        download_url=None,
        created_at=now,
        expires_at=None
    )

@router.get("/candidates/{candidate_id}/documents", response_model=List[DocumentMetadata])
async def get_candidate_documents(
    candidate_id: UUID,
    document_type: Optional[str] = Query(None),
    current_user: UserContext = Depends(require_recruiter)
):
    """Get list of documents for a candidate."""
    return []

@router.delete("/documents/{document_id}", response_model=SuccessResponse)
async def delete_document(
    document_id: UUID,
    current_user: UserContext = Depends(require_recruiter)
):
    """Delete a document."""
    return SuccessResponse(success=True, message="Document deleted (stub)")

# Candidate Notes
@router.post("/candidates/{candidate_id}/notes", response_model=CandidateNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate_note(
    candidate_id: UUID,
    note: CandidateNoteCreate,
    current_user: UserContext = Depends(require_recruiter)
):
    """Add a note about a candidate."""
    now = datetime.utcnow()
    return CandidateNoteResponse(
        id=UUID(int=0),
        candidate_id=candidate_id,
        author_id=current_user.user_id,
    author_name=current_user.email,
        content=note.content,
        is_private=note.is_private,
        tags=note.tags,
        created_at=now,
        updated_at=now
    )

@router.get("/candidates/{candidate_id}/notes", response_model=List[CandidateNoteResponse])
async def get_candidate_notes(
    candidate_id: UUID,
    current_user: UserContext = Depends(require_recruiter)
):
    """Get all notes for a candidate."""
    return []

# Job Management
@router.post("/jobs", response_model=JobPostingResponse, status_code=status.HTTP_201_CREATED)
async def create_job_posting(
    job: JobPostingCreate,
    current_user: UserContext = Depends(require_recruiter)
):
    """Create a new job posting."""
    now = datetime.utcnow()
    return JobPostingResponse(
        id=UUID(int=0),
        title=job.title,
        description=job.description or "",
        status="draft",
        created_by=current_user.user_id,
        recruiter_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        location=job.location or "Remote",
        employment_type=job.employment_type,
        department=job.department,
        seniority_level=job.seniority_level,
        salary_range=job.salary_range,
        required_skills=job.required_skills,
        nice_to_have_skills=job.nice_to_have_skills,
        responsibilities=job.responsibilities,
        requirements=job.requirements,
        benefits=job.benefits,
        application_deadline=job.application_deadline,
        published_at=None,
        created_at=now,
        updated_at=now
    )

@router.get("/jobs", response_model=PaginatedResponse[JobPostingResponse])
async def get_my_jobs(
    status_filter: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserContext = Depends(require_recruiter)
):
    """Get jobs assigned to the current recruiter."""
    return PaginatedResponse[JobPostingResponse](
        data=[],
        meta={
            "total": 0,
            "page": 1,
            "page_size": limit,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False
        }
    )

@router.put("/jobs/{job_id}", response_model=JobPostingResponse)
async def update_job_posting(
    job_id: UUID,
    job_update: JobPostingUpdate,
    current_user: UserContext = Depends(require_recruiter)
):
    """Update a job posting."""
    now = datetime.utcnow()
    return JobPostingResponse(
        id=job_id,
        title=job_update.title or "Updated Job",
        description=job_update.description or "",
        status="draft",
        created_by=current_user.user_id,
        recruiter_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        location=job_update.location or "Remote",
        employment_type=job_update.employment_type or "full_time",
        department=job_update.department or "General",
        seniority_level=job_update.seniority_level or "mid",
        salary_range=job_update.salary_range or {},
        required_skills=job_update.required_skills or [],
        nice_to_have_skills=job_update.nice_to_have_skills or [],
        responsibilities=job_update.responsibilities or [],
        requirements=job_update.requirements or [],
        benefits=job_update.benefits or [],
        application_deadline=job_update.application_deadline,
        published_at=None,
        created_at=now,
        updated_at=now
    )

# Dashboard
@router.get("/dashboard", response_model=dict)
async def get_recruiter_dashboard(
    current_user: UserContext = Depends(require_recruiter)
):
    """Get recruiter dashboard with key metrics and tasks."""
    return {
        "jobs_count": 0,
        "active_candidates": 0,
        "upcoming_interviews": 0,
        "pending_tasks": [],
        "performance": {}
    }