import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.bench import CandidateBench


class TestCandidateBenchModel:
    def test_candidate_bench_minimal_create(self, db_session: Session):
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

        bench = CandidateBench(
            user_id=user.id,
            tenant_id=1,
            current_title="Software Engineer",
            experience_years=5,
            current_location="Remote",
            remote_work_preference="flexible",
            availability_status="available",
            work_authorization="citizen",
        )

        db_session.add(bench)
        db_session.commit()
        db_session.refresh(bench)

        assert bench.id is not None
        assert bench.user_id == user.id
        assert bench.is_available is True
