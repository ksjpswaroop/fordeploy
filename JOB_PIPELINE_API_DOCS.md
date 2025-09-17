# Job Application Pipeline API Documentation

This document describes the FastAPI endpoints that convert all functions from `job_application_pipeline.py` into REST API endpoints.

## Base URL
```
http://localhost:8000/api/v1/job-pipeline
```

## Authentication
Most endpoints require environment variables to be set:
- `APIFY_TOKEN` - For job scraping
- `OPENAI_API_KEY` - For AI-powered analysis and content generation
- `SENDGRID_API_KEY` - For email sending

## Endpoints

### 1. Search Jobs
**POST** `/search-jobs`

Search for jobs using Apify LinkedIn scraper.

**Request Body:**
```json
{
  "title": "Software Engineer",
  "location": "United States",
  "company_name": ["Google", "Microsoft"],
  "company_id": ["123", "456"],
  "rows": 50,
  "actor_id": "BHzefUZlZRKWxkTck"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully found 25 jobs",
  "total_jobs": 25,
  "jobs": [...],
  "json_file_path": "apify_jobs_20240101_120000.json"
}
```

### 2. Initialize Database
**POST** `/init-database`

Initialize SQLite database for storing jobs.

**Request Body:**
```json
{
  "db_path": "jobs.db"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Database initialized successfully at jobs.db"
}
```

### 3. Save Jobs to Database
**POST** `/save-jobs-to-db`

Save scraped jobs to SQLite database with upsert functionality.

**Request Body:**
```json
[
  {
    "job_id": "123",
    "title": "Software Engineer",
    "companyName": "Google",
    "location": "Mountain View, CA",
    "descriptionHtml": "<p>Job description...</p>"
  }
]
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully saved 1 jobs to database"
}
```

### 4. Enrich Contacts
**POST** `/enrich-contacts`

Enrich job entries with recruiter contact information using Apollo API.

**Request Body:**
```json
{
  "db_path": "jobs.db"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Contact enrichment completed. 5 jobs enriched.",
  "enriched_count": 5
}
```

### 5. Extract Resume Text
**POST** `/extract-resume`

Extract text content from resume file (supports .txt, .md, .pdf, .docx).

**Request Body:**
```json
{
  "resume_path": "/path/to/resume.pdf"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Resume text extracted successfully",
  "resume_text": "John Doe\nSoftware Engineer...",
  "file_type": ".pdf"
}
```

### 6. Analyze Job Match
**POST** `/analyze-job-match`

Analyze job match using OpenAI API for detailed analysis.

**Request Body:**
```json
{
  "resume_text": "Software Engineer with 5 years Python experience",
  "job_description": "Looking for a Python developer with FastAPI experience",
  "job_title": "Senior Python Developer",
  "company_name": "Tech Corp",
  "job_id": "job_123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Job analysis completed successfully",
  "analysis": {
    "job_id": "job_123",
    "job_title": "Senior Python Developer",
    "company_name": "Tech Corp",
    "analysis": {
      "overall_match_score": 85,
      "match_threshold_met": true,
      "matching_criteria": {
        "skills": ["Python", "FastAPI"],
        "experience": ["Software Development"],
        "education": [],
        "tools": ["Python", "FastAPI"]
      },
      "missing_criteria": {
        "skills": ["Docker"],
        "experience": [],
        "certifications": [],
        "domain_knowledge": []
      },
      "recommendations": {
        "resume_updates": ["Add Docker experience"],
        "keywords_to_add": ["Docker", "Microservices"],
        "sections_to_enhance": ["Skills", "Experience"]
      }
    }
  }
}
```

### 7. Match Jobs with Resume
**POST** `/match-jobs`

Find jobs that match the resume based on similarity threshold.

**Request Body:**
```json
{
  "db_path": "jobs.db",
  "resume_text": "Software Engineer with Python experience",
  "threshold": 40.0,
  "use_openai": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Found 3 matching jobs",
  "matching_jobs": [...],
  "total_matches": 3
}
```

### 8. Filter Jobs by Blacklist
**POST** `/filter-jobs`

Filter out jobs from blacklisted companies.

**Request Body:**
```json
{
  "jobs": [
    {
      "job_id": "1",
      "company_name": "Google",
      "job_title": "Software Engineer"
    },
    {
      "job_id": "2",
      "company_name": "Blocked Company",
      "job_title": "Developer"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Filtered 1 jobs from blacklisted companies",
  "filtered_jobs": [...],
  "filtered_count": 1,
  "total_count": 2
}
```

### 9. Optimize Resume
**POST** `/optimize-resume`

Generate ATS-optimized resume using OpenAI API.

**Request Body:**
```json
{
  "resume_text": "Software Engineer with Python experience",
  "job_description": "Looking for a Python developer with FastAPI experience",
  "job_title": "Python Developer",
  "company_name": "Tech Corp",
  "use_analysis": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Resume optimized successfully",
  "optimized_resume": "John Doe\nSoftware Engineer\n..."
}
```

### 10. Generate Cover Letter
**POST** `/generate-cover-letter`

Generate optimized cover letter using OpenAI API.

**Request Body:**
```json
{
  "job_title": "Python Developer",
  "company_name": "Tech Corp",
  "recruiter_name": "Jane Smith",
  "job_description": "Looking for a Python developer with FastAPI experience",
  "resume_text": "Software Engineer with 5 years Python experience"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Cover letter generated successfully",
  "cover_letter": "Dear Jane Smith,\n\nI am writing to express my interest..."
}
```

### 11. Send Email
**POST** `/send-email`

Send email with resume and cover letter via SendGrid.

**Request Body:**
```json
{
  "to_email": "recruiter@company.com",
  "subject": "Application for Python Developer Position",
  "content": "Dear Jane Smith,\n\nI am writing to express my interest...",
  "resume_text": "John Doe\nSoftware Engineer...",
  "dry_run": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Email sent successfully",
  "email_sent": true
}
```

### 12. Full Pipeline
**POST** `/full-pipeline`

Run the complete job application pipeline.

**Request Body:**
```json
{
  "job_search_params": {
    "title": "Software Engineer",
    "location": "United States",
    "company_name": [],
    "company_id": [],
    "rows": 50,
    "actor_id": "BHzefUZlZRKWxkTck"
  },
  "resume_path": "/path/to/resume.pdf",
  "db_path": "jobs.db",
  "threshold": 40.0,
  "dry_run": false,
  "enrich_contacts": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Pipeline completed successfully",
  "total_jobs_found": 25,
  "matching_jobs": 3,
  "emails_sent": 3,
  "files_generated": [
    "resume_job_123.txt",
    "cover_letter_job_123.txt"
  ],
  "pipeline_steps": [
    "Job search initiated",
    "Found 25 jobs",
    "Jobs saved to database",
    "Contact information enriched",
    "Found 3 matching jobs",
    "Sent 3 emails"
  ]
}
```

### 13. Get Job Details
**GET** `/jobs/{job_id}`

Get detailed information about a specific job.

**Parameters:**
- `job_id`: Job identifier
- `db_path`: Database path (query parameter, default: "jobs.db")

**Response:**
```json
{
  "success": true,
  "job": {
    "job_id": "123",
    "job_title": "Software Engineer",
    "company_name": "Google",
    "location": "Mountain View, CA",
    "description_html": "<p>Job description...</p>",
    "poster_name": "John Doe",
    "poster_profile_url": "https://linkedin.com/in/johndoe",
    "contact_name": "Jane Smith",
    "contact_email": "jane@google.com",
    "contact_linkedin": "https://linkedin.com/in/janesmith",
    "raw_json": "{...}"
  }
}
```

### 14. List Jobs
**GET** `/jobs`

List all jobs in the database with pagination.

**Query Parameters:**
- `db_path`: Database path (default: "jobs.db")
- `limit`: Number of jobs to return (default: 50)
- `offset`: Number of jobs to skip (default: 0)

**Response:**
```json
{
  "success": true,
  "jobs": [...],
  "total_count": 100,
  "limit": 50,
  "offset": 0
}
```

### 15. Download File
**GET** `/download/{filename}`

Download generated files (resumes, cover letters, etc.).

**Parameters:**
- `filename`: Name of the file to download

**Response:** File download

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (missing required parameters)
- `404`: Not Found (file or job not found)
- `500`: Internal Server Error

Error responses include a JSON object with:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Environment Variables

Required environment variables:
- `APIFY_TOKEN`: Apify API token for job scraping
- `OPENAI_API_KEY`: OpenAI API key for AI analysis
- `SENDGRID_API_KEY`: SendGrid API key for email sending

## Usage Examples

### Python Client Example
```python
import requests

# Search for jobs
response = requests.post("http://localhost:8000/api/v1/job-pipeline/search-jobs", json={
    "title": "Software Engineer",
    "location": "United States",
    "rows": 10
})

jobs = response.json()["jobs"]

# Extract resume text
resume_response = requests.post("http://localhost:8000/api/v1/job-pipeline/extract-resume", json={
    "resume_path": "my_resume.pdf"
})

resume_text = resume_response.json()["resume_text"]

# Run full pipeline
pipeline_response = requests.post("http://localhost:8000/api/v1/job-pipeline/full-pipeline", json={
    "job_search_params": {
        "title": "Software Engineer",
        "location": "United States",
        "rows": 10
    },
    "resume_path": "my_resume.pdf",
    "dry_run": True
})
```

### cURL Examples
```bash
# Search for jobs
curl -X POST "http://localhost:8000/api/v1/job-pipeline/search-jobs" \
  -H "Content-Type: application/json" \
  -d '{"title": "Software Engineer", "location": "United States", "rows": 10}'

# Extract resume text
curl -X POST "http://localhost:8000/api/v1/job-pipeline/extract-resume" \
  -H "Content-Type: application/json" \
  -d '{"resume_path": "resume.pdf"}'

# List jobs
curl "http://localhost:8000/api/v1/job-pipeline/jobs?limit=10"
```

## Testing

Run the test script to verify all endpoints:
```bash
python test_job_pipeline_api.py
```

Make sure the FastAPI server is running on `http://localhost:8000` before running tests.

## Notes

1. The API maintains backward compatibility with the original pipeline functions
2. All endpoints include proper error handling and validation
3. File operations are handled safely with proper cleanup
4. Database operations use transactions for data integrity
5. Email sending includes dry-run mode for testing
6. The full pipeline endpoint can run the entire workflow in one request
