# AI Driven Recruitment Backend

A comprehensive FastAPI-based backend system for automating job search and application workflows using AI.

## 🏗️ Architecture Overview

This application follows a clean, modular architecture with the following structure:

```
ai_driven_recruitment_backend/
├── main.py                    # Main FastAPI application entry point
├── docker-compose.yml         # Docker configuration
├── Dockerfile                 # Container setup
├── requirements.txt           # Python dependencies
├── app/                       # Core application package
│   ├── api/                   # API layer
│   │   ├── main.py           # API application setup
│   │   ├── routers/          # API route handlers
│   │   └── routes/           # Additional route definitions
│   ├── core/                 # Core configuration and utilities
│   ├── models/               # Data models
│   ├── schemas/              # Pydantic schemas for API
│   ├── services/             # Business logic services
│   └── db/                   # Database utilities
├── job_application_pipeline.py # Main pipeline logic
├── email_tracker_all_in_one.py # Email tracking service
├── resume_convertion.py       # Resume format conversion
├── coverletter_convertion.py  # Cover letter conversion
├── apollotest.py             # Apollo API integration
├── user_profile.py           # User profile management
├── run_pipeline.py           # Pipeline execution script
└── archive/                  # Archived/legacy code
```

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ai_driven_recruitment_backend
   ```

2. **Start the application:**
   ```bash
   docker-compose up --build
   ```

3. **Access the API:**
   - API Documentation: http://localhost:8080/docs
   - Health Check: http://localhost:8080/health

### Manual Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python main.py
   ```

## 📋 Core Features

### 1. Job Pipeline Automation
- **Job Scraping**: Automated job search using Apify LinkedIn scraper
- **Contact Enrichment**: Find hiring manager contacts using Apollo API
- **Resume Matching**: AI-powered job-resume compatibility analysis
- **Application Sending**: Automated email sending with personalized content

### 2. Document Processing
- **Resume Conversion**: Convert text resumes to formatted DOCX
- **Cover Letter Generation**: Create personalized cover letters
- **Format Standardization**: Consistent document formatting

### 3. Email Management
- **Email Tracking**: Monitor application email status
- **SendGrid Integration**: Reliable email delivery
- **IMAP Support**: Email status verification

### 4. User Management
- **Profile Management**: User preferences and blacklists
- **Company Filtering**: Avoid unwanted companies
- **Skill Matching**: Target relevant opportunities

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# API Keys
OPENAI_API_KEY=your_openai_key
APOLLO_API_KEY=your_apollo_key
SENDGRID_API_KEY=your_sendgrid_key
APIFY_API_TOKEN=your_apify_token

# Database
DATABASE_URL=sqlite:///./jobs.db

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Application Settings
DEBUG=True
LOG_LEVEL=INFO
```

### Authentication modes

The API supports two authentication modes:

- Clerk (production): Set `CLERK_SECRET_KEY` and `CLERK_PUBLISHABLE_KEY` to enable Clerk JWT verification.
- Development bypass (local testing): Set `DEV_BEARER_TOKEN` to a value (e.g., `DEV_BEARER_TOKEN=dev-123`) to allow requests with `Authorization: Bearer <DEV_BEARER_TOKEN>` to be treated as authenticated without Clerk. The provided `docker-compose.yml` sets a default `DEV_BEARER_TOKEN=dev-123` and runs on port 8080.

Additional optional dev claims:

- `DEV_USER_ID` (default `1`)
- `DEV_USER_EMAIL` (default `dev@example.com`)
- `DEV_USER_ROLE` one of `admin|manager|recruiter|candidate` (default `manager`)
- `DEV_TENANT_ID` (default `1`)

Health endpoint shows current mode in `authentication`: `clerk`, `dev-bypass`, or `disabled`.

Quick test in Docker:

```bash
curl -s http://localhost:8080/health
curl -s -H "Authorization: Bearer dev-123" "http://localhost:8080/api/v1/bench/candidates?skip=0&limit=1"
```

## 📚 API Documentation

### Main Endpoints

- `GET /` - Root health check
- `GET /health` - Detailed health status
- `POST /pipeline/scrape` - Scrape jobs from LinkedIn
- `POST /pipeline/enrich` - Enrich jobs with contact info
- `POST /pipeline/match` - Match resume to jobs
- `POST /pipeline/send` - Send job applications

### Pipeline Workflow

1. **Scrape Jobs**: Use the scraping endpoint to find relevant positions
2. **Enrich Contacts**: Add hiring manager information to job listings
3. **Match Resume**: Analyze job compatibility with your resume
4. **Send Applications**: Automatically send personalized applications

### Notifications API (v1)

Deprecated: `/api/v1/common/notifications` now returns 410. Use `/api/v1/notifications` instead.

Endpoints:
- GET `/api/v1/notifications` — Paginated list. Query: `read`, `dismissed`, `skip`, `limit`, `order` (asc|desc). Dismissed are excluded by default.
- PATCH `/api/v1/notifications/{id}/read` — Mark as read.
- PATCH `/api/v1/notifications/{id}/dismiss` — Dismiss.
- GET `/api/v1/notifications/unread-count` — Unread count (excludes dismissed).
- PUT `/api/v1/notifications/mark-all-read` — Mark all unread as read.
- DELETE `/api/v1/notifications/{id}` — Hard delete.

### Pagination

List endpoints return a consistent `PaginatedResponse` with `data` and `meta` (total, page, page_size, total_pages, has_next, has_prev). Notifications and bench have been updated accordingly.

## 🛠️ Development

### Frontend API Base & Login

When the Next.js frontend runs separately from FastAPI you must tell the frontend where to send auth requests. Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8011
```

The login helper now uses this (or defaults to `http://127.0.0.1:8011`). Without it a relative `/auth/login` call could be served by Next.js itself and fail.

Troubleshooting steps if login fails:
1. Backend health: `curl -s http://127.0.0.1:8011/health` should return JSON including status.
2. Direct auth test:
    ```bash
    curl -s -X POST \
       -H 'Content-Type: application/x-www-form-urlencoded' \
       -d 'grant_type=password&username=you@example.com&password=YourPass123' \
       http://127.0.0.1:8011/auth/login
    ```
3. Browser DevTools > Network: confirm `/auth/login` request URL host is 127.0.0.1:8011 not localhost:3000.
4. If you see HTML in response, it's hitting Next.js not FastAPI (set env var / restart dev server).
5. Email case: frontend now lowercases email; existing users created with mixed-case still match if database values are exact.
6. For persistent 401 check user record has a bcrypt hashed password and `is_active=1`.


### Project Structure Guidelines

- **app/api/**: Contains the main FastAPI application and routers
- **app/models/**: Database models and data structures
- **app/schemas/**: Pydantic models for API validation
- **app/services/**: Business logic and external service integrations
- **Root level**: Standalone scripts and utilities

### Code Organization

- All redundant and legacy code has been moved to the `archive/` directory
- The main application entry point is `main.py`
- API routes are organized in `app/api/routers/`
- Business logic is separated into service classes

### CI & Quality Gates

- Tests run with coverage and fail under 85%.
- Ruff, Black, and MyPy are enforced in CI.

### Adding New Features

1. Create models in `app/models/`
2. Define schemas in `app/schemas/`
3. Implement business logic in `app/services/`
4. Add API routes in `app/api/routers/`
5. Update the main router includes in `app/api/main.py`

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed via `requirements.txt`
2. **API Key Issues**: Verify all required environment variables are set
3. **Database Errors**: Check database permissions and file paths
4. **Email Delivery**: Verify SendGrid configuration and API limits

### Logs and Debugging

- Application logs are available in the container output
- Set `DEBUG=True` for detailed error messages
- Use `LOG_LEVEL=DEBUG` for verbose logging

## 🧪 Reliable Local Development (New Scripts)

Use the helper scripts for a stable dev loop:

```
./dev_start.sh   # Launch backend (default :8011) wait for /health then start frontend (:3000)
./dev_stop.sh    # Stop tracked backend/frontend processes
```

What they do:
- Kill stale processes using `.backend_pid` / `.frontend_pid`.
- Wait for backend health before launching frontend.
- Export `NEXT_PUBLIC_API_BASE` pointing at backend `/api`.
- Provide clear exit codes if a component fails to become ready.

Optional env overrides before running:
```
export BACKEND_PORT=8011
export FRONTEND_PORT=3000
export DEV_BEARER_TOKEN=dev-local-token
export NEXT_PUBLIC_API_BASE=http://127.0.0.1:8011/api
```

Smoke test after start:
```
curl -s http://127.0.0.1:8011/health
curl -s http://localhost:3000/api/health
```

If things get stuck: `./dev_stop.sh` then `./dev_start.sh` again.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the API documentation at `/docs`
- Review the troubleshooting section
- Create an issue in the repository

---

**Note**: This codebase has been recently cleaned and organized. Legacy code and redundant files have been moved to the `archive/` directory for reference.
