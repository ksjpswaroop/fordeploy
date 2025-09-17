import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, Role
from app.core.security import create_access_token

client = TestClient(app)

# Helper to get token for seeded user by email

def token_for(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user, f"User {email} not found"
        return create_access_token({"sub": user.id, "role": user.get_primary_role() or "candidate"})
    finally:
        db.close()

@pytest.fixture(scope="module")
def recruiter_token():
    return token_for("sriman@example.com")

@pytest.fixture(scope="module")
def other_recruiter_token():
    return token_for("kumar@example.com")

@pytest.fixture(scope="module")
def admin_token():
    return token_for("vamshi@example.com")

BASE = "/recruiter"

@pytest.mark.parametrize("path_builder", [
    lambda rid: f"{BASE}/{rid}/candidates",
])
def test_recruiter_cannot_list_other_recruiter_candidates(recruiter_token, other_recruiter_token, path_builder):
    # First create a candidate under recruiter A
    headers_a = {"Authorization": f"Bearer {recruiter_token}"}
    r = client.post(path_builder("sriman@example.com"), json={"name": "Alice"}, headers=headers_a)
    assert r.status_code in (200, 201)

    # Recruiter B attempts to list recruiter A's candidates
    headers_b = {"Authorization": f"Bearer {other_recruiter_token}"}
    r2 = client.get(path_builder("sriman@example.com"), headers=headers_b)
    assert r2.status_code == 403


def test_recruiter_can_list_own_candidates(recruiter_token):
    headers = {"Authorization": f"Bearer {recruiter_token}"}
    r = client.get(f"{BASE}/sriman@example.com/candidates", headers=headers)
    assert r.status_code == 200


def test_admin_can_access_any_recruiter(admin_token, recruiter_token):
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    # admin lists recruiter sriman
    r = client.get(f"{BASE}/sriman@example.com/candidates", headers=headers_admin)
    assert r.status_code == 200
    # admin lists another recruiter
    r2 = client.get(f"{BASE}/kumar@example.com/candidates", headers=headers_admin)
    assert r2.status_code == 200


def test_recruiter_scope_mismatch_on_create(other_recruiter_token):
    headers = {"Authorization": f"Bearer {other_recruiter_token}"}
    # Attempt to create candidate under different recruiter namespace
    r = client.post(f"{BASE}/sriman@example.com/candidates", json={"name": "Bob"}, headers=headers)
    assert r.status_code == 403
