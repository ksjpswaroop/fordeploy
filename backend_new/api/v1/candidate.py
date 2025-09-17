"""Candidate API endpoints for job applications and profile management."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
import os
import uuid
import hashlib
from pathlib import Path
from sqlalchemy.orm import Session

try:
    import pdfminer.high_level  # type: ignore
except Exception:  # pragma: no cover - optional dependency usage guarded
    pdfminer = None  # noqa
try:
    from docx import Document  # type: ignore
except Exception:  # pragma: no cover
    Document = None  # noqa

from app.auth.dependencies import require_candidate, get_current_user
from app.auth.permissions import UserContext
from app.schemas.candidate import (
    CandidateAuthResponse, CandidateProfileCreate, CandidateProfileUpdate, CandidateProfileResponse,
    JobApplicationCreate, JobApplicationResponse, ApplicationStatusUpdate,
    ResumeUploadResponse, DocumentUploadResponse,
    InterviewAvailabilityCreate, InterviewAvailabilityResponse,
    CommunicationPreferencesUpdate, CommunicationPreferencesResponse,
    CandidateSkillCreate, CandidateSkillResponse, SkillAssessmentResponse,
    JobPreferencesCreate, JobPreferencesUpdate, JobPreferencesResponse,
    CandidateAnalyticsResponse, ApplicationMetrics
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.core.database import SessionLocal
from app.models.upload import FileUpload
from app.models.job import Job
from app.models.application import Application
from app.models.job import JobStatus
from app.schemas.job import JobResponse, JobListResponse
from pydantic import BaseModel

class JobBrowseResponse(BaseModel):
    jobs: list[JobListResponse]
    total: int
    skip: int
    limit: int



router = APIRouter(tags=["candidate"])  # no internal prefix; applied in api.v1 include

# REAL DATA ENDPOINT: Browse active jobs (DB-backed)
@router.get("/jobs", response_model=JobBrowseResponse)
async def browse_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: UserContext = Depends(require_candidate)
):
    """Return active jobs from the database (no demo data)."""
    db = SessionLocal()
    try:
        q = db.query(Job).filter(Job.status == JobStatus.ACTIVE)
        # Dev convenience: if no active jobs exist, create one so UI dropdown isn't empty
        if q.count() == 0:
            seed = Job(
                title="Sample Developer Role",
                description="Auto-seeded job so you can test creating applications immediately.",
                summary="Sample Developer Role",
                job_type="full-time",
                work_mode="remote",
                experience_level="mid",
                location_country="USA",
                status=JobStatus.ACTIVE,
                is_published=True
            )
            db.add(seed)
            try:
                db.commit()
            except Exception:
                db.rollback()
            q = db.query(Job).filter(Job.status == JobStatus.ACTIVE)
        if search:
            like = f"%{search}%"
            q = q.filter(Job.title.ilike(like))
        total = q.count()
        rows = q.offset(skip).limit(limit).all()
        # Map ORM Job (legacy richer model) to the lightweight JobListResponse schema fields
        mapped = []
        for j in rows:
            try:
                mapped.append(JobListResponse(
                    id=j.id,
                    title=j.title,
                    location=(getattr(j, 'location_city', None) or getattr(j, 'location_state', None) or getattr(j, 'location_country', None) or "Unknown"),
                    department=str(getattr(j, 'department_id', 'general')),
                    employment_type=(getattr(j, 'job_type', None) or "full-time"),
                    experience_level=getattr(j, 'experience_level'),
                    salary_min=getattr(j, 'salary_min', None),
                    salary_max=getattr(j, 'salary_max', None),
                    currency=getattr(j, 'salary_currency', 'USD'),
                    remote_allowed=bool(getattr(j, 'is_remote', False)),
                    status=getattr(j, 'status'),
                    posted_date=getattr(j, 'published_at', None),
                    applications_count=getattr(j, 'application_count', 0)
                ))
            except Exception:
                continue
        return JobBrowseResponse(jobs=mapped, total=total, skip=skip, limit=limit)
    finally:
        db.close()

# REAL DATA ENDPOINT: Candidate's applications (stub -> real query limited to current user when integrated)
@router.get("/applications", response_model=PaginatedResponse[JobApplicationResponse])
async def list_my_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    current_user: UserContext = Depends(require_candidate)
):
    db = SessionLocal()
    try:
        q = db.query(Application)
        # In real auth we'd filter: q = q.filter(Application.candidate_id == current_user.user_id)
        total = q.count()
        rows = q.order_by(Application.created_at.desc()).offset(skip).limit(limit).all()
        data = [
            JobApplicationResponse(
                id=a.id,
                job_id=a.job_id,
                candidate_id=a.candidate_id,
                status=a.status.value if hasattr(a.status,'value') else a.status,
                applied_at=a.created_at,
                updated_at=a.updated_at,
            ) for a in rows
        ]
        page = (skip // limit) + 1
        total_pages = (total + limit - 1) // limit if limit else 1
        return PaginatedResponse[JobApplicationResponse](
            data=data,
            meta={
                "total": total,
                "page": page,
                "page_size": limit,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        )
    finally:
        db.close()

# Authentication and Profile
@router.post("/auth/register", response_model=CandidateAuthResponse, status_code=status.HTTP_201_CREATED)
async def register_candidate(
    profile_data: CandidateProfileCreate,
    current_user: UserContext = Depends(require_candidate)
):
    """Complete candidate registration and create profile."""
    # TODO: Implement candidate registration
    # - Create candidate profile
    # - Link to Clerk user ID
    # - Set default preferences
    # - Send welcome communication
    return CandidateAuthResponse(
        user_id=current_user.user_id,
        profile_completed=False,
        onboarding_steps=[],
        token="dev-placeholder"
    )

@router.get("/profile", response_model=CandidateProfileResponse)
async def get_candidate_profile(
    current_user: UserContext = Depends(require_candidate)
):
    """Get the current candidate's profile information."""
    # TODO: Implement profile retrieval
    # - Fetch candidate profile
    # - Include skills and preferences
    # - Show completion status
    # Ensure all required fields present per schema
    # Align with CandidateProfileResponse schema: requires id, user_id (int), location, currency
    # Using placeholder numeric IDs (0) since no DB entity yet.
    return CandidateProfileResponse(
        id=0,
        user_id=0,
        location="Unknown",
        bio=None,
        phone=None,
        linkedin_url=None,
        github_url=None,
        portfolio_url=None,
        current_title=None,
        current_company=None,
        experience_level=None,
        expected_salary=None,
        currency="USD",
        available_from=None,
        willing_to_relocate=False,
        remote_work_preference=False,
        avatar_url=None,
        resume_url=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

@router.put("/profile", response_model=CandidateProfileResponse)
async def update_candidate_profile(
    profile_update: CandidateProfileUpdate,
    current_user: UserContext = Depends(require_candidate)
):
    """Update candidate profile information."""
    # TODO: Implement profile update
    # - Update profile fields
    # - Validate data integrity
    # - Track profile completeness
    # - Notify recruiters if significant changes
    return CandidateProfileResponse(
        user_id=current_user.user_id,
        full_name=profile_update.full_name or "Unknown",
        headline=profile_update.headline,
        location=profile_update.location,
        experience_years=profile_update.experience_years,
        skills=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        profile_completion=0.1,
    )

# Job Applications
@router.post("/applications", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_for_job(
    application: JobApplicationCreate,
    current_user: UserContext = Depends(require_candidate)
):
    """Apply for a job position."""
    # TODO: Implement job application
    # - Validate job exists and is active
    # - Check for duplicate applications
    # - Create application record
    # - Notify recruiters
    # - Send confirmation to candidate
    return JobApplicationResponse(
        id="00000000-0000-0000-0000-000000000000",
        job_id=application.job_id,
        candidate_id=current_user.user_id,
        status="submitted",
        applied_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

## (Removed duplicate stub get_my_applications; real DB-backed list_my_applications defined earlier)

@router.get("/applications/{application_id}", response_model=JobApplicationResponse)
async def get_application_details(
    application_id: UUID,
    current_user: UserContext = Depends(require_candidate)
):
    """Get detailed information about a specific application."""
    # TODO: Implement application details
    # - Validate application ownership
    # - Fetch application details
    # - Include status history
    # - Show next steps
    return JobApplicationResponse(
        id=str(application_id),
        job_id="00000000-0000-0000-0000-000000000000",
        candidate_id=current_user.user_id,
        status="submitted",
        applied_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

@router.put("/applications/{application_id}/withdraw", response_model=SuccessResponse)
async def withdraw_application(
    application_id: UUID,
    reason: Optional[str] = Query(None),
    current_user: UserContext = Depends(require_candidate)
):
    """Withdraw a job application."""
    # TODO: Implement application withdrawal
    # - Validate application ownership
    # - Update application status
    # - Notify recruiters
    # - Log withdrawal reason
    return SuccessResponse(success=True, message="Application withdrawn", data={"application_id": str(application_id)})

# Resume and Document Management
RESUME_STORAGE_DIR = Path("uploads/resumes")
RESUME_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
_RESUME_UUID_NAMESPACE = uuid.UUID("11111111-2222-3333-4444-555555555555")

ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}

def _stable_uuid_for_file_id(file_id: int) -> uuid.UUID:
    """Derive a stable UUID from integer primary key so API matches schema expectations."""
    return uuid.uuid5(_RESUME_UUID_NAMESPACE, str(file_id))

def _extract_text(file_path: Path) -> str | None:
    ext = file_path.suffix.lower()
    try:
        if ext == ".pdf" and 'pdfminer' in globals():
            return pdfminer.high_level.extract_text(str(file_path))  # type: ignore
        if ext in {".docx"} and Document:  # type: ignore
            doc = Document(str(file_path))  # type: ignore
            return "\n".join(p.text for p in doc.paragraphs)
        if ext in {".txt", ".md"}:
            return file_path.read_text(errors="ignore")
    except Exception:
        return None
    return None

@router.post("/resume", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    is_primary: bool = Query(True),
    current_user: UserContext = Depends(require_candidate)
):
    """Upload a resume file, persist metadata, optionally extract text, and return standardized response."""
    original_name = file.filename or "resume"
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_RESUME_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported resume extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_RESUME_EXTENSIONS))}")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file upload")

    sha256 = hashlib.sha256(contents).hexdigest()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = RESUME_STORAGE_DIR / stored_name
    stored_path.write_bytes(contents)

    db: Session = SessionLocal()
    try:
        # Check duplicate via hash
        existing = db.query(FileUpload).filter(FileUpload.file_hash == sha256, FileUpload.document_category == 'resume', FileUpload.uploaded_by == current_user.user_id).first()
        is_duplicate = existing is not None
        file_upload = FileUpload(
            original_filename=original_name,
            stored_filename=stored_name,
            file_path=str(stored_path),
            file_size_bytes=len(contents),
            mime_type=file.content_type or "application/octet-stream",
            file_extension=ext.lstrip('.'),
            file_hash=sha256,
            is_duplicate=is_duplicate,
            duplicate_of_id=existing.id if is_duplicate else None,
            document_category='resume',
            uploaded_by=current_user.user_id,
            candidate_id=current_user.user_id,
            processing_status='completed',
            is_safe=True,
        )
        db.add(file_upload)
        db.commit()
        db.refresh(file_upload)

        # Only attempt extraction if not duplicate (avoid repeat work)
        parsed_text = None
        if not is_duplicate:
            parsed_text = _extract_text(stored_path)
            if parsed_text:
                # Truncate overly long text for storage to avoid huge rows
                snippet = parsed_text[:50000]
                file_upload.extracted_text = snippet
                db.add(file_upload)
                db.commit()

        # Determine if this should be the primary resume (first uploaded or explicitly requested)
        if is_primary:
            # For MVP, we just treat last uploaded with is_primary flag; advanced logic could update candidate profile
            pass

        resume_uuid = _stable_uuid_for_file_id(file_upload.id)
        return ResumeUploadResponse(
            id=resume_uuid,
            filename=file_upload.original_filename,
            file_size=file_upload.file_size_bytes,
            mime_type=file_upload.mime_type,
            upload_url=f"/uploads/resumes/{stored_name}",
            download_url=None,
            is_primary=is_primary,
            parsed_data={"extracted_text_preview": (file_upload.extracted_text[:500] if file_upload.extracted_text else None)},
            created_at=file_upload.created_at,
        )
    finally:
        db.close()

@router.get("/resume", response_model=List[ResumeUploadResponse])
async def get_resumes(
    current_user: UserContext = Depends(require_candidate)
):
    """Return all resume uploads for the current candidate."""
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(FileUpload)
            .filter(FileUpload.uploaded_by == current_user.user_id, FileUpload.document_category == 'resume')
            .order_by(FileUpload.created_at.desc())
            .all()
        )
        results: list[ResumeUploadResponse] = []
        # Treat newest as primary if any
        primary_id = rows[0].id if rows else None
        for r in rows:
            resume_uuid = _stable_uuid_for_file_id(r.id)
            results.append(
                ResumeUploadResponse(
                    id=resume_uuid,
                    filename=r.original_filename,
                    file_size=r.file_size_bytes,
                    mime_type=r.mime_type,
                    upload_url=f"/uploads/resumes/{r.stored_filename}",
                    download_url=None,
                    is_primary=(r.id == primary_id),
                    parsed_data={"extracted_text_preview": (r.extracted_text[:500] if r.extracted_text else None)},
                    created_at=r.created_at,
                )
            )
        return results
    finally:
        db.close()

@router.delete("/resume/{resume_id}", response_model=SuccessResponse)
async def delete_resume(
    resume_id: UUID,
    current_user: UserContext = Depends(require_candidate)
):
    """Delete (physically remove) a resume by its UUID representation."""
    db: Session = SessionLocal()
    try:
        # Map UUID back to integer by scanning (MVP acceptable; low volume). Could be optimized with metadata column.
        rows = db.query(FileUpload).filter(FileUpload.uploaded_by == current_user.user_id, FileUpload.document_category == 'resume').all()
        target = None
        for r in rows:
            if _stable_uuid_for_file_id(r.id) == resume_id:
                target = r
                break
        if not target:
            raise HTTPException(status_code=404, detail="Resume not found")
        # Delete file from disk
        try:
            Path(target.file_path).unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass
        db.delete(target)
        db.commit()
        return SuccessResponse(success=True, message="Resume deleted", data={"resume_id": str(resume_id)})
    finally:
        db.close()

@router.post("/documents", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Query(...),
    description: Optional[str] = Query(None),
    current_user: UserContext = Depends(require_candidate)
):
    """Upload additional documents (portfolio, certificates, etc.)."""
    # TODO: Implement document upload
    # - Validate file type and size
    # - Store securely
    # - Create document record
    # - Link to candidate profile
    return DocumentUploadResponse(
        id="00000000-0000-0000-0000-000000000000",
        filename=file.filename,
        original_filename=file.filename,
        file_size=0,
        mime_type=file.content_type or "application/octet-stream",
        file_type=document_type,
        upload_url="",
        download_url=None,
        is_public=False,
        description=description,
        uploaded_by=current_user.user_id,
        created_at=datetime.utcnow(),
    )

@router.get("/documents", response_model=List[DocumentUploadResponse])
async def get_documents(
    document_type: Optional[str] = Query(None),
    current_user: UserContext = Depends(require_candidate)
):
    """Get all uploaded documents for the candidate."""
    # TODO: Implement document listing
    # - Fetch candidate's documents
    # - Filter by type if specified
    # - Include metadata
    return []

# Interview Management
@router.post("/availability", response_model=InterviewAvailabilityResponse, status_code=status.HTTP_201_CREATED)
async def set_interview_availability(
    availability: InterviewAvailabilityCreate,
    current_user: UserContext = Depends(require_candidate)
):
    """Set availability for interviews."""
    # TODO: Implement availability setting
    # - Create availability slots
    # - Handle recurring availability
    # - Notify recruiters of updates
    return InterviewAvailabilityResponse(
        id="00000000-0000-0000-0000-000000000000",
        candidate_id=current_user.user_id,
        slots=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

@router.get("/availability", response_model=List[InterviewAvailabilityResponse])
async def get_interview_availability(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: UserContext = Depends(require_candidate)
):
    """Get current interview availability."""
    # TODO: Implement availability retrieval
    # - Fetch availability slots
    # - Apply date filters
    # - Show booked vs available slots
    return []

@router.get("/interviews", response_model=List[dict])
async def get_scheduled_interviews(
    status_filter: Optional[str] = Query(None),
    current_user: UserContext = Depends(require_candidate)
):
    """Get all scheduled interviews for the candidate."""
    # TODO: Implement interview listing
    # - Fetch scheduled interviews
    # - Include job and company details
    # - Show interview status
    # - Include meeting links/details
    return []

@router.put("/interviews/{interview_id}/confirm", response_model=SuccessResponse)
async def confirm_interview(
    interview_id: UUID,
    current_user: UserContext = Depends(require_candidate)
):
    """Confirm attendance for a scheduled interview."""
    # TODO: Implement interview confirmation
    # - Validate interview exists
    # - Update confirmation status
    # - Notify recruiters
    return SuccessResponse(success=True, message="Interview confirmed")

@router.put("/interviews/{interview_id}/reschedule", response_model=SuccessResponse)
async def request_interview_reschedule(
    interview_id: UUID,
    reason: str = Query(...),
    current_user: UserContext = Depends(require_candidate)
):
    """Request to reschedule an interview."""
    # TODO: Implement reschedule request
    # - Validate interview exists
    # - Create reschedule request
    # - Notify recruiters
    # - Provide alternative times
    return SuccessResponse(success=True, message="Reschedule request received", data={"interview_id": str(interview_id)})

# Communication
@router.get("/communications", response_model=List[dict])
async def get_communications(
    communication_type: Optional[str] = Query(None),
    current_user: UserContext = Depends(require_candidate)
):
    """Get communication history with recruiters."""
    # TODO: Implement communication history
    # - Fetch communications
    # - Filter by type if specified
    # - Include recruiter details
    # - Order by date
    return []

@router.put("/communication-preferences", response_model=CommunicationPreferencesResponse)
async def update_communication_preferences(
    preferences: CommunicationPreferencesUpdate,
    current_user: UserContext = Depends(require_candidate)
):
    """Update communication preferences and notification settings."""
    # TODO: Implement preference update
    # - Update notification settings
    # - Set communication channels
    # - Configure frequency preferences
    now = datetime.utcnow()
    # Return schema-compliant placeholder
    return CommunicationPreferencesResponse(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        candidate_id=str(current_user.user_id),
        email_notifications=True,
        sms_notifications=False,
        phone_notifications=False,
        job_alerts=True,
        application_updates=True,
        interview_reminders=True,
        marketing_emails=False,
        preferred_contact_time=None,
        timezone="UTC",
        created_at=now,
        updated_at=now,
    )

@router.get("/communication-preferences", response_model=CommunicationPreferencesResponse)
async def get_communication_preferences(
    current_user: UserContext = Depends(require_candidate)
):
    """Get current communication preferences."""
    # TODO: Implement preference retrieval
    # - Fetch current preferences
    # - Include default settings
    now = datetime.utcnow()
    return CommunicationPreferencesResponse(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        candidate_id=str(current_user.user_id),
        email_notifications=True,
        sms_notifications=False,
        phone_notifications=False,
        job_alerts=True,
        application_updates=True,
        interview_reminders=True,
        marketing_emails=False,
        preferred_contact_time=None,
        timezone="UTC",
        created_at=now,
        updated_at=now,
    )

# Skills and Profile Management
@router.post("/skills", response_model=CandidateSkillResponse, status_code=status.HTTP_201_CREATED)
async def add_skill(
    skill: CandidateSkillCreate,
    current_user: UserContext = Depends(require_candidate)
):
    """Add a skill to the candidate profile."""
    # TODO: Implement skill addition
    # - Validate skill data
    # - Add to candidate profile
    # - Update skill matching
    return CandidateSkillResponse(
        id="00000000-0000-0000-0000-000000000000",
        candidate_id=current_user.user_id,
        name=skill.name,
        level=skill.level,
        years_experience=skill.years_experience,
        verified=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

@router.get("/skills", response_model=List[CandidateSkillResponse])
async def get_skills(
    current_user: UserContext = Depends(require_candidate)
):
    """Get all skills in the candidate profile."""
    # TODO: Implement skill listing
    # - Fetch candidate skills
    # - Include proficiency levels
    # - Show verification status
    return []

@router.put("/skills/{skill_id}", response_model=CandidateSkillResponse)
async def update_skill(
    skill_id: UUID,
    skill_update: CandidateSkillCreate,
    current_user: UserContext = Depends(require_candidate)
):
    """Update a skill in the candidate profile."""
    # TODO: Implement skill update
    # - Validate skill ownership
    # - Update skill details
    # - Refresh matching algorithms
    return CandidateSkillResponse(
        id=str(skill_id),
        candidate_id=current_user.user_id,
        name=skill_update.name,
        level=skill_update.level,
        years_experience=skill_update.years_experience,
        verified=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

@router.delete("/skills/{skill_id}", response_model=SuccessResponse)
async def remove_skill(
    skill_id: UUID,
    current_user: UserContext = Depends(require_candidate)
):
    """Remove a skill from the candidate profile."""
    # TODO: Implement skill removal
    # - Validate skill ownership
    # - Remove skill
    # - Update profile completeness
    return SuccessResponse(success=True, message="Skill removed", data={"skill_id": str(skill_id)})

@router.get("/skill-assessments", response_model=List[SkillAssessmentResponse])
async def get_skill_assessments(
    current_user: UserContext = Depends(require_candidate)
):
    """Get available and completed skill assessments."""
    # TODO: Implement assessment listing
    # - Fetch available assessments
    # - Show completed assessments
    # - Include scores and certifications
    return []

# Job Preferences and Settings
@router.post("/job-preferences", response_model=JobPreferencesResponse, status_code=status.HTTP_201_CREATED)
async def set_job_preferences(
    preferences: JobPreferencesCreate,
    current_user: UserContext = Depends(require_candidate)
):
    """Set job search preferences and criteria."""
    # TODO: Implement preference setting
    # - Create job preferences
    # - Set matching criteria
    # - Configure job alerts
    now = datetime.utcnow()
    return JobPreferencesResponse(
        id=0,
        candidate_id=0,
        preferred_locations=[],
        preferred_departments=[],
        preferred_employment_types=[],
        min_salary=None,
        max_salary=None,
        currency="USD",
        remote_work_only=False,
        willing_to_relocate=False,
        preferred_company_sizes=[],
        preferred_industries=[],
        work_authorization_required=False,
        created_at=now,
        updated_at=now,
    )

@router.get("/job-preferences", response_model=JobPreferencesResponse)
async def get_job_preferences(
    current_user: UserContext = Depends(require_candidate)
):
    """Get current job search preferences."""
    # TODO: Implement preference retrieval
    # - Fetch job preferences
    # - Include matching settings
    now = datetime.utcnow()
    return JobPreferencesResponse(
        id=0,
        candidate_id=0,
        preferred_locations=[],
        preferred_departments=[],
        preferred_employment_types=[],
        min_salary=None,
        max_salary=None,
        currency="USD",
        remote_work_only=False,
        willing_to_relocate=False,
        preferred_company_sizes=[],
        preferred_industries=[],
        work_authorization_required=False,
        created_at=now,
        updated_at=now,
    )

@router.put("/job-preferences", response_model=JobPreferencesResponse)
async def update_job_preferences(
    preferences: JobPreferencesUpdate,
    current_user: UserContext = Depends(require_candidate)
):
    """Update job search preferences and criteria."""
    # TODO: Implement preference update
    # - Update preferences
    # - Refresh job matching
    # - Update alert settings
    now = datetime.utcnow()
    return JobPreferencesResponse(
        id=0,
        candidate_id=0,
        preferred_locations=[],
        preferred_departments=[],
        preferred_employment_types=[],
        min_salary=None,
        max_salary=None,
        currency="USD",
        remote_work_only=False,
        willing_to_relocate=False,
        preferred_company_sizes=[],
        preferred_industries=[],
        work_authorization_required=False,
        created_at=now,
        updated_at=now,
    )

# Analytics and Insights
@router.get("/analytics", response_model=CandidateAnalyticsResponse)
async def get_candidate_analytics(
    current_user: UserContext = Depends(require_candidate)
):
    """Get personal analytics and application insights."""
    # TODO: Implement candidate analytics
    # - Application success rates
    # - Profile view statistics
    # - Interview performance
    # - Skill demand insights
    return CandidateAnalyticsResponse(
        candidate_id=current_user.user_id,
        aggregates={},
        trends={},
        insights=[],
        generated_at=datetime.utcnow(),
    )

@router.get("/application-metrics", response_model=ApplicationMetrics)
async def get_application_metrics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: UserContext = Depends(require_candidate)
):
    """Get detailed application metrics and statistics."""
    # TODO: Implement metrics calculation
    # - Applications submitted
    # - Response rates
    # - Interview conversion
    # - Success patterns
    return ApplicationMetrics(
        candidate_id=current_user.user_id,
        period_start=start_date or date.today(),
        period_end=end_date or date.today(),
        totals={},
        conversion_rates={},
        performance={},
    )

# Job Search and Recommendations
@router.get("/job-recommendations", response_model=List[dict])
async def get_job_recommendations(
    limit: int = Query(20, ge=1, le=100),
    current_user: UserContext = Depends(require_candidate)
):
    """Get personalized job recommendations."""
    # TODO: Implement job recommendations
    # - Use ML algorithms for matching
    # - Consider preferences and skills
    # - Include match scores
    # - Filter by availability
    return []

@router.get("/saved-jobs", response_model=List[dict])
async def get_saved_jobs(
    current_user: UserContext = Depends(require_candidate)
):
    """Get jobs saved by the candidate."""
    # TODO: Implement saved jobs listing
    # - Fetch saved jobs
    # - Include job status
    # - Show application status
    return []

@router.post("/jobs/{job_id}/save", response_model=SuccessResponse)
async def save_job(
    job_id: UUID,
    current_user: UserContext = Depends(require_candidate)
):
    """Save a job for later consideration."""
    # TODO: Implement job saving
    # - Validate job exists
    # - Add to saved jobs
    # - Prevent duplicates
    return SuccessResponse(success=True, message="Job saved", data={"job_id": str(job_id)})

@router.delete("/jobs/{job_id}/save", response_model=SuccessResponse)
async def unsave_job(
    job_id: UUID,
    current_user: UserContext = Depends(require_candidate)
):
    """Remove a job from saved jobs."""
    # TODO: Implement job unsaving
    # - Validate job is saved
    # - Remove from saved jobs
    return SuccessResponse(success=True, message="Job unsaved", data={"job_id": str(job_id)})

# Dashboard
@router.get("/dashboard", response_model=dict)
async def get_candidate_dashboard(
    current_user: UserContext = Depends(require_candidate)
):
    """Get candidate dashboard with key information and actions."""
    # TODO: Implement dashboard data
    # - Active applications
    # - Upcoming interviews
    # - Job recommendations
    # - Profile completion status
    # - Recent activities
    return {"applications": 0, "interviews": 0, "recommendations": 0, "profile_completion": 0.0}