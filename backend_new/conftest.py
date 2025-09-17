import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

# Ensure project root is on sys.path for imports like 'app.*'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure required env vars for settings exist before importing app modules
os.environ.setdefault("APIFY_TOKEN", "test-token")
os.environ.setdefault("CLERK_SECRET_KEY", "test-clerk-secret")
os.environ.setdefault("CLERK_PUBLISHABLE_KEY", "test-clerk-pub")

from app.core.database import get_db
from app.models.base import Base as ModelsBase
from app.main import app

# Use an in-memory SQLite DB shared across connections to avoid locks
TEST_DB_URL = "sqlite+pysqlite:///:memory:"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    # Import models so metadata has all tables
    import app.models  # noqa: F401
    ModelsBase.metadata.create_all(bind=engine)
    yield
    ModelsBase.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _override_dependency():
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session():
    """Provide a transactional DB session to tests."""
    connection = engine.connect()
    trans = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()
