from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import logging

# Add parent directory to path to import job_application_pipeline
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import authentication middleware and API routes
from app.auth.middleware import ClerkAuthMiddleware, setup_clerk_middleware
try:
    from app.api.v1 import api_router  # comprehensive v1 router collection
except Exception as import_err:  # pragma: no cover
    import logging as _logging
    _logging.getLogger(__name__).warning(f"Falling back to minimal API (v1 import failed: {import_err})")
    from fastapi import APIRouter as _APIRouter
    api_router = _APIRouter()
from app.api.routers import health, pipeline
from app.api.routers import auth as auth_router
from app.api.routers import admin as admin_router
from app.api.routers import jobflow
from app.api.routers import recruiter_candidates
from app.api.routers import public
from app.api.routers import recruiter_candidate_profile
from app.core.config import settings
from app.core.database import create_tables
from app.core.database import SessionLocal
from app.api.routers.auth import get_password_hash
from app.models.user import User, Role
from app.models.candidate_simple import CandidateSimple  # added for seeding simple candidate names
from app.services import supabase_storage as _supa_mod

app = FastAPI(
    title="AI Recruitment Pipeline",
    description="AI-driven job application automation API with Clerk authentication",
    version="1.0.0",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
)

logger = logging.getLogger(__name__)

# CORS middleware
# Use explicit origins when credentials are enabled to avoid browser blocking with "*"
origins = settings.cors_origins_list
if origins == ["*"]:
    # In local dev, default to Next.js dev server origins so Authorization/cookies work
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conditionally enable Clerk middleware
setup_clerk_middleware(app)

# Include API routes
app.include_router(api_router, prefix="/api")

# Include pipeline routes without authentication
app.include_router(health.router, tags=["health"])
app.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
app.include_router(public.router, prefix="/api", tags=["public"])  # lightweight public data
app.include_router(jobflow.router)
app.include_router(recruiter_candidates.router, prefix="/api")
app.include_router(recruiter_candidate_profile.router, prefix="/api")
# Expose auth endpoints and admin ops
app.include_router(auth_router.router)  # /auth/*
app.include_router(admin_router.router, prefix="/api")  # /api/admin/*

# Static file mount for uploaded resumes (dev only). In production would use proper storage/CDN.
upload_dir = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir, exist_ok=True)
app.mount('/uploads', StaticFiles(directory=upload_dir), name='uploads')

# Expose generated documents (cover letters, resumes) for UI download (dev / simple deployment).
gen_dir = os.path.join(os.getcwd(), 'generated_docs')
if not os.path.exists(gen_dir):
    os.makedirs(gen_dir, exist_ok=True)
app.mount('/generated_docs', StaticFiles(directory=gen_dir), name='generated_docs')

@app.get("/")
async def root():
    """API health check endpoint."""
    return {"status": "online", "service": "AI Recruitment Pipeline"}


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize resources on startup (dev-only table creation)."""
    # Only auto-create tables in non-production and when using SQLite.
    try:
        if settings.ENVIRONMENT != "production" and settings.DATABASE_URL.startswith("sqlite"):
            create_tables()
            logger.info("Database tables ensured/created on startup (dev)")
        else:
            logger.info("Skipping auto table creation (production/migrations expected)")
    except Exception as e:
        logger.warning(f"Database init on startup skipped/failed: {e}")
    # Log Supabase integration status
    try:
        db_mode = "supabase-postgres" if (settings.SUPABASE_POSTGRES_URL or "").strip() else ("sqlite" if settings.DATABASE_URL.startswith("sqlite") else "other-db")
        storage_enabled = settings.supabase_storage_enabled
        storage_client = _supa_mod.get_client() if storage_enabled else None
        logger.info(
            "Supabase status: db=%s storage_enabled=%s storage_client_ready=%s buckets(upload=%s,docs=%s)",
            db_mode,
            storage_enabled,
            bool(storage_client),
            settings.SUPABASE_STORAGE_BUCKET_UPLOADS,
            settings.SUPABASE_STORAGE_BUCKET_DOCS,
        )
    except Exception as se:  # pragma: no cover
        logger.warning(f"Supabase status logging failed: {se}")
    # Seed dedicated candidate demo user (idempotent)
    try:
        db = SessionLocal()
        email = "kc5817@srmist.edu.in"
        password_plain = "scholarIT@123"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Ensure candidate role exists
            role = db.query(Role).filter(Role.name == 'candidate').first()
            if not role:
                role = Role(name='candidate', display_name='Candidate', description='Candidate limited access')
                db.add(role); db.commit(); db.refresh(role)
            user = User(
                email=email,
                first_name="Bhuvan",
                last_name="Candidate",
                hashed_password=get_password_hash(password_plain),
                is_active=True,
                is_verified=True,
            )
            user.roles.append(role)
            db.add(user)
            db.commit(); db.refresh(user)
            logger.info("Seeded candidate user %s", email)
        else:
            # Ensure has candidate role
            if not any(r.name == 'candidate' for r in user.roles):
                role = db.query(Role).filter(Role.name == 'candidate').first()
                if role:
                    user.roles.append(role); db.commit(); db.refresh(user)
            # Remove any non-candidate roles to enforce limited access
            removed_any = False
            for r in list(user.roles):
                if r.name != 'candidate':
                    user.roles.remove(r)
                    removed_any = True
            if removed_any:
                db.commit(); db.refresh(user)
            logger.info("Candidate user already present: %s", email)
    except Exception as se:
        logger.warning(f"Candidate seed failed: {se}")
    finally:
        try:
            db.close()
        except Exception:
            pass
    # Seed recruiter and admin demo accounts
    try:
        db = SessionLocal()
        shared_password = "scholarIT@123"
        recruiter_emails = [
            ("Sriman@svksystems.com", "Sriman"),
            ("kumar@svksystems.com", "Kumar"),
            ("Joseph@svksystems.com", "Joseph"),
            ("Rajv@molinatek.com", "Raj")
        ]
        admin_emails = [
            ("Vamshi@molinatek.com", "Vamshi"),
        ]
        # Ensure roles exist
        def ensure_role(name: str, display: str, desc: str):
            r = db.query(Role).filter(Role.name == name).first()
            if not r:
                r = Role(name=name, display_name=display, description=desc)
                db.add(r); db.commit(); db.refresh(r)
            return r
        recruiter_role = ensure_role('recruiter', 'Recruiter', 'Recruiter access')
        admin_role = ensure_role('admin', 'Admin', 'Administrator full access')
        # Seed recruiters
        for em, first in recruiter_emails:
            u = db.query(User).filter(User.email == em).first()
            if not u:
                u = User(
                    email=em,
                    first_name=first,
                    last_name='Recruiter',
                    hashed_password=get_password_hash(shared_password),
                    is_active=True,
                    is_verified=True,
                )
                u.roles.append(recruiter_role)
                db.add(u)
                db.commit(); db.refresh(u)
                logger.info("Seeded recruiter user %s", em)
            else:
                # Ensure recruiter role present
                if not any(r.name == 'recruiter' for r in u.roles):
                    u.roles.append(recruiter_role); db.commit(); db.refresh(u)
        # Seed admin(s)
        for em, first in admin_emails:
            u = db.query(User).filter(User.email == em).first()
            if not u:
                u = User(
                    email=em,
                    first_name=first,
                    last_name='Admin',
                    hashed_password=get_password_hash(shared_password),
                    is_active=True,
                    is_verified=True,
                    is_superuser=True,
                )
                u.roles.append(admin_role)
                db.add(u)
                db.commit(); db.refresh(u)
                logger.info("Seeded admin user %s", em)
            else:
                # Ensure admin role present and superuser flag
                changed = False
                if not any(r.name == 'admin' for r in u.roles):
                    u.roles.append(admin_role); changed = True
                if not u.is_superuser:
                    u.is_superuser = True; changed = True
                if changed:
                    db.commit(); db.refresh(u)

        # --- Seed baseline candidate name entries for each recruiter (idempotent) ---
        candidate_seed_map = {
            "Sriman@svksystems.com": ["Bhuvan"],
            "kumar@svksystems.com": ["Skanda"],
            "Joseph@svksystems.com": ["Ram"],
            "Rajv@molinatek.com": ["Siddharth"],
        }
        created_any = False
        for rec_email, cand_names in candidate_seed_map.items():
            for cname in cand_names:
                exists = db.query(CandidateSimple).filter(
                    CandidateSimple.recruiter_identifier == rec_email,
                    CandidateSimple.name == cname
                ).first()
                if not exists:
                    obj = CandidateSimple(recruiter_identifier=rec_email, name=cname)
                    db.add(obj)
                    created_any = True
        if created_any:
            db.commit()
            logger.info("Seeded initial recruiter candidate names: %s", {
                k: v for k, v in candidate_seed_map.items()
            })
        else:
            logger.info("Recruiter candidate name seeds already present (no changes)")
    except Exception as se:
        logger.warning(f"Recruiter/admin seed failed: {se}")
    finally:
        try:
            db.close()
        except Exception:
            pass

@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    if settings.clerk_enabled and settings.dev_auth_enabled:
        auth_mode = "clerk+dev-bypass"
    elif settings.clerk_enabled:
        auth_mode = "clerk"
    elif settings.dev_auth_enabled:
        auth_mode = "dev-bypass"
    else:
        auth_mode = "disabled"
    return {
        "status": "healthy",
        "service": "AI Recruitment Pipeline",
        "version": "1.0.0",
        "authentication": auth_mode,
        "supabase": {
            "db": bool((settings.SUPABASE_POSTGRES_URL or "").strip()),
            "storage": settings.supabase_storage_enabled,
        },
    }


@app.get("/api/supabase/status")
async def supabase_status():
    """Diagnostic Supabase status (no secrets)."""
    return {
        "db_url_present": bool((settings.SUPABASE_POSTGRES_URL or "").strip()),
        "effective_db": "supabase-postgres" if (settings.SUPABASE_POSTGRES_URL or "").strip() else ("sqlite" if settings.DATABASE_URL.startswith("sqlite") else "other"),
        "storage_enabled": settings.supabase_storage_enabled,
        "buckets": {
            "uploads": settings.SUPABASE_STORAGE_BUCKET_UPLOADS,
            "docs": settings.SUPABASE_STORAGE_BUCKET_DOCS,
        },
        "env_flags": {
            "SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
            "SUPABASE_ANON_KEY": bool(os.getenv("SUPABASE_ANON_KEY")),
            "SUPABASE_SERVICE_ROLE_KEY": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        },
    }
