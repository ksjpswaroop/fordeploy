# Supabase Migration and Setup

This guide moves the backend from local SQLite to Supabase Postgres and prepares optional Supabase client env for the frontend.

## 1) Prereqs
- Supabase project created
- Database credentials (Connection string)
- Local Python venv active

## 2) Configure environment
Copy `.env.example` to `.env` and set:

- SUPABASE_POSTGRES_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/postgres?sslmode=require
- (Optional) NEXT_PUBLIC_API_BASE_URL=http://localhost:8011/api
- (Optional frontend) NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY

Note: settings will prefer SUPABASE_POSTGRES_URL for DATABASE_URL automatically.

## 3) Install deps
- Backend includes psycopg2-binary and asyncpg already in `requirements.txt`.

## 4) Run Alembic migrations against Supabase
Ensure your environment exports SUPABASE_POSTGRES_URL, then:

## 5) Configure Supabase Storage (optional but recommended)
- Create two buckets in Supabase Storage:
	- uploads (public or private)
	- docs (public or private)
- If buckets are private, the backend will issue 1-hour signed URLs.
- Set env vars:
	- SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (or ANON KEY for read-only), SUPABASE_STORAGE_BUCKET_UPLOADS=uploads, SUPABASE_STORAGE_BUCKET_DOCS=docs

## 6) Migrate existing files to Supabase Storage
Run the helper to upload local files:

```
python scripts/migrate_files_to_supabase.py
```

Uploads:
- ./uploads/*  -> uploads bucket with same relative key
- ./generated_docs/run_<id>/* -> docs bucket under runs/<id>/*

## 7) Runtime behavior
- When Supabase Storage is configured, newly uploaded candidate documents and generated resumes/cover letters are mirrored to Storage and APIs will return public or signed URLs in responses. Local filesystem remains as a fallback.

```
source .venv/bin/activate
export SUPABASE_POSTGRES_URL=postgresql+psycopg2://...
python -m alembic upgrade head
```

## 5) One-off data copy from local SQLite (optional)
If you have existing dev data in `recruitment_mvp.db`:

```
source .venv/bin/activate
export SQLITE_DATABASE_URL=sqlite:///./recruitment_mvp.db
export SUPABASE_POSTGRES_URL=postgresql+psycopg2://...
python scripts/migrate_sqlite_to_supabase.py
```

The script creates missing tables and copies rows in dependency order. Primary key conflicts are skipped.

## 6) Run the backend with Supabase
```
source .venv/bin/activate
export SUPABASE_POSTGRES_URL=postgresql+psycopg2://...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8011 --reload
```

## 7) Frontend
- Next.js dev proxies /api and /auth to the backend by default via `next.config.js`.
- If you use Supabase client on the frontend later, set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

## Notes
- In production, manage secrets via your platform’s secret manager.
- Use Alembic for schema changes; avoid `create_all` outside of dev scripts.
