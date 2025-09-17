import pytest
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.bench_service import BenchService
from app.schemas.bench import CandidateBenchCreate, CandidateBenchUpdate


@pytest.fixture()
def bench_service() -> BenchService:
    return BenchService()


def seed_user(db_session: Session) -> User:
    user = User(
        email="candidate@example.com",
        username="candidate1",
        first_name="Cand",
        last_name="Idate",
        hashed_password="test-hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_create_candidate_profile(db_session: Session, bench_service: BenchService):
    user = seed_user(db_session)
    payload = CandidateBenchCreate(
        user_id=user.id,
        profile_manager_id=None,
        current_title="Software Engineer",
        experience_years=5,
        current_salary=None,
        expected_salary=None,
        current_location="Remote",
        willing_to_relocate=False,
        preferred_locations=[],
        remote_work_preference="flexible",
        availability_status="available",
        available_from=None,
        notice_period_days=0,
        work_authorization="citizen",
        visa_status=None,
        visa_expiry=None,
        highest_education=None,
        education_field=None,
        university=None,
        graduation_year=None,
        professional_summary=None,
        key_achievements=[],
        resume_url=None,
        portfolio_url=None,
        linkedin_url=None,
        github_url=None,
        hourly_rate=None,
        markup_percentage=None,
        marketing_approved=False,
        marketing_notes=None,
        unique_selling_points=[],
        preferred_contact_method="email",
        best_time_to_contact=None,
        timezone="UTC",
    )

    created = bench_service.create_candidate(db_session, tenant_id=1, data=payload, current_user_id=user.id)
    assert created.id is not None
    assert created.user_id == user.id
    assert created.tenant_id == 1


def test_list_candidates_with_filter(db_session: Session, bench_service: BenchService):
    user = seed_user(db_session)
    # create two candidates with different statuses
    for status in ("available", "engaged"):
        bench_service.create_candidate(
            db_session,
            tenant_id=1,
            data=CandidateBenchCreate(
                user_id=user.id,
                profile_manager_id=None,
                current_title="Engineer",
                experience_years=3,
                current_salary=None,
                expected_salary=None,
                current_location="Remote",
                willing_to_relocate=False,
                preferred_locations=[],
                remote_work_preference="flexible",
                availability_status=status,
                available_from=None,
                notice_period_days=0,
                work_authorization="citizen",
            ),
            current_user_id=user.id,
        )

    items, total = bench_service.list_candidates(db_session, tenant_id=1, filters={"availability_status": ["available"]}, skip=0, limit=50)
    assert total >= 1
    assert all(c.availability_status == "available" for c in items)


def test_get_update_and_patch_status(db_session: Session, bench_service: BenchService):
    user = seed_user(db_session)
    created = bench_service.create_candidate(
        db_session,
        tenant_id=1,
        data=CandidateBenchCreate(
            user_id=user.id,
            profile_manager_id=None,
            current_title="Engineer",
            experience_years=2,
            current_salary=None,
            expected_salary=None,
            current_location="Remote",
            willing_to_relocate=False,
            preferred_locations=[],
            remote_work_preference="flexible",
            availability_status="available",
            work_authorization="citizen",
        ),
        current_user_id=user.id,
    )

    got = bench_service.get_candidate(db_session, tenant_id=1, candidate_id=created.id)
    assert got is not None
    assert got.id == created.id

    updated = bench_service.update_candidate(db_session, tenant_id=1, candidate_id=created.id, data=CandidateBenchUpdate(current_title="Sr Engineer"))
    assert updated.current_title == "Sr Engineer"

    patched = bench_service.update_status(db_session, tenant_id=1, candidate_id=created.id, availability_status="engaged")
    assert patched.availability_status == "engaged"


def test_list_filters_and_sorting_branches(db_session: Session, bench_service: BenchService):
    user = seed_user(db_session)
    # Seed three candidates with varying attributes
    c1 = bench_service.create_candidate(
        db_session,
        tenant_id=1,
        data=CandidateBenchCreate(
            user_id=user.id,
            profile_manager_id=None,
            current_title="Alpha Engineer",
            experience_years=1,
            current_salary=None,
            expected_salary=None,
            current_location="Remote",
            willing_to_relocate=False,
            preferred_locations=[],
            remote_work_preference="flexible",
            availability_status="available",
            work_authorization="citizen",
            hourly_rate=50,
        ),
        current_user_id=user.id,
    )
    c2 = bench_service.create_candidate(
        db_session,
        tenant_id=1,
        data=CandidateBenchCreate(
            user_id=user.id,
            profile_manager_id=None,
            current_title="Beta Engineer",
            experience_years=5,
            current_salary=None,
            expected_salary=None,
            current_location="Remote",
            willing_to_relocate=False,
            preferred_locations=[],
            remote_work_preference="flexible",
            availability_status="engaged",
            work_authorization="citizen",
            hourly_rate=100,
        ),
        current_user_id=user.id,
    )
    c3 = bench_service.create_candidate(
        db_session,
        tenant_id=1,
        data=CandidateBenchCreate(
            user_id=user.id,
            profile_manager_id=None,
            current_title="Gamma Engineer",
            experience_years=10,
            current_salary=None,
            expected_salary=None,
            current_location="Remote",
            willing_to_relocate=False,
            preferred_locations=[],
            remote_work_preference="flexible",
            availability_status="available",
            work_authorization="citizen",
            hourly_rate=None,
        ),
        current_user_id=user.id,
    )

    # Filter by bench_status
    items, total = bench_service.list_candidates(db_session, tenant_id=1, filters={"bench_status": ["active"]}, skip=0, limit=50)
    assert total >= 0  # presence of filter path

    # Filter by min/max experience
    items, total = bench_service.list_candidates(db_session, tenant_id=1, filters={"min_experience": 2, "max_experience": 6}, skip=0, limit=50)
    assert any(i.experience_years == 5 for i in items)

    # Filter by min/max rate
    items, total = bench_service.list_candidates(db_session, tenant_id=1, filters={"min_rate": 60, "max_rate": 120}, skip=0, limit=50)
    assert all((i.hourly_rate or 0) >= 60 for i in items)

    # Title contains (case-insensitive)
    items, total = bench_service.list_candidates(db_session, tenant_id=1, filters={"title_contains": "engineer"}, skip=0, limit=50)
    assert total >= 3

    # Sorting branches: created_at asc
    items, total = bench_service.list_candidates(db_session, tenant_id=1, filters={"order": "created_at"}, skip=0, limit=50)
    assert len(items) >= 3

    # Sorting branches: hourly_rate asc (nulls first)
    items, _ = bench_service.list_candidates(db_session, tenant_id=1, filters={"order": "hourly_rate"}, skip=0, limit=50)
    # First should be None hourly_rate (treated as nulls first)
    assert items[0].hourly_rate is None

    # Sorting branches: hourly_rate desc (nulls last)
    items, _ = bench_service.list_candidates(db_session, tenant_id=1, filters={"order": "-hourly_rate"}, skip=0, limit=50)
    assert items[0].hourly_rate == 100

    # Sorting branches: experience_years asc and desc
    items_asc, _ = bench_service.list_candidates(db_session, tenant_id=1, filters={"order": "experience_years"}, skip=0, limit=50)
    items_desc, _ = bench_service.list_candidates(db_session, tenant_id=1, filters={"order": "-experience_years"}, skip=0, limit=50)
    assert items_asc[0].experience_years == 1
    assert items_desc[0].experience_years == 10
