# Production Runbook

## Overview
This backend is production-ready with:
- Gunicorn + Uvicorn workers
- Postgres via docker-compose
- Alembic migrations on startup
- CORS configured by `CORS_ORIGINS`
- Dev auth disabled by default in prod

## Quick start (Docker, local production)

1) Copy env template and edit secrets:

```zsh
cp .env.example .env
# edit .env with strong SECRET_KEY and your CORS_ORIGINS
```

2) Bring up Postgres + API:

```zsh
docker compose -f docker-compose.prod.yml up -d --build
```

3) Verify health:

```zsh
curl -s http://127.0.0.1:8080/health | jq .
```

## Notes
- In production, tables are managed by Alembic; app does not auto-create tables.
- To create a new migration:

```zsh
alembic revision -m "change" --autogenerate
alembic upgrade head
```

- To scale workers, set `WEB_CONCURRENCY`.

## DigitalOcean App Platform
- Set the run command: `sh -c "./scripts/prestart.sh && gunicorn -c gunicorn_conf.py app.main:app"`
- Set env: `ENVIRONMENT=production`, `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`
- Disable `DEV_BEARER_TOKEN`.
