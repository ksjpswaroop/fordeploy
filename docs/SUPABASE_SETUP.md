# Supabase Integration Setup

This guide explains how to enable Supabase (Postgres + Storage) for the AI Recruitment Backend.

## 1. Prerequisites
- Supabase project created
- Service Role Key and Anon Key available
- Postgres connection info (project ref + password)
- Buckets to create: `docs`, `uploads` (public)

## 2. Environment Variables
Add to `.env` (see `.env.example`):
```
SUPABASE_POSTGRES_URL=postgresql+psycopg2://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require
SUPABASE_SERVICE_ROLE_KEY=...  # server only
SUPABASE_URL=https://<PROJECT_REF>.supabase.co
SUPABASE_ANON_KEY=...          # optional front-end use
SUPABASE_STORAGE_BUCKET_DOCS=docs
SUPABASE_STORAGE_BUCKET_UPLOADS=uploads
```
If `SUPABASE_POSTGRES_URL` is set it overrides the normal `DATABASE_URL`.

## 3. Buckets
In Supabase Dashboard → Storage:
1. Create bucket `docs` (public)
2. Create bucket `uploads` (public)
3. (Optional) If private buckets desired, make them private and rely on signed URLs (update code to call `create_signed_url`).

## 4. Data Migration
Run once to copy existing SQLite data into Supabase Postgres.
```
source .venv/bin/activate
python scripts/migrate_sqlite_to_supabase.py --skip-empty
```
Script auto-detects `SUPABASE_POSTGRES_URL`. Check output: `Total copied rows:` should match expectations.

## 5. File Migration (Local → Storage)
```
python scripts/migrate_files_to_supabase.py --verbose
```
Use `--dry-run` first if cautious.

## 6. Restart Backend
Stop any running uvicorn then:
```
python -m uvicorn app.main:app --port 8011 --reload
```
On startup logs should show: `Supabase DB enabled: True, Storage enabled: True`.

## 7. Verify Health
```
curl -s http://localhost:8011/health | jq
```
Expect:
```
"supabase": { "db": true, "storage": true }
```

## 8. Functionality Checks
- Trigger job pipeline: POST /api/jobs/run
- Inspect generated document URLs: should begin with `https://<PROJECT_REF>.supabase.co/storage/v1/object/public/docs/`
- Upload candidate resume: response should include URL in `uploads` bucket.

## 9. Troubleshooting
| Symptom | Cause | Fix |
| ------- | ----- | --- |
| db=false | Bad `SUPABASE_POSTGRES_URL` or network | Validate URL; ensure psycopg2 installed |
| storage=false | Missing service role key or bucket | Check env vars & bucket names |
| 403 on file URL | Bucket private | Make public or implement signed URL route |
| Counts mismatch after migration | Migration skipped table | Re-run without `--skip-empty` for that table |

## 10. Rollback / Disable
Unset `SUPABASE_POSTGRES_URL` (and storage vars) then restart; app falls back to SQLite & local filesystem.

## 11. Next Steps
- Add signed URL endpoint for private buckets (if required)
- Add retry/backoff for uploads
- Add unit tests mocking Supabase client

---
Document version: 1.0
