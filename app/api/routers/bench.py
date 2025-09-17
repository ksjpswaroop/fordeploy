from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.permissions import get_current_user, UserContext, require_permission, Permission
from app.schemas.bench import (
    CandidateBenchCreate,
    CandidateBenchUpdate,
    CandidateBenchResponse,
    CandidateBenchSummary,
)
from app.schemas.common import PaginatedResponse
from app.api.utils.pagination import build_pagination_meta
from app.services.bench_service import BenchService


router = APIRouter(prefix="/candidates", tags=["bench"])


def get_service() -> BenchService:
    return BenchService()


@router.post("/", response_model=CandidateBenchResponse, status_code=status.HTTP_201_CREATED)
@require_permission(Permission.CANDIDATE_CREATE)
async def create_candidate(
    payload: CandidateBenchCreate,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    service: BenchService = Depends(get_service),
):
    candidate = service.create_candidate(db, tenant_id=int(current_user.tenant_id or 1), data=payload, current_user_id=int(current_user.user_id))
    return candidate


@router.get("/", response_model=PaginatedResponse[CandidateBenchSummary], summary="List bench candidates", description="Paginated list with filters for availability, status, experience, rate, and title. Supports sorting and pagination.")
@require_permission(Permission.CANDIDATE_READ)
async def list_candidates(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    service: BenchService = Depends(get_service),
    availability_status: Optional[List[str]] = Query(None),
    bench_status: Optional[List[str]] = Query(None),
    min_experience: Optional[int] = Query(None, ge=0),
    max_experience: Optional[int] = Query(None, ge=0),
    min_rate: Optional[float] = Query(None, ge=0),
    max_rate: Optional[float] = Query(None, ge=0),
    title_contains: Optional[str] = Query(None, min_length=2),
    order: str = Query("-created_at", description="Sort by field, prefix '-' for desc"),
    skip: int = 0,
    limit: int = 50,
):
    filters: Dict[str, Any] = {}
    if availability_status:
        filters["availability_status"] = availability_status
    if bench_status:
        filters["bench_status"] = bench_status
    if min_experience is not None:
        filters["min_experience"] = min_experience
    if max_experience is not None:
        filters["max_experience"] = max_experience
    if min_rate is not None:
        filters["min_rate"] = min_rate
    if max_rate is not None:
        filters["max_rate"] = max_rate
    if title_contains:
        filters["title_contains"] = title_contains
    filters["order"] = order
    items, total = service.list_candidates(db, tenant_id=int(current_user.tenant_id or 1), filters=filters, skip=skip, limit=limit)
    meta = build_pagination_meta(total=total, skip=skip, limit=limit)
    return PaginatedResponse[CandidateBenchSummary](data=items, meta=meta)


@router.get("/{candidate_id}", response_model=CandidateBenchResponse)
@require_permission(Permission.CANDIDATE_READ)
async def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    service: BenchService = Depends(get_service),
):
    candidate = service.get_candidate(db, tenant_id=int(current_user.tenant_id or 1), candidate_id=candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.put("/{candidate_id}", response_model=CandidateBenchResponse)
@require_permission(Permission.CANDIDATE_UPDATE)
async def update_candidate(
    candidate_id: int,
    payload: CandidateBenchUpdate,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    service: BenchService = Depends(get_service),
):
    candidate = service.update_candidate(db, tenant_id=int(current_user.tenant_id or 1), candidate_id=candidate_id, data=payload)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.patch("/{candidate_id}/status", response_model=CandidateBenchResponse)
@require_permission(Permission.CANDIDATE_UPDATE)
async def update_status(
    candidate_id: int,
    availability_status: str,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    service: BenchService = Depends(get_service),
):
    candidate = service.update_status(db, tenant_id=int(current_user.tenant_id or 1), candidate_id=candidate_id, availability_status=availability_status)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate
