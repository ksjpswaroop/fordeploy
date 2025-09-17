# Comprehensive Testing Guide

## Overview
This document provides a complete testing strategy for the AI-Driven Recruitment Backend, including unit tests, integration tests, end-to-end tests, and manual testing procedures.

## Testing Strategy

### Testing Pyramid
```
    /\     E2E Tests (10%)
   /  \    - Full workflow testing
  /____\   - User journey validation
 /      \  Integration Tests (30%)
/        \ - API endpoint testing
\        / - Database integration
 \______/  Unit Tests (60%)
           - Service layer testing
           - Model validation
```

## Test Environment Setup

### 1. Testing Dependencies
```bash
# Install testing dependencies
pip install pytest pytest-asyncio pytest-cov httpx pytest-mock

# Install additional testing tools
pip install factory-boy faker freezegun
```

### 2. Test Database Setup
```bash
# Create test database
psql -c "CREATE DATABASE recruitment_test;"

# Set test environment variables
export DATABASE_URL="postgresql://user:password@localhost/recruitment_test"
export TESTING=true
```

### 3. Test Configuration
Create `tests/conftest.py`:
```python
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings

# Test database setup
TEST_DATABASE_URL = "postgresql://user:password@localhost/recruitment_test"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

## Unit Testing

### 1. Model Testing
Create `tests/test_models.py`:
```python
import pytest
from app.models.user import User
from app.models.job import Job
from app.models.application import Application

class TestUserModel:
    def test_user_creation(self, db_session):
        user = User(
            clerk_id="user_123",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "John Doe"
    
    def test_user_validation(self):
        with pytest.raises(ValueError):
            User(email="invalid-email")

class TestJobModel:
    def test_job_creation(self, db_session):
        job = Job(
            title="Software Engineer",
            company="Tech Corp",
            description="Great opportunity",
            requirements=["Python", "FastAPI"],
            salary_min=80000,
            salary_max=120000
        )
        db_session.add(job)
        db_session.commit()
        
        assert job.id is not None
        assert job.title == "Software Engineer"
        assert "Python" in job.requirements
```

### 2. Service Testing
Create `tests/test_services.py`:
```python
import pytest
from unittest.mock import Mock, patch
from app.services.user_service import UserService
from app.services.job_service import JobService
from app.schemas.user import UserCreate, UserUpdate

class TestUserService:
    @pytest.fixture
    def user_service(self, db_session):
        return UserService(db_session)
    
    def test_create_user(self, user_service):
        user_data = UserCreate(
            clerk_id="user_123",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        user = user_service.create_user(user_data)
        
        assert user.email == "test@example.com"
        assert user.clerk_id == "user_123"
    
    def test_get_user_by_email(self, user_service):
        # Create test user first
        user_data = UserCreate(
            clerk_id="user_123",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        created_user = user_service.create_user(user_data)
        
        # Test retrieval
        found_user = user_service.get_user_by_email("test@example.com")
        
        assert found_user is not None
        assert found_user.id == created_user.id
    
    def test_update_user(self, user_service):
        # Create test user
        user_data = UserCreate(
            clerk_id="user_123",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        user = user_service.create_user(user_data)
        
        # Update user
        update_data = UserUpdate(first_name="Jane")
        updated_user = user_service.update_user(user.id, update_data)
        
        assert updated_user.first_name == "Jane"
        assert updated_user.last_name == "Doe"  # Unchanged

class TestJobService:
    @pytest.fixture
    def job_service(self, db_session):
        return JobService(db_session)
    
    def test_create_job(self, job_service):
        job_data = {
            "title": "Software Engineer",
            "company": "Tech Corp",
            "description": "Great opportunity",
            "requirements": ["Python", "FastAPI"]
        }
        
        job = job_service.create_job(job_data)
        
        assert job.title == "Software Engineer"
        assert "Python" in job.requirements
    
    def test_search_jobs(self, job_service):
        # Create test jobs
        jobs_data = [
            {"title": "Python Developer", "company": "A Corp"},
            {"title": "Java Developer", "company": "B Corp"},
            {"title": "Python Engineer", "company": "C Corp"}
        ]
        
        for job_data in jobs_data:
            job_service.create_job(job_data)
        
        # Search for Python jobs
        results = job_service.search_jobs(query="Python")
        
        assert len(results) == 2
        assert all("Python" in job.title for job in results)
```

### 3. Schema Validation Testing
Create `tests/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError
from app.schemas.user import UserCreate, UserResponse
from app.schemas.job import JobCreate, JobResponse
from app.schemas.application import ApplicationCreate

class TestUserSchemas:
    def test_valid_user_create(self):
        user_data = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "candidate"
        }
        
        user = UserCreate(**user_data)
        
        assert user.email == "test@example.com"
        assert user.role == "candidate"
    
    def test_invalid_email(self):
        user_data = {
            "clerk_id": "user_123",
            "email": "invalid-email",
            "first_name": "John",
            "last_name": "Doe",
            "role": "candidate"
        }
        
        with pytest.raises(ValidationError):
            UserCreate(**user_data)
    
    def test_invalid_role(self):
        user_data = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "invalid_role"
        }
        
        with pytest.raises(ValidationError):
            UserCreate(**user_data)

class TestJobSchemas:
    def test_valid_job_create(self):
        job_data = {
            "title": "Software Engineer",
            "company": "Tech Corp",
            "description": "Great opportunity",
            "requirements": ["Python", "FastAPI"],
            "salary_min": 80000,
            "salary_max": 120000
        }
        
        job = JobCreate(**job_data)
        
        assert job.title == "Software Engineer"
        assert job.salary_min < job.salary_max
    
    def test_invalid_salary_range(self):
        job_data = {
            "title": "Software Engineer",
            "company": "Tech Corp",
            "description": "Great opportunity",
            "salary_min": 120000,
            "salary_max": 80000  # Invalid: max < min
        }
        
        with pytest.raises(ValidationError):
            JobCreate(**job_data)
```

## Integration Testing

### 1. API Endpoint Testing
Create `tests/test_api.py`:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestUserAPI:
    def test_create_user(self, client):
        user_data = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "candidate"
        }
        
        response = client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
    
    def test_get_user(self, client):
        # Create user first
        user_data = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "candidate"
        }
        create_response = client.post("/api/v1/users/", json=user_data)
        user_id = create_response.json()["id"]
        
        # Get user
        response = client.get(f"/api/v1/users/{user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
    
    def test_update_user(self, client):
        # Create user first
        user_data = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "candidate"
        }
        create_response = client.post("/api/v1/users/", json=user_data)
        user_id = create_response.json()["id"]
        
        # Update user
        update_data = {"first_name": "Jane"}
        response = client.put(f"/api/v1/users/{user_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jane"
    
    def test_delete_user(self, client):
        # Create user first
        user_data = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "candidate"
        }
        create_response = client.post("/api/v1/users/", json=user_data)
        user_id = create_response.json()["id"]
        
        # Delete user
        response = client.delete(f"/api/v1/users/{user_id}")
        
        assert response.status_code == 204
        
        # Verify user is deleted
        get_response = client.get(f"/api/v1/users/{user_id}")
        assert get_response.status_code == 404

class TestJobAPI:
    def test_create_job(self, client):
        job_data = {
            "title": "Software Engineer",
            "company": "Tech Corp",
            "description": "Great opportunity",
            "requirements": ["Python", "FastAPI"],
            "salary_min": 80000,
            "salary_max": 120000
        }
        
        response = client.post("/api/v1/jobs/", json=job_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Software Engineer"
        assert "id" in data
    
    def test_search_jobs(self, client):
        # Create test jobs
        jobs = [
            {"title": "Python Developer", "company": "A Corp"},
            {"title": "Java Developer", "company": "B Corp"},
            {"title": "Python Engineer", "company": "C Corp"}
        ]
        
        for job_data in jobs:
            client.post("/api/v1/jobs/", json=job_data)
        
        # Search for Python jobs
        response = client.get("/api/v1/jobs/search?q=Python")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert all("Python" in job["title"] for job in data["items"])

class TestApplicationAPI:
    def test_create_application(self, client):
        # Create user and job first
        user_data = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "candidate"
        }
        user_response = client.post("/api/v1/users/", json=user_data)
        user_id = user_response.json()["id"]
        
        job_data = {
            "title": "Software Engineer",
            "company": "Tech Corp",
            "description": "Great opportunity"
        }
        job_response = client.post("/api/v1/jobs/", json=job_data)
        job_id = job_response.json()["id"]
        
        # Create application
        application_data = {
            "user_id": user_id,
            "job_id": job_id,
            "cover_letter": "I'm interested in this position"
        }
        
        response = client.post("/api/v1/applications/", json=application_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == user_id
        assert data["job_id"] == job_id
        assert data["status"] == "submitted"
```

### 2. Database Integration Testing
Create `tests/test_database.py`:
```python
import pytest
from sqlalchemy import text
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job

class TestDatabaseIntegration:
    def test_database_connection(self, db_session):
        result = db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    def test_user_job_relationship(self, db_session):
        # Create user
        user = User(
            clerk_id="user_123",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="recruiter"
        )
        db_session.add(user)
        db_session.commit()
        
        # Create job
        job = Job(
            title="Software Engineer",
            company="Tech Corp",
            description="Great opportunity",
            created_by=user.id
        )
        db_session.add(job)
        db_session.commit()
        
        # Test relationship
        assert job.creator.email == "test@example.com"
        assert user.created_jobs[0].title == "Software Engineer"
    
    def test_cascade_delete(self, db_session):
        # Create user with job
        user = User(
            clerk_id="user_123",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="recruiter"
        )
        db_session.add(user)
        db_session.commit()
        
        job = Job(
            title="Software Engineer",
            company="Tech Corp",
            description="Great opportunity",
            created_by=user.id
        )
        db_session.add(job)
        db_session.commit()
        
        job_id = job.id
        
        # Delete user
        db_session.delete(user)
        db_session.commit()
        
        # Check if job still exists (should depend on cascade settings)
        remaining_job = db_session.query(Job).filter(Job.id == job_id).first()
        # Assert based on your cascade configuration
```

## End-to-End Testing

### 1. User Journey Testing
Create `tests/test_e2e.py`:
```python
import pytest
from fastapi.testclient import TestClient

class TestUserJourneys:
    def test_candidate_application_flow(self, client):
        """Test complete candidate application process"""
        
        # 1. Create candidate user
        candidate_data = {
            "clerk_id": "candidate_123",
            "email": "candidate@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "role": "candidate"
        }
        candidate_response = client.post("/api/v1/users/", json=candidate_data)
        assert candidate_response.status_code == 201
        candidate_id = candidate_response.json()["id"]
        
        # 2. Create recruiter and job
        recruiter_data = {
            "clerk_id": "recruiter_123",
            "email": "recruiter@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "recruiter"
        }
        recruiter_response = client.post("/api/v1/users/", json=recruiter_data)
        assert recruiter_response.status_code == 201
        recruiter_id = recruiter_response.json()["id"]
        
        job_data = {
            "title": "Software Engineer",
            "company": "Tech Corp",
            "description": "Great opportunity",
            "requirements": ["Python", "FastAPI"],
            "created_by": recruiter_id
        }
        job_response = client.post("/api/v1/jobs/", json=job_data)
        assert job_response.status_code == 201
        job_id = job_response.json()["id"]
        
        # 3. Candidate searches for jobs
        search_response = client.get("/api/v1/jobs/search?q=Software")
        assert search_response.status_code == 200
        jobs = search_response.json()["items"]
        assert len(jobs) >= 1
        assert any(job["id"] == job_id for job in jobs)
        
        # 4. Candidate applies for job
        application_data = {
            "user_id": candidate_id,
            "job_id": job_id,
            "cover_letter": "I'm very interested in this position"
        }
        application_response = client.post("/api/v1/applications/", json=application_data)
        assert application_response.status_code == 201
        application_id = application_response.json()["id"]
        assert application_response.json()["status"] == "submitted"
        
        # 5. Recruiter views applications
        applications_response = client.get(f"/api/v1/jobs/{job_id}/applications")
        assert applications_response.status_code == 200
        applications = applications_response.json()["items"]
        assert len(applications) == 1
        assert applications[0]["id"] == application_id
        
        # 6. Recruiter updates application status
        status_update = {"status": "under_review"}
        update_response = client.put(
            f"/api/v1/applications/{application_id}/status",
            json=status_update
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "under_review"
        
        # 7. Schedule interview
        interview_data = {
            "application_id": application_id,
            "scheduled_at": "2024-02-01T10:00:00Z",
            "interview_type": "technical",
            "notes": "Technical screening"
        }
        interview_response = client.post("/api/v1/interviews/", json=interview_data)
        assert interview_response.status_code == 201
        
        # 8. Candidate views their applications
        candidate_apps_response = client.get(f"/api/v1/users/{candidate_id}/applications")
        assert candidate_apps_response.status_code == 200
        candidate_apps = candidate_apps_response.json()["items"]
        assert len(candidate_apps) == 1
        assert candidate_apps[0]["status"] == "under_review"
    
    def test_recruiter_job_management_flow(self, client):
        """Test complete recruiter job management process"""
        
        # 1. Create recruiter
        recruiter_data = {
            "clerk_id": "recruiter_123",
            "email": "recruiter@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "recruiter"
        }
        recruiter_response = client.post("/api/v1/users/", json=recruiter_data)
        assert recruiter_response.status_code == 201
        recruiter_id = recruiter_response.json()["id"]
        
        # 2. Create job posting
        job_data = {
            "title": "Senior Python Developer",
            "company": "Tech Innovations",
            "description": "Looking for experienced Python developer",
            "requirements": ["Python", "Django", "PostgreSQL"],
            "salary_min": 90000,
            "salary_max": 130000,
            "created_by": recruiter_id
        }
        job_response = client.post("/api/v1/jobs/", json=job_data)
        assert job_response.status_code == 201
        job_id = job_response.json()["id"]
        
        # 3. Update job posting
        job_update = {
            "description": "Updated: Looking for experienced Python developer with FastAPI experience",
            "requirements": ["Python", "Django", "FastAPI", "PostgreSQL"]
        }
        update_response = client.put(f"/api/v1/jobs/{job_id}", json=job_update)
        assert update_response.status_code == 200
        assert "FastAPI" in update_response.json()["requirements"]
        
        # 4. View job analytics
        analytics_response = client.get(f"/api/v1/jobs/{job_id}/analytics")
        assert analytics_response.status_code == 200
        analytics = analytics_response.json()
        assert "views" in analytics
        assert "applications" in analytics
        
        # 5. Close job posting
        close_response = client.put(f"/api/v1/jobs/{job_id}/close")
        assert close_response.status_code == 200
        assert close_response.json()["status"] == "closed"
```

### 2. Pipeline Testing
Create `tests/test_pipeline_e2e.py`:
```python
import pytest
from fastapi.testclient import TestClient

class TestPipelineEndToEnd:
    def test_complete_pipeline_flow(self, client):
        """Test complete job pipeline from scraping to application"""
        
        # 1. Health check
        health_response = client.get("/healthz")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"
        
        # 2. Scrape jobs
        scrape_data = {
            "title": "Python Developer",
            "location": "San Francisco",
            "rows": 10
        }
        scrape_response = client.post("/pipeline/scrape", json=scrape_data)
        assert scrape_response.status_code == 200
        scrape_result = scrape_response.json()
        assert scrape_result["jobs_scraped"] > 0
        
        # 3. Enrich job data
        enrich_data = {
            "database_path": scrape_result["output_path"]
        }
        enrich_response = client.post("/pipeline/enrich", json=enrich_data)
        assert enrich_response.status_code == 200
        enrich_result = enrich_response.json()
        assert enrich_result["enriched_count"] > 0
        
        # 4. Match jobs with resume
        match_data = {
            "resume_path": "test_resume.pdf",
            "database_path": scrape_result["output_path"],
            "threshold": 30.0
        }
        match_response = client.post("/pipeline/match", json=match_data)
        assert match_response.status_code == 200
        match_result = match_response.json()
        assert "matches_found" in match_result
        
        # 5. Send applications (dry run)
        if match_result["matches_found"] > 0:
            job_ids = [job["job_id"] for job in match_result["jobs"][:3]]
            send_data = {
                "job_ids": job_ids,
                "resume_path": "test_resume.pdf",
                "database_path": scrape_result["output_path"],
                "dry_run": True
            }
            send_response = client.post("/pipeline/send", json=send_data)
            assert send_response.status_code == 200
            send_result = send_response.json()
            assert send_result["jobs_processed"] == len(job_ids)
```

## Manual Testing Procedures

### 1. API Testing with Postman/Insomnia

#### Authentication Testing
1. **Test Clerk Integration**
   - Obtain valid JWT token from Clerk
   - Test protected endpoints with valid token
   - Test protected endpoints with invalid/expired token
   - Verify role-based access control

2. **Test Endpoints**
   ```
   GET /api/v1/users/me (with auth header)
   POST /api/v1/jobs/ (with recruiter auth)
   GET /api/v1/jobs/search?q=python
   POST /api/v1/applications/ (with candidate auth)
   ```

#### Pipeline Testing
1. **Health Check**
   ```
   GET /healthz
   Expected: {"status": "healthy", "version": "1.0.0", ...}
   ```

2. **Scraping**
   ```
   POST /pipeline/scrape
   Body: {
     "title": "Software Engineer",
     "location": "San Francisco",
     "rows": 5
   }
   ```

3. **Job Enrichment**
   ```
   POST /pipeline/enrich
   Body: {"database_path": "jobs.db"}
   ```

4. **Job Matching**
   ```
   POST /pipeline/match
   Body: {
     "resume_path": "resume.pdf",
     "threshold": 30.0
   }
   ```

### 2. Database Testing

#### Connection Testing
```sql
-- Test database connection
SELECT version();

-- Test table creation
SHOW TABLES;

-- Test data integrity
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM jobs;
SELECT COUNT(*) FROM applications;
```

#### Migration Testing
```bash
# Test migration up
alembic upgrade head

# Test migration down
alembic downgrade -1

# Test migration history
alembic history
```

### 3. Performance Testing

#### Load Testing with Locust
Create `tests/load_test.py`:
```python
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login and get auth token
        pass
    
    @task(3)
    def search_jobs(self):
        self.client.get("/api/v1/jobs/search?q=python")
    
    @task(2)
    def get_job_details(self):
        self.client.get("/api/v1/jobs/1")
    
    @task(1)
    def create_application(self):
        data = {
            "job_id": 1,
            "cover_letter": "Test application"
        }
        self.client.post("/api/v1/applications/", json=data)
```

Run load test:
```bash
locust -f tests/load_test.py --host=http://localhost:8000
```

### 4. Security Testing

#### Authentication Security
- [ ] Test JWT token validation
- [ ] Test token expiration handling
- [ ] Test role-based access control
- [ ] Test unauthorized access attempts

#### Input Validation
- [ ] Test SQL injection attempts
- [ ] Test XSS prevention
- [ ] Test file upload security
- [ ] Test rate limiting

#### Data Protection
- [ ] Test password hashing
- [ ] Test sensitive data encryption
- [ ] Test CORS configuration
- [ ] Test HTTPS enforcement

## Test Execution

### Running Tests

#### Unit Tests
```bash
# Run all unit tests
pytest tests/test_models.py tests/test_services.py tests/test_schemas.py -v

# Run with coverage
pytest tests/test_models.py --cov=app --cov-report=html
```

#### Integration Tests
```bash
# Run API tests
pytest tests/test_api.py -v

# Run database tests
pytest tests/test_database.py -v
```

#### End-to-End Tests
```bash
# Run E2E tests
pytest tests/test_e2e.py -v

# Run pipeline tests
pytest tests/test_pipeline_e2e.py -v
```

#### All Tests
```bash
# Run complete test suite
pytest -v --cov=app --cov-report=html --cov-report=term

# Run tests in parallel
pytest -n auto
```

### Continuous Integration

Create `.github/workflows/test.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: recruitment_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=app --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/recruitment_test
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

## Test Data Management

### Test Fixtures
Create `tests/fixtures.py`:
```python
import factory
from factory.alchemy import SQLAlchemyModelFactory
from app.models.user import User
from app.models.job import Job
from app.models.application import Application

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"
    
    clerk_id = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.first_name.lower()}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = "candidate"

class JobFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Job
        sqlalchemy_session_persistence = "commit"
    
    title = factory.Faker("job")
    company = factory.Faker("company")
    description = factory.Faker("text")
    requirements = factory.LazyFunction(lambda: ["Python", "FastAPI"])
    salary_min = 80000
    salary_max = 120000

class ApplicationFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Application
        sqlalchemy_session_persistence = "commit"
    
    user = factory.SubFactory(UserFactory)
    job = factory.SubFactory(JobFactory)
    cover_letter = factory.Faker("text")
    status = "submitted"
```

### Test Data Cleanup
```python
@pytest.fixture(autouse=True)
def cleanup_test_data(db_session):
    """Clean up test data after each test"""
    yield
    
    # Clean up in reverse order of dependencies
    db_session.query(Application).delete()
    db_session.query(Job).delete()
    db_session.query(User).delete()
    db_session.commit()
```

## Quality Metrics and Reporting

### Coverage Requirements
- **Minimum Coverage:** 80%
- **Critical Paths:** 95%
- **New Code:** 90%

### Test Metrics to Track
- Test execution time
- Test success rate
- Code coverage percentage
- Number of flaky tests
- Performance benchmarks

### Reporting
```bash
# Generate coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Generate test report
pytest --html=reports/report.html --self-contained-html

# Performance profiling
pytest --profile --profile-svg
```

## Troubleshooting Common Issues

### Test Failures
1. **Database Connection Issues**
   - Check PostgreSQL service status
   - Verify connection string
   - Ensure test database exists

2. **Authentication Failures**
   - Verify Clerk configuration
   - Check JWT token validity
   - Ensure proper test user setup

3. **Import Errors**
   - Check PYTHONPATH configuration
   - Verify all dependencies installed
   - Check for circular imports

### Performance Issues
1. **Slow Tests**
   - Use database transactions for rollback
   - Mock external API calls
   - Optimize test data creation

2. **Memory Leaks**
   - Properly close database connections
   - Clean up test data
   - Monitor resource usage

## Best Practices

### Test Organization
- Group related tests in classes
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Keep tests independent and isolated

### Test Data
- Use factories for test data creation
- Avoid hardcoded values
- Clean up after each test
- Use realistic but minimal data

### Assertions
- Use specific assertions
- Test both positive and negative cases
- Verify error messages and status codes
- Check side effects and state changes

### Maintenance
- Review and update tests regularly
- Remove obsolete tests
- Refactor duplicated test code
- Keep tests simple and readable

Remember: Good tests are your safety net for confident development and deployment!