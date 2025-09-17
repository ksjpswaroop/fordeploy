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
    # Seed user
    user = User(
        email="notif@example.com",
        username="notifuser",
        first_name="Notif",
        last_name="User",
        hashed_password="hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    # Seed notifications
    n1 = Notification(
        user_id=user.id,
        title="Welcome",
        message="Hello",
        notification_type=NotificationType.SYSTEM,
        priority=Priority.MEDIUM,
        is_read=False,
    )
    n2 = Notification(
        user_id=user.id,
        title="Action",
        message="Please review",
        notification_type=NotificationType.INTERVIEW,
        priority=Priority.HIGH,
        is_read=False,
    )
    db_session.add_all([n1, n2])
    db_session.commit()

    # Inject user context and DB session
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


def test_list_mark_read_dismiss(client: TestClient):
    res = client.get("/api/v1/notifications")
    assert res.status_code == 200
    payload = res.json()
    assert "data" in payload and isinstance(payload["data"], list)
    assert len(payload["data"]) >= 2
    target_id = payload["data"][0]["id"]

    res2 = client.patch(f"/api/v1/notifications/{target_id}/read")
    assert res2.status_code == 200
    assert res2.json()["is_read"] is True

    res3 = client.patch(f"/api/v1/notifications/{target_id}/dismiss")
    assert res3.status_code == 200
    assert res3.json()["is_dismissed"] is True
