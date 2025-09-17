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
def seed(db_session: Session):
    u = User(email="rb@example.com", username="rb", first_name="R", last_name="B", hashed_password="h", is_active=True)
    db_session.add(u)
    db_session.flush()
    n = Notification(user_id=u.id, title="R", message="B", notification_type=NotificationType.SYSTEM, priority=Priority.MEDIUM)
    db_session.add(n)
    db_session.commit()
    return u, n


def override_user(role: UserRole, user_id: int):
    def fake_get_user():
        return UserContext(user_id=str(user_id), email="x@y.z", role=role, tenant_id="1")
    from app.auth import permissions as perms
    app.dependency_overrides[perms.get_current_user] = fake_get_user


def override_db(db_session: Session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override_get_db


def test_rbac_allows_roles(seed, db_session: Session):
    user, n = seed
    override_db(db_session)

    # Manager allowed
    override_user(UserRole.MANAGER, user.id)
    c = TestClient(app)
    assert c.get("/api/v1/notifications").status_code == 200
    assert c.patch(f"/api/v1/notifications/{n.id}/read").status_code == 200

    # Recruiter allowed
    override_user(UserRole.RECRUITER, user.id)
    c2 = TestClient(app)
    assert c2.get("/api/v1/notifications").status_code == 200

    # Candidate allowed
    override_user(UserRole.CANDIDATE, user.id)
    c3 = TestClient(app)
    assert c3.get("/api/v1/notifications").status_code == 200


def test_rbac_denies_without_auth(seed, db_session: Session):
    # Clear auth override -> should 401
    app.dependency_overrides.clear()
    c = TestClient(app)
    r = c.get("/api/v1/notifications")
    assert r.status_code in (401, 403)
