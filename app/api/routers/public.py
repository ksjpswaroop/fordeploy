from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.job import Job
from app.models.application import Application

router = APIRouter(prefix="/public", tags=["public"])

@router.get("/jobs")
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(Job).order_by(Job.created_at.desc())
    total = q.count()
    rows = q.offset(skip).limit(limit).all()
    return {
        "items": [
            {
                "id": j.id,
                "title": j.title,
                "location": j.location_display,
                "status": j.status.value if hasattr(j.status, 'value') else j.status,
                "updated_at": j.updated_at,
            } for j in rows
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/candidates")
def list_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Derive unique candidate user IDs from applications (simplified MVP)
    subq = db.query(Application.candidate_id).distinct().offset(skip).limit(limit).all()
    ids = [r[0] for r in subq if r[0] is not None]
    # For MVP just count applications per candidate
    items = []
    if ids:
        for cid in ids:
            app_count = db.query(Application).filter(Application.candidate_id == cid).count()
            items.append({
                "id": cid,
                "name": f"Candidate {cid}",
                "role": None,
                "stage": None,
                "score": None,
                "updated_at": None,
                "applications": app_count,
            })
    return {
        "items": items,
        "total": len(items),
        "skip": skip,
        "limit": limit,
    }
