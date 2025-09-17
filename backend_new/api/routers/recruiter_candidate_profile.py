from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.core.database import get_db
from app.api.dependencies import require_recruiter_owner
from app.models.candidate_simple import CandidateSimple
from app.models.recruiter_candidate import (
    RecruiterCandidateProfile, RecruiterCandidateActivity,
    RecruiterCandidateNote, RecruiterCandidateDocument,
    RecruiterCandidateCommunication, RecruiterCandidateInterview
)
from app.schemas.recruiter_candidate import (
    RecruiterCandidateProfileCreate, RecruiterCandidateProfileUpdate, RecruiterCandidateProfileResponse,
    RecruiterCandidateActivityCreate, RecruiterCandidateActivityResponse, RecruiterCandidateActivityList,
    RecruiterCandidateNoteCreate, RecruiterCandidateNoteResponse,
    RecruiterCandidateDocumentCreate, RecruiterCandidateDocumentResponse,
    RecruiterCandidateCommunicationCreate, RecruiterCandidateCommunicationResponse,
    RecruiterCandidateInterviewCreate, RecruiterCandidateInterviewResponse
)

router = APIRouter(prefix="/recruiter", tags=["recruiter-candidate-profile"])  # mounted under /api


def _ensure_candidate(db: Session, recruiter_identifier: str, candidate_id: int) -> CandidateSimple:
    cand = db.query(CandidateSimple).filter(
        CandidateSimple.id == candidate_id,
        CandidateSimple.recruiter_identifier == recruiter_identifier
    ).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return cand


@router.get("/{recruiter_identifier}/candidates/{candidate_id}/profile", response_model=RecruiterCandidateProfileResponse, dependencies=[Depends(require_recruiter_owner)])
def get_profile(recruiter_identifier: str, candidate_id: int, db: Session = Depends(get_db)):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    prof = db.query(RecruiterCandidateProfile).filter(RecruiterCandidateProfile.candidate_id == candidate_id).first()
    if not prof:
        # create an empty profile lazily
        prof = RecruiterCandidateProfile(candidate_id=candidate_id, recruiter_identifier=recruiter_identifier)
        db.add(prof)
        db.commit()
        db.refresh(prof)
    return RecruiterCandidateProfileResponse.model_validate(prof)


@router.put("/{recruiter_identifier}/candidates/{candidate_id}/profile", response_model=RecruiterCandidateProfileResponse, dependencies=[Depends(require_recruiter_owner)])
def update_profile(recruiter_identifier: str, candidate_id: int, payload: RecruiterCandidateProfileUpdate, db: Session = Depends(get_db)):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    prof = db.query(RecruiterCandidateProfile).filter(RecruiterCandidateProfile.candidate_id == candidate_id).first()
    if not prof:
        prof = RecruiterCandidateProfile(candidate_id=candidate_id, recruiter_identifier=recruiter_identifier)
        db.add(prof)
        db.flush()
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(prof, k, v)
    db.add(prof)
    db.commit()
    db.refresh(prof)
    return RecruiterCandidateProfileResponse.model_validate(prof)


@router.get("/{recruiter_identifier}/candidates/{candidate_id}/activities", response_model=RecruiterCandidateActivityList, dependencies=[Depends(require_recruiter_owner)])
def list_activities(
    recruiter_identifier: str,
    candidate_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    q = db.query(RecruiterCandidateActivity).filter(
        RecruiterCandidateActivity.candidate_id == candidate_id,
        RecruiterCandidateActivity.recruiter_identifier == recruiter_identifier
    )
    total = q.count()
    rows = q.order_by(RecruiterCandidateActivity.occurred_at.desc()).offset(skip).limit(limit).all()
    return RecruiterCandidateActivityList(
        items=[RecruiterCandidateActivityResponse.model_validate(r) for r in rows],
        total=total
    )


@router.post("/{recruiter_identifier}/candidates/{candidate_id}/activities", response_model=RecruiterCandidateActivityResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_recruiter_owner)])
def create_activity(
    recruiter_identifier: str,
    candidate_id: int,
    payload: RecruiterCandidateActivityCreate,
    db: Session = Depends(get_db)
):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    act = RecruiterCandidateActivity(
        candidate_id=candidate_id,
        recruiter_identifier=recruiter_identifier,
        type=payload.type,
        title=payload.title,
        job_id=payload.job_id,
        run_id=payload.run_id,
        details=json.dumps(payload.details) if payload.details is not None else None
    )
    # also bump last_activity_at on profile
    prof = db.query(RecruiterCandidateProfile).filter(RecruiterCandidateProfile.candidate_id == candidate_id).first()
    if not prof:
        prof = RecruiterCandidateProfile(candidate_id=candidate_id, recruiter_identifier=recruiter_identifier)
        db.add(prof)
    from datetime import datetime as _dt
    prof.last_activity_at = _dt.utcnow()
    db.add(act)
    db.add(prof)
    db.commit()
    db.refresh(act)
    return RecruiterCandidateActivityResponse.model_validate(act)


# ----------------------- Notes -----------------------
@router.get("/{recruiter_identifier}/candidates/{candidate_id}/notes", response_model=list[RecruiterCandidateNoteResponse], dependencies=[Depends(require_recruiter_owner)])
def list_notes(recruiter_identifier: str, candidate_id: int, db: Session = Depends(get_db)):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    rows = db.query(RecruiterCandidateNote).filter(
        RecruiterCandidateNote.recruiter_identifier == recruiter_identifier,
        RecruiterCandidateNote.candidate_id == candidate_id
    ).order_by(RecruiterCandidateNote.created_at.desc()).all()
    items: list[RecruiterCandidateNoteResponse] = []
    for r in rows:
        tags_list = r.tags.split(',') if r.tags else None
        items.append(RecruiterCandidateNoteResponse(
            id=r.id,
            candidate_id=r.candidate_id,
            recruiter_identifier=r.recruiter_identifier,
            title=r.title,
            content=r.content,
            note_type=r.note_type,
            is_private=bool(r.is_private),
            tags=tags_list,
            created_at=r.created_at,
            updated_at=r.updated_at
        ))
    return items


@router.post("/{recruiter_identifier}/candidates/{candidate_id}/notes", response_model=RecruiterCandidateNoteResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_recruiter_owner)])
def create_note(recruiter_identifier: str, candidate_id: int, payload: RecruiterCandidateNoteCreate, db: Session = Depends(get_db)):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    obj = RecruiterCandidateNote(
        candidate_id=candidate_id,
        recruiter_identifier=recruiter_identifier,
        title=payload.title,
        content=payload.content,
        note_type=payload.note_type,
        is_private=1 if payload.is_private else 0,
        tags=",".join(payload.tags or []) if payload.tags else None
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return RecruiterCandidateNoteResponse(
        id=obj.id,
        candidate_id=obj.candidate_id,
        recruiter_identifier=obj.recruiter_identifier,
        title=obj.title,
        content=obj.content,
        note_type=obj.note_type,
        is_private=bool(obj.is_private),
        tags=payload.tags or None,
        created_at=obj.created_at,
        updated_at=obj.updated_at
    )


# ----------------------- Documents -----------------------
@router.get("/{recruiter_identifier}/candidates/{candidate_id}/documents", response_model=list[RecruiterCandidateDocumentResponse], dependencies=[Depends(require_recruiter_owner)])
def list_documents(recruiter_identifier: str, candidate_id: int, db: Session = Depends(get_db)):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    rows = db.query(RecruiterCandidateDocument).filter(
        RecruiterCandidateDocument.recruiter_identifier == recruiter_identifier,
        RecruiterCandidateDocument.candidate_id == candidate_id
    ).order_by(RecruiterCandidateDocument.created_at.desc()).all()
    items: list[RecruiterCandidateDocumentResponse] = []
    from app.core.config import settings
    supa_enabled = settings.supabase_storage_enabled
    if supa_enabled:
        from app.services.supabase_storage import get_public_url, create_signed_url
        bucket = settings.SUPABASE_STORAGE_BUCKET_UPLOADS
    for r in rows:
        download_url = f"/uploads/{r.storage_path}" if r.storage_path else None
        if supa_enabled and r.storage_path:
            try:
                url = get_public_url(bucket, r.storage_path) or create_signed_url(bucket, r.storage_path, 3600)
                if url:
                    download_url = url
            except Exception:
                pass
        items.append(RecruiterCandidateDocumentResponse(
            id=r.id,
            candidate_id=r.candidate_id,
            recruiter_identifier=r.recruiter_identifier,
            filename=r.filename,
            document_type=r.document_type,
            storage_path=r.storage_path,
            mime_type=r.mime_type,
            file_size=r.file_size,
            download_url=download_url,
            created_at=r.created_at,
            updated_at=r.updated_at,
        ))
    return items


@router.post("/{recruiter_identifier}/candidates/{candidate_id}/documents", response_model=RecruiterCandidateDocumentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_recruiter_owner)])
def upload_document(
    recruiter_identifier: str,
    candidate_id: int,
    file: UploadFile = File(...),
    document_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    # Save to uploads folder
    import os
    upload_dir = os.path.join(os.getcwd(), 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    # create unique filename
    import uuid
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"cand{candidate_id}_{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(upload_dir, unique_name)
    with open(dest_path, 'wb') as out:
        out.write(file.file.read())

    rel_path = unique_name
    # Mirror to Supabase Storage if configured
    from app.core.config import settings
    if settings.supabase_storage_enabled:
        try:
            from app.services.supabase_storage import upload_bytes
            with open(dest_path, 'rb') as fh:
                data = fh.read()
            key = f"recruiters/{recruiter_identifier}/candidates/{candidate_id}/{unique_name}"
            ok = upload_bytes(settings.SUPABASE_STORAGE_BUCKET_UPLOADS, key, data, content_type=file.content_type or None, upsert=True)
            if ok:
                rel_path = key
        except Exception:
            pass
    obj = RecruiterCandidateDocument(
        candidate_id=candidate_id,
        recruiter_identifier=recruiter_identifier,
        filename=file.filename,
        document_type=document_type,
        storage_path=rel_path,
        mime_type=file.content_type,
        file_size=None
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    # Build download URL (prefer Supabase when enabled)
    download_url = f"/uploads/{obj.storage_path}"
    if settings.supabase_storage_enabled:
        try:
            from app.services.supabase_storage import get_public_url, create_signed_url
            url = get_public_url(settings.SUPABASE_STORAGE_BUCKET_UPLOADS, obj.storage_path) or create_signed_url(settings.SUPABASE_STORAGE_BUCKET_UPLOADS, obj.storage_path, 3600)
            if url:
                download_url = url
        except Exception:
            pass
    return RecruiterCandidateDocumentResponse(
        id=obj.id,
        candidate_id=obj.candidate_id,
        recruiter_identifier=obj.recruiter_identifier,
        filename=obj.filename,
        document_type=obj.document_type,
        storage_path=obj.storage_path,
        mime_type=obj.mime_type,
        file_size=obj.file_size,
        download_url=download_url,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


# ----------------------- Communications -----------------------
@router.get("/{recruiter_identifier}/candidates/{candidate_id}/communications", response_model=list[RecruiterCandidateCommunicationResponse])
def list_communications(recruiter_identifier: str, candidate_id: int, db: Session = Depends(get_db)):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    rows = db.query(RecruiterCandidateCommunication).filter(
        RecruiterCandidateCommunication.recruiter_identifier == recruiter_identifier,
        RecruiterCandidateCommunication.candidate_id == candidate_id
    ).order_by(RecruiterCandidateCommunication.created_at.desc()).all()
    return [RecruiterCandidateCommunicationResponse.model_validate(r) for r in rows]


@router.post("/{recruiter_identifier}/candidates/{candidate_id}/communications", response_model=RecruiterCandidateCommunicationResponse, status_code=status.HTTP_201_CREATED)
def create_communication(recruiter_identifier: str, candidate_id: int, payload: RecruiterCandidateCommunicationCreate, db: Session = Depends(get_db)):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    obj = RecruiterCandidateCommunication(
        candidate_id=candidate_id,
        recruiter_identifier=recruiter_identifier,
        communication_type=payload.communication_type,
        subject=payload.subject,
        content=payload.content,
        status='sent'
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return RecruiterCandidateCommunicationResponse.model_validate(obj)


# ----------------------- Interviews -----------------------
@router.get("/{recruiter_identifier}/candidates/{candidate_id}/interviews", response_model=list[RecruiterCandidateInterviewResponse])
def list_interviews(recruiter_identifier: str, candidate_id: int, db: Session = Depends(get_db)):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    rows = db.query(RecruiterCandidateInterview).filter(
        RecruiterCandidateInterview.recruiter_identifier == recruiter_identifier,
        RecruiterCandidateInterview.candidate_id == candidate_id
    ).order_by(RecruiterCandidateInterview.scheduled_at.desc().nullslast()).all()
    return [RecruiterCandidateInterviewResponse.model_validate(r) for r in rows]


@router.post("/{recruiter_identifier}/candidates/{candidate_id}/interviews", response_model=RecruiterCandidateInterviewResponse, status_code=status.HTTP_201_CREATED)
def create_interview(recruiter_identifier: str, candidate_id: int, payload: RecruiterCandidateInterviewCreate, db: Session = Depends(get_db)):
    _ensure_candidate(db, recruiter_identifier, candidate_id)
    obj = RecruiterCandidateInterview(
        candidate_id=candidate_id,
        recruiter_identifier=recruiter_identifier,
        title=payload.title,
        interview_type=payload.interview_type,
        job_id=payload.job_id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        location=payload.location,
        status='scheduled'
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return RecruiterCandidateInterviewResponse.model_validate(obj)
