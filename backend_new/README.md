# AI-Driven Recruitment Backend API

A FastAPI-based backend service for AI-driven recruitment platform.

## Features

- FastAPI REST API
- SQLAlchemy ORM with Alembic migrations
- JWT Authentication
- AI-powered candidate matching
- Email automation with SendGrid
- Web scraping capabilities with Apify
- PostgreSQL/SQLite database support

## Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Database Setup**
   ```bash
   alembic upgrade head
   ```

4. **Run Development Server**
   ```bash
   python main.py
   # or
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Digital Ocean Deployment

1. **Using Docker**
   ```bash
   docker build -f Dockerfile -t recruitment-backend .
   docker run -p 8000:8000 recruitment-backend
   ```

2. **Using App Platform**
   - Use the `backend-app.yaml` configuration
   - Set environment variables in Digital Ocean dashboard
   - Deploy directly from GitHub

## Environment Variables

See `.env.example` for all required environment variables:

- `DATABASE_URL`: Database connection string
- `OPENAI_API_KEY`: OpenAI API key for AI features
- `SENDGRID_API_KEY`: SendGrid for email automation
- `APIFY_API_TOKEN`: Apify for web scraping

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
backend_new/
├── app/                 # Main application code
│   ├── api/            # API routes
│   ├── core/           # Core configuration
│   ├── models/         # Database models
│   ├── schemas/        # Pydantic schemas
│   └── services/       # Business logic
├── migrations/         # Alembic migrations
├── tests/             # Test suite
├── scripts/           # Deployment scripts
└── requirements.txt   # Python dependencies
```

## Testing

```bash
pytest
```

## Deployment

See `DEPLOY_BACKEND.md` for detailed deployment instructions.