from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.dependencies import require_recruiter_owner, require_admin, get_current_user
from app.models.user import User
from app.models.candidate_simple import CandidateSimple
from app.schemas.candidate_simple import (
    CandidateSimpleCreate, CandidateSimpleResponse, CandidateSimpleList
)

router = APIRouter(prefix="/recruiter", tags=["recruiter-candidates"])


@router.get("/{recruiter_identifier}/candidates", response_model=CandidateSimpleList, dependencies=[Depends(require_recruiter_owner)])
def list_recruiter_candidates(
    recruiter_identifier: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(CandidateSimple).filter(CandidateSimple.recruiter_identifier == recruiter_identifier)
    if search:
        like = f"%{search}%"
        q = q.filter(CandidateSimple.name.ilike(like))
    total = q.count()
    rows = q.order_by(CandidateSimple.created_at.desc()).offset(skip).limit(limit).all()
    return CandidateSimpleList(items=[CandidateSimpleResponse.model_validate(r) for r in rows], total=total)


@router.post("/{recruiter_identifier}/candidates", response_model=CandidateSimpleResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_recruiter_owner)])
def add_recruiter_candidate(
    recruiter_identifier: str,
    payload: CandidateSimpleCreate,
    db: Session = Depends(get_db)
):
    rec_id = recruiter_identifier.strip()
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Candidate name required")
    existing = db.query(CandidateSimple).filter(
        CandidateSimple.recruiter_identifier == rec_id,
        CandidateSimple.name == name
    ).first()
    if existing:
        return CandidateSimpleResponse.model_validate(existing)
    obj = CandidateSimple(recruiter_identifier=rec_id, name=name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CandidateSimpleResponse.model_validate(obj)


@router.delete("/{recruiter_identifier}/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_recruiter_owner)])
def delete_recruiter_candidate(
    recruiter_identifier: str,
    candidate_id: int,
    db: Session = Depends(get_db)
):
    rec_id = recruiter_identifier.strip()
    cand = db.query(CandidateSimple).filter(
        CandidateSimple.id == candidate_id,
        CandidateSimple.recruiter_identifier == rec_id
    ).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db.delete(cand)
    db.commit()
    return None


# ===================== Admin Management Endpoints =====================
@router.get("/admin/candidates", response_model=CandidateSimpleList, dependencies=[Depends(require_admin)])
def admin_list_all_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    search: Optional[str] = Query(None),
    recruiter: Optional[str] = Query(None, description="Filter by recruiter identifier"),
    db: Session = Depends(get_db)
):
    """List all candidates across recruiters (admin only)."""
    q = db.query(CandidateSimple)
    if recruiter:
        q = q.filter(CandidateSimple.recruiter_identifier == recruiter)
    if search:
        like = f"%{search}%"
        q = q.filter(CandidateSimple.name.ilike(like))
    total = q.count()
    rows = q.order_by(CandidateSimple.created_at.desc()).offset(skip).limit(limit).all()
    return CandidateSimpleList(items=[CandidateSimpleResponse.model_validate(r) for r in rows], total=total)


@router.patch("/admin/candidates/{candidate_id}", response_model=CandidateSimpleResponse, dependencies=[Depends(require_admin)])
def admin_reassign_candidate(
    candidate_id: int,
    new_recruiter_identifier: str = Query(..., description="Target recruiter email/identifier"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user)
):
    """Reassign a candidate to a different recruiter (admin only).

    Idempotent if already assigned. Enforces uniqueness constraint implicitly.
    """
    new_rid = new_recruiter_identifier.strip()
    if not new_rid:
        raise HTTPException(status_code=400, detail="new_recruiter_identifier required")
    cand = db.query(CandidateSimple).filter(CandidateSimple.id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    # If unchanged, return
    if cand.recruiter_identifier == new_rid:
        return CandidateSimpleResponse.model_validate(cand)
    # Check for name clash under target recruiter
    clash = db.query(CandidateSimple).filter(
        CandidateSimple.recruiter_identifier == new_rid,
        CandidateSimple.name == cand.name
    ).first()
    if clash:
        raise HTTPException(status_code=409, detail="A candidate with same name already exists under target recruiter")
    cand.recruiter_identifier = new_rid
    db.add(cand)
    db.commit()
    db.refresh(cand)
    return CandidateSimpleResponse.model_validate(cand)


@router.post("/admin/candidates", response_model=CandidateSimpleResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def admin_create_candidate(
    recruiter_identifier: str = Query(..., description="Recruiter to assign"),
    name: str = Query(..., description="Candidate name"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user)
):
    recruiter_identifier = recruiter_identifier.strip()
    name = name.strip()
    if not recruiter_identifier or not name:
        raise HTTPException(status_code=400, detail="recruiter_identifier and name required")
    existing = db.query(CandidateSimple).filter(
        CandidateSimple.recruiter_identifier == recruiter_identifier,
        CandidateSimple.name == name
    ).first()
    if existing:
        return CandidateSimpleResponse.model_validate(existing)
    obj = CandidateSimple(recruiter_identifier=recruiter_identifier, name=name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CandidateSimpleResponse.model_validate(obj)
