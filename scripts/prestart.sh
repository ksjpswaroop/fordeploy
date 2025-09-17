#!/usr/bin/env sh
set -e

echo "[prestart] Environment: ${ENVIRONMENT:-unknown}"

# Optionally wait for Postgres if DATABASE_URL starts with postgresql or postgres
if printf "%s" "$DATABASE_URL" | grep -Eq "^postgres(ql)?://"; then
  echo "[prestart] Waiting for Postgres to be ready..."
  # Basic wait loop using psql if available or python fallback
  if command -v psql >/dev/null 2>&1; then
    until PGPASSWORD="${PGPASSWORD:-}" psql "$DATABASE_URL" -c '\q' >/dev/null 2>&1; do
      echo "[prestart] Postgres is unavailable - sleeping"
      sleep 1
    done
  else
    python - <<'PY'
import os, time
import sys
import urllib.parse as up
import socket

url = os.environ.get('DATABASE_URL')
if not url:
    sys.exit(0)
p = up.urlparse(url)
host = p.hostname or 'localhost'
port = p.port or 5432
deadline = time.time() + 60
while time.time() < deadline:
    s = socket.socket()
    try:
        s.settimeout(2)
        s.connect((host, port))
        s.close()
        sys.exit(0)
    except Exception:
        time.sleep(1)
print('[prestart] Timed out waiting for Postgres', file=sys.stderr)
sys.exit(1)
PY
  fi
  echo "[prestart] Postgres is up."
fi

# Run Alembic migrations if migrations are present
if [ -d "migrations" ]; then
  echo "[prestart] Running Alembic migrations..."
  if ! alembic upgrade head; then
    echo "[prestart] Alembic upgrade failed; attempting bootstrap via SQLAlchemy create_all + alembic stamp head"
    python - <<'PY'
from app.core.database import create_tables
try:
    create_tables()
    print('[prestart] SQLAlchemy create_all completed')
except Exception as e:
    import sys
    print('[prestart] SQLAlchemy create_all failed:', e, file=sys.stderr)
    sys.exit(1)
PY
    if [ $? -ne 0 ]; then
      echo "[prestart] Bootstrap failed; exiting" >&2
      exit 1
    fi
    alembic stamp head || {
      echo "[prestart] Alembic stamp head failed" >&2
      exit 1
    }
  fi
fi

echo "[prestart] Completed."

# Optional lightweight seed (controlled by SEED_DEMO=1) for initial UI population
if [ "${SEED_DEMO}" = "1" ]; then
  echo "[prestart] Running demo seed if database empty..."
python - <<'PY'
from app.core.database import SessionLocal
from app.models.user import User
from app.models.job import Job, JobStatus, ExperienceLevel
from app.models.application import Application, ApplicationStatus
from app.models.user import User as CandidateUser
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
session = SessionLocal()
try:
  jobs_empty = session.query(Job).count() == 0
  apps_empty = session.query(Application).count() == 0
  if jobs_empty:
    u = session.query(User).filter(User.id==1).first()
    if not u:
      u = User(id=1,email='seed@example.com',username='seed',first_name='Seed',last_name='User',hashed_password=pwd.hash('password'),is_active=True,is_verified=True)
      session.add(u)
      session.flush()
    for i in range(1,4):
      session.add(Job(title=f'Seed Job {i}', description='Initial seeded job', summary='Seed summary', job_type='full-time', work_mode='remote', experience_level=ExperienceLevel.MID, location_country='USA', is_remote=True, status=JobStatus.ACTIVE, created_by=u.id))
    session.commit()
    print('[prestart] Seeded demo jobs')
  if apps_empty:
    try:
      job = session.query(Job).first()
      if job:
        for i in range(1,4):
          cu = session.query(CandidateUser).filter(CandidateUser.email==f'candidate{i}@example.com').first()
          if not cu:
            cu = CandidateUser(email=f'candidate{i}@example.com', username=f'candidate{i}', first_name='Candidate', last_name=str(i), hashed_password=pwd.hash('password'), is_active=True, is_verified=True)
            session.add(cu)
            session.flush()
          app = Application(job_id=job.id, candidate_id=cu.id, candidate_email=cu.email, candidate_name=f'Candidate {i}', status=ApplicationStatus.SUBMITTED)
          session.add(app)
        session.commit()
        print('[prestart] Seeded demo applications')
    except Exception as app_err:
      session.rollback()
      print('[prestart] Application seeding failed:', app_err)
  else:
    print('[prestart] Jobs/applications already present; skipping seed')
except Exception as e:
  print('[prestart] Seeding skipped due to error:', e)
finally:
  session.close()
PY
fi
