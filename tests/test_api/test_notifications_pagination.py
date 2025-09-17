import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.auth.permissions import UserContext, UserRole
from app.models.user import User
from app.models.communication import Notification
from app.schemas.base import NotificationType, Priority
from app.core.database import get_db


@pytest.fixture()
def client(db_session: Session):
    user = User(email="p@example.com", username="p1", first_name="P", last_name="U", hashed_password="h", is_active=True)
    db_session.add(user)
    db_session.flush()
    # Seed 12 notifications (some dismissed)
    for i in range(12):
        db_session.add(Notification(
            user_id=user.id,
            title=f"N{i}",
            message="x",
            notification_type=NotificationType.SYSTEM,
            priority=Priority.LOW,
            is_read=(i % 3 == 0),
            is_dismissed=(i % 5 == 0),
        ))
    db_session.commit()

    def fake_get_user():
        return UserContext(user_id=str(user.id), email=user.email, role=UserRole.RECRUITER, tenant_id="1")

    from app.auth import permissions as perms
    app.dependency_overrides[perms.get_current_user] = fake_get_user

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override_get_db

    return TestClient(app)


def test_pagination_and_dismissed_filter(client: TestClient):
    # Default excludes dismissed; with 12 total, 2 dismissed at i=0,5,10 -> 3 dismissed => 9 visible
    r1 = client.get("/api/v1/notifications", params={"limit": 5, "skip": 0})
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["meta"]["page"] == 1
    assert body1["meta"]["page_size"] == 5
    assert body1["meta"]["total"] >= 9
    assert len(body1["data"]) == 5

    # Next page
    r2 = client.get("/api/v1/notifications", params={"limit": 5, "skip": 5})
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["meta"]["page"] == 2

    # Include only dismissed
    r3 = client.get("/api/v1/notifications", params={"dismissed": True})
    assert r3.status_code == 200
    body3 = r3.json()
    # Should return only the 3 dismissed items
    items = body3["data"]
    assert len(items) == 3
    assert all(it["is_dismissed"] is True for it in items)


def test_unread_count_and_mark_all_read(client: TestClient):
    # unread count should exclude dismissed
    cnt = client.get("/api/v1/notifications/unread-count").json()["unread"]
    assert cnt >= 0

    # mark all
    r = client.put("/api/v1/notifications/mark-all-read")
    assert r.status_code == 200
    # verify now unread count is 0
    cnt2 = client.get("/api/v1/notifications/unread-count").json()["unread"]
    assert cnt2 == 0
