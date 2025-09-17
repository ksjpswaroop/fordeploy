from sqlalchemy.orm import Session
from app.models import Tenant, User, CandidateBench


def test_candidate_bench_isolation_by_tenant(db_session: Session):
    # Create two tenants
    t1 = Tenant(name="Tenant One", domain="t1.example")
    t2 = Tenant(name="Tenant Two", domain="t2.example")
    db_session.add_all([t1, t2])
    db_session.commit()

    # Create a user for association (minimal fields to satisfy constraints)
    u1 = User(
        email="u1@t1.com",
        first_name="U1",
        last_name="T1",
        hashed_password="x",
    )
    u2 = User(
        email="u2@t2.com",
        first_name="U2",
        last_name="T2",
        hashed_password="x",
    )
    db_session.add_all([u1, u2])
    db_session.commit()

    # Add candidate bench entries scoped to tenants
    cb1 = CandidateBench(
        tenant_id=t1.id,
        user_id=u1.id,
        current_title="Backend Engineer",
        experience_years=5,
        current_location="NYC",
        remote_work_preference="flexible",
        availability_status="available",
        work_authorization="citizen",
    )
    cb2 = CandidateBench(
        tenant_id=t2.id,
        user_id=u2.id,
        current_title="Data Engineer",
        experience_years=4,
        current_location="SF",
        remote_work_preference="remote",
        availability_status="engaged",
        work_authorization="green_card",
    )
    db_session.add_all([cb1, cb2])
    db_session.commit()

    # Verify isolation
    t1_results = db_session.query(CandidateBench).filter(CandidateBench.tenant_id == t1.id).all()
    t2_results = db_session.query(CandidateBench).filter(CandidateBench.tenant_id == t2.id).all()

    assert len(t1_results) == 1
    assert len(t2_results) == 1
    assert t1_results[0].user_id == u1.id
    assert t2_results[0].user_id == u2.id
