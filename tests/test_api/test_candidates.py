import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.auth.permissions import UserContext, UserRole
from app.models.user import User


@pytest.fixture()
def client(db_session: Session):
    # Seed a user
    user = User(
        email="manager@example.com",
        username="manager1",
        first_name="Man",
        last_name="Ager",
        hashed_password="hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Override middleware by injecting user context on request via dependency override pattern
    def fake_get_user():
        return UserContext(user_id=str(user.id), email=user.email, role=UserRole.MANAGER, tenant_id="1")

    from app.auth import permissions as perms
    app.dependency_overrides[perms.get_current_user] = fake_get_user

    return TestClient(app)


def test_create_and_list_candidates(client: TestClient):
    # Create
    payload = {
        "user_id": 1,
        "current_title": "Engineer",
        "experience_years": 3,
        "current_location": "Remote",
        "remote_work_preference": "flexible",
        "availability_status": "available",
        "work_authorization": "citizen",
        "preferred_contact_method": "email",
        "timezone": "UTC"
    }
    res = client.post("/api/v1/bench/candidates/", json=payload)
    assert res.status_code in (201, 200), res.text
    created = res.json()
    assert created["id"]
    assert created["user_id"] == payload["user_id"]

    # List with filter
    res = client.get("/api/v1/bench/candidates", params={"availability_status": "available"})
    assert res.status_code == 200
    payload = res.json()
    assert "data" in payload and "meta" in payload
    assert any(item["availability_status"] == "available" for item in payload["data"])

    # Get by id
    res = client.get(f"/api/v1/bench/candidates/{created['id']}")
    assert res.status_code == 200
    got = res.json()
    assert got["id"] == created["id"]

    # Update
    res = client.put(f"/api/v1/bench/candidates/{created['id']}", json={"current_title": "Sr Engineer"})
    assert res.status_code == 200
    assert res.json()["current_title"] == "Sr Engineer"

    # Patch status
    res = client.patch(f"/api/v1/bench/candidates/{created['id']}/status", params={"availability_status": "engaged"})
    assert res.status_code == 200
    assert res.json()["availability_status"] == "engaged"
