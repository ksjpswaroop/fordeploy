# 🧪 Manual Testing Guide for Job Pipeline API

This guide shows you how to manually test the Job Pipeline API using various methods.

## 🚀 Starting the Application

### Method 1: Standalone Job Pipeline API
```bash
# Activate virtual environment
source venv312/bin/activate

# Start the API server
./venv312/bin/python -c "
import sys
sys.path.append('.')
from fastapi import FastAPI
from app.api.routers.job_pipeline import router

app = FastAPI(title='Job Pipeline API', version='1.0.0')
app.include_router(router)

if __name__ == '__main__':
    import uvicorn
    print('🚀 Starting Job Pipeline API...')
    print('📖 API Documentation: http://localhost:8000/docs')
    print('🔗 Job Pipeline Endpoints: http://localhost:8000/job-pipeline/')
    uvicorn.run(app, host='0.0.0.0', port=8000)
"
```

### Method 2: Full Application (if database is configured)
```bash
# Start the main application
./venv312/bin/python main.py
```

## 📖 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🧪 Testing Methods

### 1. **Using cURL Commands**

#### Test Database Initialization
```bash
curl -X POST "http://localhost:8000/job-pipeline/init-database" \
  -H "Content-Type: application/json" \
  -d '{"db_path": "test_jobs.db"}'
```

#### Test Resume Text Extraction
```bash
curl -X POST "http://localhost:8000/job-pipeline/extract-resume" \
  -H "Content-Type: application/json" \
  -d '{"resume_path": "sample_resume.txt"}'
```

#### Test Job Analysis (requires OpenAI API key)
```bash
curl -X POST "http://localhost:8000/job-pipeline/analyze-job-match" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Software Engineer with 5 years Python experience",
    "job_description": "Looking for a Python developer with FastAPI experience",
    "job_title": "Senior Python Developer",
    "company_name": "Tech Corp",
    "job_id": "test_job_123"
  }'
```

#### Test Resume Optimization (requires OpenAI API key)
```bash
curl -X POST "http://localhost:8000/job-pipeline/optimize-resume" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Software Engineer with Python experience",
    "job_description": "Looking for a Python developer with FastAPI and SQLAlchemy experience",
    "job_title": "Python Developer",
    "company_name": "Tech Corp",
    "use_analysis": false
  }'
```

#### Test Cover Letter Generation (requires OpenAI API key)
```bash
curl -X POST "http://localhost:8000/job-pipeline/generate-cover-letter" \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "Python Developer",
    "company_name": "Tech Corp",
    "recruiter_name": "Jane Smith",
    "job_description": "Looking for a Python developer with FastAPI experience",
    "resume_text": "Software Engineer with 5 years Python experience"
  }'
```

#### Test Job Filtering
```bash
curl -X POST "http://localhost:8000/job-pipeline/filter-jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "jobs": [
      {"job_id": "1", "company_name": "Google", "job_title": "Software Engineer"},
      {"job_id": "2", "company_name": "Microsoft", "job_title": "Developer"},
      {"job_id": "3", "company_name": "Blocked Company", "job_title": "Engineer"}
    ]
  }'
```

#### List Jobs in Database
```bash
curl "http://localhost:8000/job-pipeline/jobs?db_path=test_jobs.db&limit=10"
```

### 2. **Using Python Scripts**

#### Create a Test Script
```python
#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000/job-pipeline"

def test_database_init():
    """Test database initialization."""
    response = requests.post(f"{BASE_URL}/init-database", json={"db_path": "test_jobs.db"})
    print(f"Database Init: {response.status_code} - {response.json()}")

def test_resume_extraction():
    """Test resume text extraction."""
    response = requests.post(f"{BASE_URL}/extract-resume", json={"resume_path": "sample_resume.txt"})
    print(f"Resume Extraction: {response.status_code} - {response.json()}")

def test_job_analysis():
    """Test job analysis."""
    data = {
        "resume_text": "Software Engineer with 5 years Python experience",
        "job_description": "Looking for a Python developer with FastAPI experience",
        "job_title": "Senior Python Developer",
        "company_name": "Tech Corp",
        "job_id": "test_job_123"
    }
    response = requests.post(f"{BASE_URL}/analyze-job-match", json=data)
    print(f"Job Analysis: {response.status_code} - {response.json()}")

if __name__ == "__main__":
    test_database_init()
    test_resume_extraction()
    test_job_analysis()
```

### 3. **Using Postman or Insomnia**

1. **Import the OpenAPI spec**: http://localhost:8000/openapi.json
2. **Set base URL**: http://localhost:8000
3. **Test endpoints** using the GUI interface

### 4. **Using the Swagger UI**

1. Go to http://localhost:8000/docs
2. Click on any endpoint to expand it
3. Click "Try it out"
4. Fill in the request body
5. Click "Execute"

## 🔧 Environment Variables for Full Testing

To test all features, set these environment variables:

```bash
# Required for job scraping
export APIFY_TOKEN="your_apify_token_here"

# Required for AI features
export OPENAI_API_KEY="your_openai_api_key_here"

# Required for email sending
export SENDGRID_API_KEY="your_sendgrid_api_key_here"

# Optional for contact enrichment
export APOLLO_API_KEY="your_apollo_api_key_here"
```

## 📋 Test Scenarios

### Scenario 1: Basic Functionality Test
```bash
# 1. Initialize database
curl -X POST "http://localhost:8000/job-pipeline/init-database" \
  -H "Content-Type: application/json" \
  -d '{"db_path": "test_jobs.db"}'

# 2. Extract resume text
curl -X POST "http://localhost:8000/job-pipeline/extract-resume" \
  -H "Content-Type: application/json" \
  -d '{"resume_path": "sample_resume.txt"}'

# 3. List jobs (should be empty initially)
curl "http://localhost:8000/job-pipeline/jobs?db_path=test_jobs.db"
```

### Scenario 2: AI-Powered Features Test (requires OpenAI API key)
```bash
# 1. Analyze job match
curl -X POST "http://localhost:8000/job-pipeline/analyze-job-match" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Data Scientist with 5 years experience in Python, machine learning, and data analysis",
    "job_description": "We are looking for a Senior Data Scientist with expertise in Python, machine learning, and statistical analysis. Experience with TensorFlow and PyTorch is required.",
    "job_title": "Senior Data Scientist",
    "company_name": "AI Tech Corp",
    "job_id": "ai_job_001"
  }'

# 2. Optimize resume
curl -X POST "http://localhost:8000/job-pipeline/optimize-resume" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Data Scientist with Python experience",
    "job_description": "Looking for a Data Scientist with Python, machine learning, TensorFlow, and PyTorch experience",
    "job_title": "Data Scientist",
    "company_name": "Tech Corp",
    "use_analysis": false
  }'

# 3. Generate cover letter
curl -X POST "http://localhost:8000/job-pipeline/generate-cover-letter" \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "Data Scientist",
    "company_name": "Tech Corp",
    "recruiter_name": "Sarah Johnson",
    "job_description": "Looking for a Data Scientist with Python, machine learning, TensorFlow, and PyTorch experience",
    "resume_text": "Data Scientist with 5 years experience in Python, machine learning, and data analysis"
  }'
```

### Scenario 3: Full Pipeline Test (requires all API keys)
```bash
curl -X POST "http://localhost:8000/job-pipeline/full-pipeline" \
  -H "Content-Type: application/json" \
  -d '{
    "job_search_params": {
      "title": "Software Engineer",
      "location": "United States",
      "company_name": [],
      "company_id": [],
      "rows": 5,
      "actor_id": "BHzefUZlZRKWxkTck"
    },
    "resume_path": "sample_resume.txt",
    "db_path": "test_jobs.db",
    "threshold": 40.0,
    "dry_run": true,
    "enrich_contacts": true
  }'
```

## 🐛 Troubleshooting

### Common Issues:

1. **"APIFY_TOKEN environment variable not set"**
   - Set the APIFY_TOKEN environment variable
   - Or test endpoints that don't require job scraping

2. **"OPENAI_API_KEY environment variable not set"**
   - Set the OPENAI_API_KEY environment variable
   - Or test endpoints that don't use AI features

3. **"SENDGRID_API_KEY environment variable not set"**
   - Set the SENDGRID_API_KEY environment variable
   - Or use dry_run=true for email testing

4. **"Module not found" errors**
   - Make sure you're using the virtual environment: `source venv312/bin/activate`
   - Install missing dependencies: `pip install -r requirements.txt`

5. **Database connection errors**
   - The job pipeline uses SQLite by default, no setup required
   - For PostgreSQL features, configure DATABASE_URL

### Testing Without API Keys:

You can test most functionality without API keys:
- Database operations
- Resume text extraction
- Job filtering
- File operations
- Basic validation

## 📊 Expected Responses

### Successful Response Format:
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {...}
}
```

### Error Response Format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## 🎯 Quick Test Checklist

- [ ] Server starts without errors
- [ ] API documentation loads at /docs
- [ ] Database initialization works
- [ ] Resume extraction works
- [ ] Job analysis works (with OpenAI key)
- [ ] Resume optimization works (with OpenAI key)
- [ ] Cover letter generation works (with OpenAI key)
- [ ] Job filtering works
- [ ] Error handling works properly

## 🚀 Production Testing

For production testing:
1. Set all required environment variables
2. Use a real database
3. Test with actual API keys
4. Monitor logs for errors
5. Test email sending (use dry_run=false carefully)
6. Test job scraping with real parameters

Happy testing! 🎉
