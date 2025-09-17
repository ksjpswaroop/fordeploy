# Testing Framework - AI-Driven Recruitment Backend

## Table of Contents
1. [Testing Philosophy](#testing-philosophy)
2. [Test-Driven Development (TDD)](#test-driven-development-tdd)
3. [Testing Pyramid](#testing-pyramid)
4. [Unit Testing Guidelines](#unit-testing-guidelines)
5. [Integration Testing](#integration-testing)
6. [System Testing](#system-testing)
7. [Test Coverage Requirements](#test-coverage-requirements)
8. [Testing Tools and Setup](#testing-tools-and-setup)
9. [Test Data Management](#test-data-management)
10. [Continuous Integration](#continuous-integration)
11. [Performance Testing](#performance-testing)
12. [Security Testing](#security-testing)

## Testing Philosophy

### Core Principles
1. **Quality First**: Tests are not optional - they are part of the definition of done
2. **Fast Feedback**: Tests should run quickly to enable rapid development cycles
3. **Reliable**: Tests should be deterministic and not flaky
4. **Maintainable**: Tests should be easy to read, understand, and modify
5. **Comprehensive**: Critical paths must have 100% test coverage

### Testing Mindset
- Write tests before writing production code (TDD)
- Think about edge cases and error conditions
- Test behavior, not implementation details
- Keep tests simple and focused
- Use descriptive test names that explain the scenario

## Test-Driven Development (TDD)

### TDD Cycle (Red-Green-Refactor)

```
1. 🔴 RED: Write a failing test
   ↓
2. 🟢 GREEN: Write minimal code to make it pass
   ↓
3. 🔵 REFACTOR: Improve code while keeping tests green
   ↓
   Repeat
```

### TDD Implementation Steps

#### Step 1: Write a Failing Test (RED)
```python
# test_candidate_service.py
def test_create_candidate_profile_success():
    """Test successful candidate profile creation."""
    # Arrange
    candidate_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "skills": ["Python", "FastAPI"]
    }
    
    # Act
    result = candidate_service.create_profile(candidate_data)
    
    # Assert
    assert result.id is not None
    assert result.name == "John Doe"
    assert result.email == "john@example.com"
    assert len(result.skills) == 2
```

#### Step 2: Write Minimal Code (GREEN)
```python
# candidate_service.py
def create_profile(candidate_data: dict) -> CandidateProfile:
    """Create a new candidate profile."""
    # Minimal implementation to make test pass
    profile = CandidateProfile(
        id=1,
        name=candidate_data["name"],
        email=candidate_data["email"],
        skills=candidate_data["skills"]
    )
    return profile
```

#### Step 3: Refactor (BLUE)
```python
# candidate_service.py (refactored)
def create_profile(candidate_data: dict) -> CandidateProfile:
    """Create a new candidate profile."""
    # Validate input
    if not candidate_data.get("email"):
        raise ValueError("Email is required")
    
    # Create profile with proper ID generation
    profile = CandidateProfile(
        id=generate_unique_id(),
        name=candidate_data["name"],
        email=candidate_data["email"],
        skills=candidate_data.get("skills", [])
    )
    
    # Save to database
    db.session.add(profile)
    db.session.commit()
    
    return profile
```

### TDD Best Practices
- Start with the simplest test case
- Write only enough code to make the test pass
- Refactor both test and production code
- Keep the cycle short (5-10 minutes)
- Don't skip the refactor step

## Testing Pyramid

```
        /\     E2E Tests (5%)
       /  \    - Full system tests
      /    \   - User journey tests
     /______\  - Browser automation
    /        \
   / Integration \ (25%)
  /    Tests     \ - API tests
 /________________\ - Database tests
/                  \
/   Unit Tests      \ (70%)
/     (Fast)        \ - Function tests
/__________________\ - Class tests
```

### Test Distribution Guidelines
- **70% Unit Tests**: Fast, isolated, focused
- **25% Integration Tests**: Component interactions
- **5% End-to-End Tests**: Full user workflows

## Unit Testing Guidelines

### Test Structure (AAA Pattern)
```python
def test_function_name():
    """Test description explaining what is being tested."""
    # Arrange - Set up test data and conditions
    input_data = {"key": "value"}
    expected_result = "expected_output"
    
    # Act - Execute the function being tested
    actual_result = function_under_test(input_data)
    
    # Assert - Verify the results
    assert actual_result == expected_result
```

### Test Naming Convention
```python
# Pattern: test_[method]_[scenario]_[expected_result]
def test_create_candidate_with_valid_data_returns_candidate():
    pass

def test_create_candidate_with_invalid_email_raises_validation_error():
    pass

def test_get_candidate_with_nonexistent_id_returns_none():
    pass
```

### Unit Test Examples

#### Testing Models
```python
# tests/test_models/test_candidate.py
import pytest
from app.models.bench import CandidateBench
from app.schemas.base import BenchStatus

class TestCandidateBench:
    """Test cases for CandidateBench model."""
    
    def test_create_candidate_with_required_fields_succeeds(self):
        """Test candidate creation with minimum required fields."""
        # Arrange
        candidate_data = {
            "user_id": 1,
            "status": BenchStatus.AVAILABLE,
            "hourly_rate": 75.00
        }
        
        # Act
        candidate = CandidateBench(**candidate_data)
        
        # Assert
        assert candidate.user_id == 1
        assert candidate.status == BenchStatus.AVAILABLE
        assert candidate.hourly_rate == 75.00
        assert candidate.is_available is True
    
    def test_candidate_status_change_updates_availability(self):
        """Test that status change updates availability flag."""
        # Arrange
        candidate = CandidateBench(
            user_id=1,
            status=BenchStatus.AVAILABLE,
            hourly_rate=75.00
        )
        
        # Act
        candidate.status = BenchStatus.PLACED
        
        # Assert
        assert candidate.is_available is False
    
    @pytest.mark.parametrize("rate,expected", [
        (0, False),
        (-10, False),
        (50, True),
        (200, True)
    ])
    def test_hourly_rate_validation(self, rate, expected):
        """Test hourly rate validation with various values."""
        # Arrange & Act
        if expected:
            candidate = CandidateBench(
                user_id=1,
                status=BenchStatus.AVAILABLE,
                hourly_rate=rate
            )
            # Assert
            assert candidate.hourly_rate == rate
        else:
            # Assert
            with pytest.raises(ValueError):
                CandidateBench(
                    user_id=1,
                    status=BenchStatus.AVAILABLE,
                    hourly_rate=rate
                )
```

#### Testing Services
```python
# tests/test_services/test_candidate_service.py
import pytest
from unittest.mock import Mock, patch
from app.services.candidate_service import CandidateService
from app.models.bench import CandidateBench
from app.schemas.bench import CandidateBenchCreate

class TestCandidateService:
    """Test cases for CandidateService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def candidate_service(self, mock_db_session):
        """Create CandidateService instance with mocked dependencies."""
        return CandidateService(db_session=mock_db_session)
    
    def test_create_candidate_with_valid_data_returns_candidate(
        self, candidate_service, mock_db_session
    ):
        """Test successful candidate creation."""
        # Arrange
        candidate_data = CandidateBenchCreate(
            user_id=1,
            status="available",
            hourly_rate=75.00,
            skills=["Python", "FastAPI"]
        )
        
        expected_candidate = CandidateBench(
            id=1,
            user_id=1,
            status="available",
            hourly_rate=75.00
        )
        
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        # Act
        with patch('app.models.bench.CandidateBench', return_value=expected_candidate):
            result = candidate_service.create_candidate(candidate_data)
        
        # Assert
        assert result.id == 1
        assert result.user_id == 1
        assert result.hourly_rate == 75.00
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    def test_create_candidate_with_duplicate_user_raises_error(
        self, candidate_service, mock_db_session
    ):
        """Test candidate creation with duplicate user ID."""
        # Arrange
        candidate_data = CandidateBenchCreate(
            user_id=1,
            status="available",
            hourly_rate=75.00
        )
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = Mock()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Candidate already exists"):
            candidate_service.create_candidate(candidate_data)
    
    def test_get_candidates_with_filters_returns_filtered_results(
        self, candidate_service, mock_db_session
    ):
        """Test candidate retrieval with filters."""
        # Arrange
        filters = {"status": "available", "min_rate": 50}
        expected_candidates = [Mock(), Mock()]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = expected_candidates
        mock_db_session.query.return_value = mock_query
        
        # Act
        result = candidate_service.get_candidates(filters)
        
        # Assert
        assert len(result) == 2
        mock_db_session.query.assert_called_once_with(CandidateBench)
```

#### Testing API Endpoints
```python
# tests/test_api/test_candidate_endpoints.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from tests.conftest import override_get_db

class TestCandidateEndpoints:
    """Test cases for candidate API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client with database override."""
        app.dependency_overrides[get_db] = override_get_db
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers for requests."""
        return {"Authorization": "Bearer test_token"}
    
    def test_create_candidate_with_valid_data_returns_201(
        self, client, auth_headers
    ):
        """Test successful candidate creation via API."""
        # Arrange
        candidate_data = {
            "user_id": 1,
            "status": "available",
            "hourly_rate": 75.00,
            "skills": ["Python", "FastAPI"]
        }
        
        # Act
        response = client.post(
            "/api/v1/candidates",
            json=candidate_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == 1
        assert data["status"] == "available"
        assert data["hourly_rate"] == 75.00
        assert "id" in data
    
    def test_create_candidate_with_invalid_data_returns_422(
        self, client, auth_headers
    ):
        """Test candidate creation with invalid data."""
        # Arrange
        invalid_data = {
            "user_id": "invalid",  # Should be integer
            "status": "invalid_status",
            "hourly_rate": -10  # Should be positive
        }
        
        # Act
        response = client.post(
            "/api/v1/candidates",
            json=invalid_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_get_candidates_without_auth_returns_401(self, client):
        """Test candidate retrieval without authentication."""
        # Act
        response = client.get("/api/v1/candidates")
        
        # Assert
        assert response.status_code == 401
    
    def test_get_candidates_with_filters_returns_filtered_results(
        self, client, auth_headers
    ):
        """Test candidate retrieval with query filters."""
        # Act
        response = client.get(
            "/api/v1/candidates?status=available&min_rate=50",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
```

## Integration Testing

### Database Integration Tests
```python
# tests/test_integration/test_database.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.bench import CandidateBench
from app.models.user import User

class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.fixture(scope="class")
    def db_engine(self):
        """Create test database engine."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def db_session(self, db_engine):
        """Create database session for each test."""
        Session = sessionmaker(bind=db_engine)
        session = Session()
        yield session
        session.rollback()
        session.close()
    
    def test_candidate_user_relationship(self, db_session):
        """Test relationship between candidate and user."""
        # Arrange
        user = User(
            email="test@example.com",
            clerk_id="test_clerk_id",
            role="profile_manager"
        )
        db_session.add(user)
        db_session.flush()  # Get user ID
        
        candidate = CandidateBench(
            user_id=user.id,
            status="available",
            hourly_rate=75.00
        )
        db_session.add(candidate)
        db_session.commit()
        
        # Act
        retrieved_candidate = db_session.query(CandidateBench).first()
        
        # Assert
        assert retrieved_candidate.user.email == "test@example.com"
        assert retrieved_candidate.user_id == user.id
```

### API Integration Tests
```python
# tests/test_integration/test_api_flow.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestAPIIntegrationFlow:
    """Integration tests for complete API workflows."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_complete_candidate_lifecycle(self, client):
        """Test complete candidate management workflow."""
        # Step 1: Create user
        user_data = {
            "email": "candidate@example.com",
            "role": "job_seeker"
        }
        user_response = client.post("/api/v1/users", json=user_data)
        assert user_response.status_code == 201
        user_id = user_response.json()["id"]
        
        # Step 2: Create candidate profile
        candidate_data = {
            "user_id": user_id,
            "status": "available",
            "hourly_rate": 75.00,
            "skills": ["Python", "FastAPI"]
        }
        candidate_response = client.post(
            "/api/v1/candidates", 
            json=candidate_data
        )
        assert candidate_response.status_code == 201
        candidate_id = candidate_response.json()["id"]
        
        # Step 3: Update candidate status
        update_data = {"status": "interviewing"}
        update_response = client.patch(
            f"/api/v1/candidates/{candidate_id}/status",
            json=update_data
        )
        assert update_response.status_code == 200
        
        # Step 4: Verify final state
        get_response = client.get(f"/api/v1/candidates/{candidate_id}")
        assert get_response.status_code == 200
        final_data = get_response.json()
        assert final_data["status"] == "interviewing"
        assert final_data["is_available"] is False
```

## System Testing

### End-to-End Test Example
```python
# tests/test_e2e/test_user_journey.py
import pytest
from playwright.sync_api import sync_playwright

class TestUserJourney:
    """End-to-end tests for user journeys."""
    
    @pytest.fixture
    def browser(self):
        """Create browser instance for testing."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()
    
    def test_profile_manager_candidate_workflow(self, browser):
        """Test complete profile manager workflow."""
        page = browser.new_page()
        
        # Step 1: Login as profile manager
        page.goto("http://localhost:3000/login")
        page.fill("[data-testid=email]", "manager@example.com")
        page.fill("[data-testid=password]", "password123")
        page.click("[data-testid=login-button]")
        
        # Step 2: Navigate to candidates page
        page.wait_for_selector("[data-testid=dashboard]")
        page.click("[data-testid=candidates-nav]")
        
        # Step 3: Create new candidate
        page.click("[data-testid=add-candidate]")
        page.fill("[data-testid=candidate-name]", "John Doe")
        page.fill("[data-testid=candidate-email]", "john@example.com")
        page.select_option("[data-testid=candidate-status]", "available")
        page.fill("[data-testid=hourly-rate]", "75")
        page.click("[data-testid=save-candidate]")
        
        # Step 4: Verify candidate appears in list
        page.wait_for_selector("[data-testid=candidate-list]")
        candidate_row = page.locator("text=John Doe").first
        assert candidate_row.is_visible()
        
        # Step 5: Update candidate status
        page.click("[data-testid=candidate-actions]")
        page.click("[data-testid=update-status]")
        page.select_option("[data-testid=status-select]", "interviewing")
        page.click("[data-testid=confirm-update]")
        
        # Step 6: Verify status update
        status_badge = page.locator("[data-testid=status-badge]")
        assert "interviewing" in status_badge.text_content().lower()
```

## Test Coverage Requirements

### Coverage Targets
- **Overall Coverage**: 90% minimum
- **Critical Paths**: 100% coverage required
- **New Code**: 95% coverage required
- **Bug Fixes**: 100% coverage for fix and regression

### Coverage by Component
```
Component               Target    Critical
─────────────────────────────────────────
Models                   95%       100%
Services                 90%       100%
API Endpoints           85%       100%
Authentication          100%      100%
Database Operations     95%       100%
Utilities               80%       N/A
```

### Coverage Reporting
```bash
# Generate coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Coverage with branch analysis
pytest --cov=app --cov-branch --cov-report=html

# Fail if coverage below threshold
pytest --cov=app --cov-fail-under=90
```

### Coverage Configuration
```ini
# .coveragerc
[run]
source = app
omit = 
    app/migrations/*
    app/tests/*
    app/config.py
    */venv/*
    */virtualenv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:

[html]
directory = htmlcov
```

## Testing Tools and Setup

### Required Dependencies
```txt
# Testing framework
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
pytest-xdist>=3.3.0  # Parallel testing

# Test utilities
factory-boy>=3.3.0   # Test data factories
faker>=19.0.0         # Fake data generation
httpx>=0.25.0         # HTTP client for API tests
responses>=0.23.0     # Mock HTTP responses

# Database testing
sqlalchemy-utils>=0.41.0
pytest-postgresql>=5.0.0

# End-to-end testing
playwright>=1.37.0
selenium>=4.11.0
```

### Test Configuration
```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db
from app.models.base import Base

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(db_engine):
    """Create database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture
def client():
    """Create test client."""
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    return {"Authorization": "Bearer test_token"}
```

### Pytest Configuration
```ini
# pytest.ini
[tool:pytest]
addopts = 
    -v
    --strict-markers
    --strict-config
    --cov=app
    --cov-branch
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=90

testpaths = tests

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    auth: Authentication related tests
    database: Database related tests

filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

## Test Data Management

### Factory Pattern for Test Data
```python
# tests/factories.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from app.models.user import User
from app.models.bench import CandidateBench
from tests.conftest import TestingSessionLocal

class BaseFactory(SQLAlchemyModelFactory):
    """Base factory for all model factories."""
    class Meta:
        sqlalchemy_session = TestingSessionLocal
        sqlalchemy_session_persistence = "commit"

class UserFactory(BaseFactory):
    """Factory for User model."""
    class Meta:
        model = User
    
    email = factory.Faker("email")
    clerk_id = factory.Faker("uuid4")
    role = "job_seeker"
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True

class CandidateBenchFactory(BaseFactory):
    """Factory for CandidateBench model."""
    class Meta:
        model = CandidateBench
    
    user = factory.SubFactory(UserFactory)
    status = "available"
    hourly_rate = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    years_of_experience = factory.Faker("random_int", min=1, max=20)
    location = factory.Faker("city")
    remote_work_preference = "hybrid"
```

### Using Factories in Tests
```python
# tests/test_models/test_candidate.py
from tests.factories import CandidateBenchFactory, UserFactory

def test_candidate_creation_with_factory():
    """Test candidate creation using factory."""
    # Arrange & Act
    candidate = CandidateBenchFactory()
    
    # Assert
    assert candidate.id is not None
    assert candidate.user is not None
    assert candidate.hourly_rate > 0
    assert candidate.status == "available"

def test_multiple_candidates_with_same_user():
    """Test creating multiple candidates with specific user."""
    # Arrange
    user = UserFactory(email="specific@example.com")
    
    # Act
    candidate1 = CandidateBenchFactory(user=user, status="available")
    candidate2 = CandidateBenchFactory(user=user, status="placed")
    
    # Assert
    assert candidate1.user.email == "specific@example.com"
    assert candidate2.user.email == "specific@example.com"
    assert candidate1.user_id == candidate2.user_id
```

## Continuous Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      run: |
        flake8 app tests
        black --check app tests
        isort --check-only app tests
        mypy app
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
      run: |
        pytest --cov=app --cov-report=xml --cov-report=term
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        types: [python]
        pass_filenames: false
        always_run: true
```

## Performance Testing

### Load Testing with Locust
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and get auth token."""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def get_candidates(self):
        """Test candidate list endpoint."""
        self.client.get("/api/v1/candidates", headers=self.headers)
    
    @task(2)
    def get_candidate_detail(self):
        """Test candidate detail endpoint."""
        self.client.get("/api/v1/candidates/1", headers=self.headers)
    
    @task(1)
    def create_candidate(self):
        """Test candidate creation."""
        candidate_data = {
            "user_id": 1,
            "status": "available",
            "hourly_rate": 75.00
        }
        self.client.post(
            "/api/v1/candidates", 
            json=candidate_data, 
            headers=self.headers
        )
```

### Database Performance Tests
```python
# tests/performance/test_database_performance.py
import time
import pytest
from app.models.bench import CandidateBench
from tests.factories import CandidateBenchFactory

class TestDatabasePerformance:
    """Performance tests for database operations."""
    
    def test_candidate_query_performance(self, db_session):
        """Test candidate query performance with large dataset."""
        # Arrange - Create 1000 candidates
        candidates = CandidateBenchFactory.create_batch(1000)
        db_session.commit()
        
        # Act - Measure query time
        start_time = time.time()
        results = db_session.query(CandidateBench).filter(
            CandidateBench.status == "available"
        ).limit(50).all()
        end_time = time.time()
        
        # Assert - Query should complete within 100ms
        query_time = end_time - start_time
        assert query_time < 0.1, f"Query took {query_time:.3f}s, expected < 0.1s"
        assert len(results) <= 50
    
    def test_bulk_insert_performance(self, db_session):
        """Test bulk insert performance."""
        # Arrange
        candidate_data = [{
            "user_id": i,
            "status": "available",
            "hourly_rate": 75.00
        } for i in range(1000)]
        
        # Act - Measure bulk insert time
        start_time = time.time()
        db_session.bulk_insert_mappings(CandidateBench, candidate_data)
        db_session.commit()
        end_time = time.time()
        
        # Assert - Bulk insert should complete within 1 second
        insert_time = end_time - start_time
        assert insert_time < 1.0, f"Bulk insert took {insert_time:.3f}s, expected < 1.0s"
```

## Security Testing

### Authentication Tests
```python
# tests/security/test_authentication.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestAuthenticationSecurity:
    """Security tests for authentication."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_endpoint_requires_authentication(self, client):
        """Test that protected endpoints require authentication."""
        # Act
        response = client.get("/api/v1/candidates")
        
        # Assert
        assert response.status_code == 401
    
    def test_invalid_token_rejected(self, client):
        """Test that invalid tokens are rejected."""
        # Arrange
        headers = {"Authorization": "Bearer invalid_token"}
        
        # Act
        response = client.get("/api/v1/candidates", headers=headers)
        
        # Assert
        assert response.status_code == 401
    
    def test_expired_token_rejected(self, client):
        """Test that expired tokens are rejected."""
        # Arrange - Use a known expired token
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        # Act
        response = client.get("/api/v1/candidates", headers=headers)
        
        # Assert
        assert response.status_code == 401
```

### Input Validation Tests
```python
# tests/security/test_input_validation.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestInputValidation:
    """Security tests for input validation."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer valid_token"}
    
    def test_sql_injection_prevention(self, client, auth_headers):
        """Test that SQL injection attempts are prevented."""
        # Arrange - SQL injection payload
        malicious_payload = "'; DROP TABLE candidates; --"
        
        # Act
        response = client.get(
            f"/api/v1/candidates?search={malicious_payload}",
            headers=auth_headers
        )
        
        # Assert - Should not cause server error
        assert response.status_code in [200, 400, 422]
        # Database should still be intact (test in separate transaction)
    
    def test_xss_prevention(self, client, auth_headers):
        """Test that XSS attempts are prevented."""
        # Arrange - XSS payload
        xss_payload = "<script>alert('xss')</script>"
        candidate_data = {
            "user_id": 1,
            "status": "available",
            "hourly_rate": 75.00,
            "notes": xss_payload
        }
        
        # Act
        response = client.post(
            "/api/v1/candidates",
            json=candidate_data,
            headers=auth_headers
        )
        
        # Assert - Should sanitize or reject malicious input
        if response.status_code == 201:
            data = response.json()
            assert "<script>" not in data.get("notes", "")
```

## Test Execution Commands

### Basic Test Execution
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_models/test_candidate.py

# Run specific test method
pytest tests/test_models/test_candidate.py::test_create_candidate

# Run tests with specific marker
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

### Coverage and Reporting
```bash
# Run tests with coverage
pytest --cov=app

# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Run tests with coverage and fail if below threshold
pytest --cov=app --cov-fail-under=90

# Generate XML coverage report for CI
pytest --cov=app --cov-report=xml
```

### Parallel Test Execution
```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Run tests on 4 processes
pytest -n 4

# Run tests in parallel with coverage
pytest -n auto --cov=app
```

### Performance and Load Testing
```bash
# Run performance tests
pytest -m performance

# Run load tests with Locust
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Run load test with specific parameters
locust -f tests/performance/locustfile.py --host=http://localhost:8000 -u 10 -r 2 -t 60s
```

---

**Summary**: This testing framework provides comprehensive guidelines for implementing test-driven development, ensuring high code quality, and maintaining reliable test coverage across the AI-Driven Recruitment Backend system. Follow these practices to build robust, maintainable, and well-tested code.