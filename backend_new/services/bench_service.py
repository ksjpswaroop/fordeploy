from typing import Tuple, List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.bench import CandidateBench
from app.schemas.bench import CandidateBenchCreate, CandidateBenchUpdate


class BenchService:
    """Service layer for Candidate Bench operations."""

    def create_candidate(self, db: Session, tenant_id: int, data: CandidateBenchCreate, current_user_id: int) -> CandidateBench:
        candidate = CandidateBench(
            tenant_id=tenant_id,
            user_id=data.user_id,
            profile_manager_id=data.profile_manager_id,
            current_title=data.current_title,
            experience_years=data.experience_years,
            current_salary=data.current_salary,
            expected_salary=data.expected_salary,
            current_location=data.current_location,
            willing_to_relocate=data.willing_to_relocate,
            preferred_locations=data.preferred_locations or [],
            remote_work_preference=(getattr(data.remote_work_preference, "value", data.remote_work_preference)),
            availability_status=(getattr(data.availability_status, "value", data.availability_status)),
            available_from=data.available_from,
            notice_period_days=data.notice_period_days,
            work_authorization=(getattr(data.work_authorization, "value", data.work_authorization)),
            visa_status=data.visa_status,
            visa_expiry=data.visa_expiry,
            highest_education=data.highest_education,
            education_field=data.education_field,
            university=data.university,
            graduation_year=data.graduation_year,
            professional_summary=data.professional_summary,
            key_achievements=data.key_achievements or [],
            resume_url=data.resume_url,
            portfolio_url=data.portfolio_url,
            linkedin_url=data.linkedin_url,
            github_url=data.github_url,
            hourly_rate=data.hourly_rate,
            markup_percentage=data.markup_percentage,
            marketing_approved=data.marketing_approved,
            marketing_notes=data.marketing_notes,
            unique_selling_points=data.unique_selling_points or [],
            preferred_contact_method=data.preferred_contact_method,
            best_time_to_contact=data.best_time_to_contact,
            timezone=data.timezone,
            created_by=current_user_id,
            updated_by=current_user_id,
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate

    def list_candidates(self, db: Session, tenant_id: int, filters: Optional[Dict[str, Any]] = None, skip: int = 0, limit: int = 50) -> Tuple[List[CandidateBench], int]:
        # Build base query with tenant scope
        base_stmt = select(CandidateBench).where(CandidateBench.tenant_id == tenant_id)

        # Apply filters to both items and count
        if filters:
            if availability := filters.get("availability_status"):
                base_stmt = base_stmt.where(CandidateBench.availability_status.in_(availability))
            if status := filters.get("bench_status"):
                base_stmt = base_stmt.where(CandidateBench.bench_status.in_(status))
            if (min_exp := filters.get("min_experience")) is not None:
                base_stmt = base_stmt.where(CandidateBench.experience_years >= min_exp)
            if (max_exp := filters.get("max_experience")) is not None:
                base_stmt = base_stmt.where(CandidateBench.experience_years <= max_exp)
            if (min_rate := filters.get("min_rate")) is not None:
                base_stmt = base_stmt.where(CandidateBench.hourly_rate >= min_rate)
            if (max_rate := filters.get("max_rate")) is not None:
                base_stmt = base_stmt.where(CandidateBench.hourly_rate <= max_rate)
            if title_contains := filters.get("title_contains"):
                like = f"%{title_contains}%"
                base_stmt = base_stmt.where(CandidateBench.current_title.ilike(like))

        # Sorting
        order = (filters or {}).get("order") or "-created_at"
        if order.startswith("-"):
            field = order[1:]
            if field == "created_at":
                base_stmt = base_stmt.order_by(CandidateBench.created_at.desc())
            elif field == "hourly_rate":
                base_stmt = base_stmt.order_by(CandidateBench.hourly_rate.desc().nullslast())
            elif field == "experience_years":
                base_stmt = base_stmt.order_by(CandidateBench.experience_years.desc())
        else:
            field = order
            if field == "created_at":
                base_stmt = base_stmt.order_by(CandidateBench.created_at.asc())
            elif field == "hourly_rate":
                base_stmt = base_stmt.order_by(CandidateBench.hourly_rate.asc().nullsfirst())
            elif field == "experience_years":
                base_stmt = base_stmt.order_by(CandidateBench.experience_years.asc())

        # Paged items
        items = db.execute(base_stmt.offset(skip).limit(limit)).scalars().all()

        # Total count with same filters
        count_stmt = select(func.count(CandidateBench.id)).where(CandidateBench.tenant_id == tenant_id)
        if filters:
            if availability := filters.get("availability_status"):
                count_stmt = count_stmt.where(CandidateBench.availability_status.in_(availability))
            if status := filters.get("bench_status"):
                count_stmt = count_stmt.where(CandidateBench.bench_status.in_(status))
            if (min_exp := filters.get("min_experience")) is not None:
                count_stmt = count_stmt.where(CandidateBench.experience_years >= min_exp)
            if (max_exp := filters.get("max_experience")) is not None:
                count_stmt = count_stmt.where(CandidateBench.experience_years <= max_exp)
            if (min_rate := filters.get("min_rate")) is not None:
                count_stmt = count_stmt.where(CandidateBench.hourly_rate >= min_rate)
            if (max_rate := filters.get("max_rate")) is not None:
                count_stmt = count_stmt.where(CandidateBench.hourly_rate <= max_rate)
            if title_contains := filters.get("title_contains"):
                like = f"%{title_contains}%"
                count_stmt = count_stmt.where(CandidateBench.current_title.ilike(like))
        total = db.scalar(count_stmt) or 0

        return items, int(total)

    def get_candidate(self, db: Session, tenant_id: int, candidate_id: int) -> Optional[CandidateBench]:
        return db.query(CandidateBench).filter(CandidateBench.tenant_id == tenant_id, CandidateBench.id == candidate_id).first()

    def update_candidate(self, db: Session, tenant_id: int, candidate_id: int, data: CandidateBenchUpdate) -> CandidateBench:
        candidate = self.get_candidate(db, tenant_id, candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(candidate, field, value)
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate

    def update_status(self, db: Session, tenant_id: int, candidate_id: int, availability_status: str) -> CandidateBench:
        candidate = self.get_candidate(db, tenant_id, candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")
        candidate.availability_status = availability_status
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate
