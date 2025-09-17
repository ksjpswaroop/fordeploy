from __future__ import annotations
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
import os, json, hashlib, shutil, concurrent.futures, time, uuid, sqlite3
import asyncio

from app.models import PipelineRun, RunStatus, Stage, ScrapedJob
from app.core.database import SessionLocal
from app.services.pipeline_orchestrator import run_pipeline
from app.services.apollo_enrichment import search_recruiter_contacts
from job_application_pipeline import extract_resume_text
from job_application_pipeline import (
    generate_optimized_cover_letter,
    generate_ats_optimized_resume_with_analysis,
    analyze_job_match_with_openai,
    clean_html,
    send_email_via_sendgrid,
)
from app.core.config import settings
import sqlite3  # kept for read access helpers
from app.services.apollo_enrichment import find_recruiter_contact
from app.services.apollo_enrichment import search_recruiter_contacts as _search_multi_contacts
from app.services.supabase_storage import upload_bytes, get_public_url, create_signed_url, list_prefix  # safe even if None when not configured

# Optional: expose email tracker DB (events.db) if present
def _get_events_conn():
    """Read-only style connection (returns None if file missing)."""
    db_path = os.getenv('TRACKING_DB_PATH', 'events.db')
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None

def _get_events_conn_writable():
    """Ensure events.db exists with required tables and return connection."""
    db_path = os.getenv('TRACKING_DB_PATH', 'events.db')
    try:
        conn = sqlite3.connect(db_path)
        # Return rows as dict-like objects for r['col'] access
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # Create tables if they do not exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                to_email TEXT,
                subject TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                provider_msgid TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg_id TEXT,
                event TEXT,
                email TEXT,
                url TEXT,
                reason TEXT,
                timestamp INTEGER
            )
        """)
        conn.commit()
        return conn
    except Exception:
        try:
            conn.close()
        except Exception:  # pragma: no cover - best effort
            pass
        return None

def _record_tracked_email(email: str, subject: str, status: str, provider_msgid: str | None = None):
    """Insert (or upsert) a tracked message + initial event so UI can display it.

    We intentionally create a new synthetic message id for each send attempt so the
    UI reflects individual actions (including dry-run previews).
    """
    conn = _get_events_conn_writable()
    if not conn:
        return
    try:
        msg_id = uuid.uuid4().hex
        ts = int(time.time())
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO messages(id,to_email,subject,provider_msgid) VALUES (?,?,?,?)",
            (msg_id, email, subject, provider_msgid)
        )
        cur.execute(
            "INSERT INTO events(msg_id,event,email,timestamp) VALUES (?,?,?,?)",
            (msg_id, status, email, ts)
        )
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

router = APIRouter(prefix="/api", tags=["jobflow"])  # global prefix alignment


class QuickSearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    limit: int = 15

class QuickSearchJob(BaseModel):
    title: str
    company: Optional[str]
    location: Optional[str]
    url: Optional[str]
    source: str

@router.post("/search/jobs", response_model=List[QuickSearchJob])
async def quick_search_jobs(payload: QuickSearchRequest):
    """Lightweight job search without creating a full pipeline run.

    Attempts Indeed scrape only. If zero results, seeds demo samples so the UI always shows something.
    """
    from app.services.scrape_indeed import scrape_indeed
    results: list[QuickSearchJob] = []
    try:
        indeed_jobs = await scrape_indeed(query=payload.query, location=payload.location, pages=1)
    except Exception:
        indeed_jobs = []
    for j in indeed_jobs[:payload.limit]:
        title = j.get("title")
        if not title:
            continue
        results.append(QuickSearchJob(
            title=title,
            company=j.get("company"),
            location=j.get("location"),
            url=j.get("url"),
            source="indeed"
        ))
    if not results:
        # fallback demo jobs
        demo_samples = [
            (f"{payload.query.title()} Engineer", "Acme Corp", payload.location or "Remote", "https://example.com/job/acme"),
            (f"Senior {payload.query.title()} Developer", "Globex", payload.location or "USA", "https://example.com/job/globex"),
            (f"{payload.query.title()} Specialist", "Initech", payload.location or "Europe", "https://example.com/job/initech"),
        ]
        for t,c,l,u in demo_samples[:payload.limit]:
            results.append(QuickSearchJob(title=t, company=c, location=l, url=u, source="demo"))
    return results


@router.get("/health")
async def health():
    """Composite health check including external service probes (lightweight)."""
    results: dict[str, dict] = {}
    # OpenAI check: validate API key format / quick model list (head request fallback)
    try:
        key = settings.OPENAI_API_KEY
        if not key:
            results['openai'] = {"ok": False, "error": "missing_key"}
        else:
            # avoid full model list (may require billing); simple format check
            if not key.startswith('sk-') and 'svcacct' not in key:
                results['openai'] = {"ok": False, "error": "invalid_format"}
            else:
                results['openai'] = {"ok": True}
    except Exception as e:  # noqa: BLE001
        results['openai'] = {"ok": False, "error": str(e)[:120]}

    # Apollo.io API key basic check (no external call to avoid latency)
    try:
        if settings.APOLLO_API_KEY:
            masked = settings.APOLLO_API_KEY[:4] + "***" + settings.APOLLO_API_KEY[-4:]
            results['apollo'] = {"ok": True, "key_masked": masked}
        else:
            results['apollo'] = {"ok": False, "error": "missing_key"}
    except Exception as e:  # noqa: BLE001
        results['apollo'] = {"ok": False, "error": str(e)[:120]}

    # SendGrid quick check: attempt a /v3/user/account (requires auth) HEAD fallback to mail send endpoint
    try:
        if not settings.SENDGRID_API_KEY:
            results['sendgrid'] = {"ok": False, "error": "missing_key"}
        else:
            import httpx
            # Use a very short timeout; we only care if auth header structure accepted (2xx or 4xx w/ auth nuance)
            url = 'https://api.sendgrid.com/v3/user/account'
            headers = {"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"}
            try:
                async with httpx.AsyncClient(timeout=3.5) as client:
                    r = await client.get(url, headers=headers)
                if r.status_code in (200, 201):
                    results['sendgrid'] = {"ok": True}
                elif r.status_code == 401:
                    results['sendgrid'] = {"ok": False, "error": "unauthorized"}
                else:
                    results['sendgrid'] = {"ok": True, "status": r.status_code}
            except Exception as sx:  # network error
                results['sendgrid'] = {"ok": False, "error": f"net:{str(sx)[:60]}"}
    except Exception as e:  # noqa: BLE001
        results['sendgrid'] = {"ok": False, "error": str(e)[:120]}

    overall = all(section.get('ok') for section in results.values()) if results else True
    return {"ok": overall, "services": results}


class RunRequest(BaseModel):
    query: str
    locations: Optional[List[str]] = None
    sources: Optional[List[str]] = ["indeed"]
    auto_send: bool = False
    resume_profile: Optional[dict] = None
    email_template: Optional[str] = None


class RunStartResponse(BaseModel):
    task_id: str


class RunStatusResponse(BaseModel):
    id: int
    status: str
    stage: str
    counts: dict  # may now include generated, generation_progress
    errors: List[str] = []


@router.post("/jobs/run", response_model=RunStartResponse)
async def start_run(req: RunRequest):
    db = SessionLocal()
    run = PipelineRun(query=req.query, locations=req.locations, sources=req.sources or ["indeed"], counts={})
    db.add(run)
    db.commit()
    db.refresh(run)
    # Basic log in counts immediately so UI sees pending run even if pipeline fails early
    run.counts = run.counts or {}
    db.add(run); db.commit()
    # Execute pipeline inline (temporary) to ensure deterministic insertion for demo
    # Launch pipeline in background so client can poll for progressive counts
    asyncio.create_task(run_pipeline(run.id, req.query, req.locations, req.sources))
    return RunStartResponse(task_id=str(run.id))


@router.get("/runs/{task_id}", response_model=RunStatusResponse)
async def get_run(task_id: str):
    db = SessionLocal()
    run = db.get(PipelineRun, int(task_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunStatusResponse(
        id=run.id,
        status=run.status.value,
        stage=run.stage,
        counts=run.counts or {},
        errors=[run.error] if run.error else []
    )


class RunJobItem(BaseModel):
    id: int
    title: str
    company: str | None
    url: str | None
    location: str | None
    recruiter_name: str | None = None
    recruiter_email: str | None = None
    recruiter_contacts: list[dict] | None = None  # list of {name,title,email,linkedin_url}
    cover_letter: str | None = None
    resume_custom: str | None = None
    resume_txt_url: str | None = None
    resume_docx_url: str | None = None
    resume_match: float | None = None  # 0-100 similarity percent

class JobRecruiterContact(BaseModel):
    job_id: int
    contacts: list[dict]

class CoverLetterDoc(BaseModel):
    job_id: int
    docx_filename: str
    size: int

class JobDetailResponse(BaseModel):
    id: int
    run_id: int
    title: str
    company: str | None
    url: str | None
    location: str | None
    recruiter_name: str | None
    recruiter_email: str | None
    recruiter_contacts: list[dict] | None = None
    cover_letter: str | None
    resume_custom: str | None
    resume_txt_url: str | None = None
    resume_docx_url: str | None = None
    resume_match: float | None = None

@router.get("/runs/{task_id}/jobs/{job_id}/details", response_model=JobDetailResponse)
async def get_job_details(task_id: str, job_id: int, request: Request):
    db = SessionLocal()
    job = db.get(ScrapedJob, job_id)
    if not job or job.run_id != int(task_id):
        raise HTTPException(status_code=404, detail="Job not found for run")
    import os, json as _json
    base_url = str(request.base_url).rstrip('/')
    run_dir = os.path.join(os.getcwd(), 'generated_docs', f'run_{task_id}')
    txt_path = os.path.join(run_dir, f'resume_job{job.id}.txt')
    docx_path = os.path.join(run_dir, f'resume_job{job.id}.docx')
    txt_url = f"{base_url}/generated_docs/run_{task_id}/resume_job{job.id}.txt" if os.path.exists(txt_path) else None
    docx_url = f"{base_url}/generated_docs/run_{task_id}/resume_job{job.id}.docx" if os.path.exists(docx_path) else None
    from app.core.config import settings as _settings
    if _settings.supabase_storage_enabled:
        try:
            key_txt = f"runs/{task_id}/resume_job{job.id}.txt"
            key_docx = f"runs/{task_id}/resume_job{job.id}.docx"
            supa_txt = get_public_url(_settings.SUPABASE_STORAGE_BUCKET_DOCS, key_txt) or create_signed_url(_settings.SUPABASE_STORAGE_BUCKET_DOCS, key_txt, 3600)
            supa_docx = get_public_url(_settings.SUPABASE_STORAGE_BUCKET_DOCS, key_docx) or create_signed_url(_settings.SUPABASE_STORAGE_BUCKET_DOCS, key_docx, 3600)
            txt_url = supa_txt or txt_url
            docx_url = supa_docx or docx_url
        except Exception:
            pass
    recruiter_contacts = None
    if job.metadata_json:
        try:
            meta = _json.loads(job.metadata_json) or {}
            if isinstance(meta.get('recruiter_contacts'), list):
                recruiter_contacts = meta.get('recruiter_contacts')
        except Exception:
            recruiter_contacts = None
    # Live fetch if missing and Apollo available; then persist
    if recruiter_contacts is None:
        try:
            if settings.APOLLO_API_KEY and job.company and job.title:
                from app.services.apollo_enrichment import search_recruiter_contacts as _live_search
                live = _live_search(job.company, job.title, max_results=5) or []
                if live:
                    recruiter_contacts = live
                    try:
                        meta = (job.metadata_json and _json.loads(job.metadata_json)) or {}
                    except Exception:
                        meta = {}
                    meta['recruiter_contacts'] = live
                    job.metadata_json = _json.dumps(meta)
                    db.add(job)
                    db.commit()
        except Exception:
            pass
    # Compute lightweight resume match if resume_text present in run metadata
    resume_match_val = None
    try:
        run = db.get(PipelineRun, int(task_id)) if 'PipelineRun' in globals() else None
    except Exception:
        run = None
    resume_text = None
    try:
        if run and getattr(run, 'metadata_json', None):
            _meta = _json.loads(run.metadata_json) or {}
            resume_text = _meta.get('resume_text')
    except Exception:
        resume_text = None
    if resume_text and job.description:
        try:
            # Simple token overlap ratio (case-insensitive unique tokens)
            import re
            toks_r = set(re.findall(r"[a-zA-Z0-9]+", resume_text.lower()))
            toks_j = set(re.findall(r"[a-zA-Z0-9]+", job.description.lower()))
            if toks_r and toks_j:
                overlap = len(toks_r & toks_j)
                denom = min(len(toks_r), len(toks_j)) or 1
                resume_match_val = round((overlap/denom)*100, 1)
        except Exception:
            resume_match_val = None
    return JobDetailResponse(
        id=job.id,
        run_id=job.run_id,
        title=job.title,
        company=job.company,
        url=job.url,
        location=job.location,
        recruiter_name=job.recruiter_name,
        recruiter_email=job.recruiter_email,
        recruiter_contacts=recruiter_contacts,
        cover_letter=job.cover_letter,
        resume_custom=job.resume_custom,
        resume_txt_url=txt_url,
        resume_docx_url=docx_url,
        resume_match=resume_match_val
    )

class EnrichJobResponse(BaseModel):
    id: int
    recruiter_name: str | None
    recruiter_email: str | None
    enriched: bool

class BulkEnrichResponse(BaseModel):
    run_id: int
    processed: int
    updated_with_email: int
    updated_name_only: int
    skipped_missing_fields: int
    no_contact_found: int
    exceptions: int
    acted_on_job_ids: list[int] = []  # jobs we attempted (after filters/force)
    forced: bool = False
    debug: Optional[dict] = None  # optional extra diagnostics when ?debug=1



@router.get("/runs/{task_id}/jobs", response_model=List[RunJobItem])
async def list_run_jobs(task_id: str, request: Request):
    db = SessionLocal()
    jobs = db.query(ScrapedJob).filter(ScrapedJob.run_id == int(task_id)).limit(200).all()
    # Determine file base path; files are stored under generated_docs/run_<id>
    import os
    run_dir = os.path.join(os.getcwd(), 'generated_docs', f'run_{task_id}')
    items = []
    base = str(request.base_url).rstrip('/')
    from app.core.config import settings as _settings
    supa_enabled = _settings.supabase_storage_enabled
    bucket_docs = _settings.SUPABASE_STORAGE_BUCKET_DOCS if supa_enabled else None
    # Attempt to load resume_text once
    resume_text = None
    try:
        run_obj = db.get(PipelineRun, int(task_id))
        if run_obj and getattr(run_obj, 'metadata_json', None):
            import json as _json2
            _meta = _json2.loads(run_obj.metadata_json) or {}
            resume_text = _meta.get('resume_text')
    except Exception:
        resume_text = None
    for j in jobs:
        txt_path = os.path.join(run_dir, f'resume_job{j.id}.txt')
        docx_path = os.path.join(run_dir, f'resume_job{j.id}.docx')
        txt_url = f"{base}/generated_docs/run_{task_id}/resume_job{j.id}.txt" if os.path.exists(txt_path) else None
        docx_url = f"{base}/generated_docs/run_{task_id}/resume_job{j.id}.docx" if os.path.exists(docx_path) else None
        # Prefer Supabase URLs when available
        if supa_enabled:
            key_txt = f"runs/{task_id}/resume_job{j.id}.txt"
            key_docx = f"runs/{task_id}/resume_job{j.id}.docx"
            try:
                supa_txt = get_public_url(bucket_docs, key_txt) or create_signed_url(bucket_docs, key_txt, 3600)
                supa_docx = get_public_url(bucket_docs, key_docx) or create_signed_url(bucket_docs, key_docx, 3600)
                txt_url = supa_txt or txt_url
                docx_url = supa_docx or docx_url
            except Exception:
                pass
        recruiter_contacts: list[dict] | None = None
        # Attempt to pull cached recruiter_contacts from metadata_json if present
        try:
            if j.metadata_json:
                import json as _json
                meta = _json.loads(j.metadata_json)
                if isinstance(meta, dict) and isinstance(meta.get('recruiter_contacts'), list):
                    recruiter_contacts = meta.get('recruiter_contacts')[:5]
        except Exception:
            recruiter_contacts = None
        # compute resume match if possible
        resume_match_val = None
        if resume_text and j.description:
            try:
                import re
                toks_r = set(re.findall(r"[a-zA-Z0-9]+", resume_text.lower()))
                toks_j = set(re.findall(r"[a-zA-Z0-9]+", (j.description or '').lower()))
                if toks_r and toks_j:
                    overlap = len(toks_r & toks_j)
                    denom = min(len(toks_r), len(toks_j)) or 1
                    resume_match_val = round((overlap/denom)*100, 1)
            except Exception:
                resume_match_val = None
        items.append(RunJobItem(
            id=j.id, title=j.title, company=j.company, url=j.url, location=j.location,
            recruiter_name=j.recruiter_name, recruiter_email=j.recruiter_email,
            recruiter_contacts=recruiter_contacts,
            cover_letter=j.cover_letter, resume_custom=j.resume_custom,
            resume_txt_url=txt_url, resume_docx_url=docx_url,
            resume_match=resume_match_val
        ))
    return items

@router.post("/jobs/{job_id}/enrich", response_model=EnrichJobResponse)
async def enrich_single_job(job_id: int):
    """Force Apollo enrichment for a single scraped job (manual test helper)."""
    db = SessionLocal()
    try:
        j = db.get(ScrapedJob, job_id)
        if not j:
            raise HTTPException(status_code=404, detail="Job not found")
        contact = None
        if settings.APOLLO_API_KEY and j.company and j.title:
            try:
                contact = find_recruiter_contact(j.company, j.title)
            except Exception as e:  # noqa: BLE001
                contact = None
        from datetime import datetime as _dt
        if contact:
            prev_name = j.recruiter_name
            if contact.get("name"):
                j.recruiter_name = contact.get("name")
            email_val = contact.get("email") or None
            if email_val:
                j.recruiter_email = email_val
            # Cache multiple contacts for UI expansion
            try:
                multi = search_recruiter_contacts(j.company, j.title, max_results=5) or []
            except Exception:
                multi = []
            if multi:
                import json as _json
                meta = {}
                if j.metadata_json:
                    try:
                        meta = _json.loads(j.metadata_json) or {}
                    except Exception:
                        meta = {}
                meta['recruiter_contacts'] = multi
                j.metadata_json = _json.dumps(meta)
            j.enriched_at = _dt.utcnow()
            db.commit()
            enriched_flag = bool(j.recruiter_email)
            import logging as _log
            _log.info("Manual enrich job=%s name=%s email=%s", j.id, j.recruiter_name, 'SET' if j.recruiter_email else 'MISSING')
            return EnrichJobResponse(id=j.id, recruiter_name=j.recruiter_name, recruiter_email=j.recruiter_email, enriched=enriched_flag)
        return EnrichJobResponse(id=j.id, recruiter_name=j.recruiter_name, recruiter_email=j.recruiter_email, enriched=bool(j.recruiter_email))
    finally:
        db.close()

@router.post("/runs/{task_id}/enrich", response_model=BulkEnrichResponse)
async def bulk_enrich(task_id: int, limit: int = 200, force: bool = False, debug: int = 0):
    """Re-run Apollo enrichment for jobs in a run.

    Behavior:
    - If force=False: only jobs without recruiter_email are retried.
    - If force=True: jobs are retried even if email already present (could refresh name/email).
    - Always preserves recruiter_name when available, even if email remains locked.

    Debug Mode (?debug=1): returns additional diagnostics: per_reason_job_ids, sample_contacts.
    """
    db = SessionLocal()
    try:
        run = db.get(PipelineRun, int(task_id))
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        base_q = db.query(ScrapedJob).filter(ScrapedJob.run_id == run.id)
        jobs = base_q.limit(limit).all()
        processed = updated_email = updated_name_only = 0
        skipped_missing_fields = no_contact = exceptions = 0
        acted_on: list[int] = []
        reason_map: dict[str, list[int]] = {"skipped_missing_fields": [], "no_contact": [], "updated_email": [], "updated_name_only": [], "exception": [], "already_enriched": []}
        sample_contacts: dict[int, dict] = {}
        from app.services.apollo_enrichment import find_recruiter_contact
        import logging as _log
        for j in jobs:
            if j.recruiter_email and not force:
                reason_map["already_enriched"].append(j.id)
                continue
            # We'll attempt this job
            if not (settings.APOLLO_API_KEY and j.company and j.title):
                skipped_missing_fields += 1
                reason_map["skipped_missing_fields"].append(j.id)
                continue
            acted_on.append(j.id)
            processed += 1
            try:
                contact = find_recruiter_contact(j.company, j.title)
                # Also capture multiple contacts for dashboard expansion (cache in metadata_json)
                try:
                    multi = _search_multi_contacts(j.company, j.title, max_results=5) or []
                except Exception:
                    multi = []
                if multi:
                    import json as _json
                    meta = {}
                    if j.metadata_json:
                        try:
                            meta = _json.loads(j.metadata_json) or {}
                        except Exception:
                            meta = {}
                    meta['recruiter_contacts'] = multi
                    j.metadata_json = _json.dumps(meta)
            except Exception as e:  # noqa: BLE001
                exceptions += 1
                reason_map["exception"].append(j.id)
                _log.info("Bulk enrich exception job=%s: %s", j.id, e)
                continue
            if not contact:
                no_contact += 1
                reason_map["no_contact"].append(j.id)
                continue
            # Capture sample contact for debug purposes
            if debug:
                # Redact email partially
                cpy = dict(contact)
                em = cpy.get("email")
                if em and len(em) > 5:
                    cpy["email"] = em[:2] + "***" + em[-2:]
                sample_contacts[j.id] = {k: cpy.get(k) for k in ("name", "email", "title") if k in cpy}
            if contact.get("name"):
                j.recruiter_name = contact.get("name")
            if contact.get("email"):
                j.recruiter_email = contact.get("email")
                updated_email += 1
                reason_map["updated_email"].append(j.id)
            else:
                updated_name_only += 1
                reason_map["updated_name_only"].append(j.id)
        db.commit()
        debug_blob = None
        if debug:
            debug_blob = {
                "reason_job_ids": {k: v for k, v in reason_map.items() if v},
                "sample_contacts": sample_contacts,
                "total_jobs_in_run": base_q.count(),
                "limit": limit,
            }
        return BulkEnrichResponse(
            run_id=run.id,
            processed=processed,
            updated_with_email=updated_email,
            updated_name_only=updated_name_only,
            skipped_missing_fields=skipped_missing_fields,
            no_contact_found=no_contact,
            exceptions=exceptions,
            acted_on_job_ids=acted_on,
            forced=force,
            debug=debug_blob,
        )
    finally:
        db.close()

@router.get("/runs/{task_id}/recruiters", response_model=List[JobRecruiterContact])
async def list_run_recruiters(task_id: str, max_per_job: int = 3):
    """Return real Apollo recruiter contacts per job (live lookup, no fallbacks)."""
    db = SessionLocal()
    jobs = db.query(ScrapedJob).filter(ScrapedJob.run_id == int(task_id)).limit(60).all()
    out: list[JobRecruiterContact] = []
    for j in jobs:
        if not j.company or not j.title:
            out.append(JobRecruiterContact(job_id=j.id, contacts=[]))
            continue
        try:
            contacts = search_recruiter_contacts(j.company, j.title, max_results=max_per_job) or []
        except Exception:
            contacts = []
        out.append(JobRecruiterContact(job_id=j.id, contacts=contacts))
    return out

@router.get("/runs/{task_id}/coverletters", response_model=List[CoverLetterDoc])
async def list_cover_letter_docs(task_id: str):
    import os
    run_dir = os.path.abspath(os.path.join(os.getcwd(), 'generated_docs', f'run_{task_id}'))
    out: list[CoverLetterDoc] = []
    from app.core.config import settings as _settings
    supa_enabled = _settings.supabase_storage_enabled
    if supa_enabled:
        try:
            entries = list_prefix(_settings.SUPABASE_STORAGE_BUCKET_DOCS, f"runs/{task_id}")
            for ent in entries:
                name = ent.get("name") or ""
                if name.endswith('.docx') and name.startswith('cover_letter_job'):
                    try:
                        job_id = int(name.split('job')[1].split('.')[0])
                    except Exception:
                        continue
                    size = int(ent.get("metadata", {}).get("size", ent.get("size", 0)) or 0)
                    out.append(CoverLetterDoc(job_id=job_id, docx_filename=name, size=size))
        except Exception:
            pass
    if os.path.isdir(run_dir):
        for name in os.listdir(run_dir):
            if name.endswith('.docx') and name.startswith('cover_letter_job'):
                try:
                    job_id = int(name.split('job')[1].split('.')[0])
                except Exception:
                    continue
                full = os.path.join(run_dir, name)
                try:
                    size = os.path.getsize(full)
                except Exception:
                    size = 0
                out.append(CoverLetterDoc(job_id=job_id, docx_filename=name, size=size))
    return sorted(out, key=lambda x: x.job_id)

@router.get("/runs/{task_id}/coverletters/{filename}")
async def download_cover_letter_doc(task_id: str, filename: str):
    import os
    safe = ''.join(c for c in filename if c.isalnum() or c in ('_','-','.'))
    if '..' in safe:
        raise HTTPException(status_code=400, detail='invalid filename')
    from app.core.config import settings as _settings
    if _settings.supabase_storage_enabled:
        # Redirect to signed/public URL
        bucket = _settings.SUPABASE_STORAGE_BUCKET_DOCS
        key = f"runs/{task_id}/{safe}"
        url = get_public_url(bucket, key) or create_signed_url(bucket, key, 3600)
        if url:
            from fastapi.responses import RedirectResponse as _Redirect
            return _Redirect(url=url, status_code=307)
    run_dir = os.path.abspath(os.path.join(os.getcwd(), 'generated_docs', f'run_{task_id}'))
    path = os.path.join(run_dir, safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail='file not found')
    return FileResponse(path, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', filename=safe)


class ResumeUpload(BaseModel):
    run_id: int
    resume_text: str

@router.post("/runs/{task_id}/resume")
async def upload_resume(task_id: str, payload: ResumeUpload):
    if int(task_id) != payload.run_id:
        raise HTTPException(status_code=400, detail="run_id mismatch")
    # Placeholder: store resume text in run.metadata_json for future personalization
    db = SessionLocal()
    run = db.get(PipelineRun, int(task_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    meta = (run.metadata_json and __import__('json').loads(run.metadata_json)) or {}
    meta['resume_text'] = payload.resume_text[:20000]
    import json as _json
    run.metadata_json = _json.dumps(meta)
    db.add(run)
    db.commit()
    return {"ok": True}


@router.post("/runs/{task_id}/resume/upload")
async def upload_resume_file(task_id: str, file: UploadFile = File(...)):
    run_id = int(task_id)
    db = SessionLocal()
    run = db.get(PipelineRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    # Ensure uploads dir
    base_dir = os.path.abspath(os.path.join(os.getcwd(), 'uploads', 'resumes'))
    os.makedirs(base_dir, exist_ok=True)
    # Sanitize filename
    orig = file.filename or 'resume'
    safe = ''.join(c for c in orig if c.isalnum() or c in ('-', '_', '.')) or 'resume.txt'
    stored_name = f"run{run_id}_{safe}"
    stored_path = os.path.join(base_dir, stored_name)
    # Write file to disk
    with open(stored_path, 'wb') as out:
        shutil.copyfileobj(file.file, out)
    # Hash
    h = hashlib.sha256()
    with open(stored_path, 'rb') as f: h.update(f.read())
    file_hash = h.hexdigest()
    # Extract text
    text = extract_resume_text(stored_path)
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from resume")
    # Mirror to Supabase Storage if configured (store original uploaded resume)
    if settings.supabase_storage_enabled:
        try:
            key = f"runs/{run_id}/uploads/{stored_name}"
            with open(stored_path, 'rb') as fh:
                data = fh.read()
            upload_bytes(settings.SUPABASE_STORAGE_BUCKET_UPLOADS, key, data, content_type=file.content_type or None, upsert=True)
        except Exception:
            pass
    # Persist into metadata_json
    meta = (run.metadata_json and json.loads(run.metadata_json)) or {}
    meta['resume_file'] = {
        'original': orig,
        'stored': stored_name,
        'hash': file_hash,
        'chars': len(text)
    }
    meta['resume_text'] = text[:20000]
    run.metadata_json = json.dumps(meta)
    db.add(run)
    db.commit()
    return {"ok": True, "stored": stored_name, "length": len(text)}


class GenerateRequest(BaseModel):
    limit: int = 5
    force: bool = False  # regenerate even if custom docs already exist
    refresh_placeholders: bool = True  # replace placeholder texts automatically
    all: bool = False  # ignore limit and process all jobs in run

class BulkResumeGenerateRequest(BaseModel):
    all: bool = True  # default: generate for all
    limit: int = 0    # ignored unless all is False
    force: bool = True  # overwrite existing if True

@router.post("/runs/{task_id}/resumes/generate")
async def bulk_generate_resumes(task_id: str, payload: BulkResumeGenerateRequest):
    """Generate (or regenerate) resume_custom for jobs in a run.

    Uses unified resume_service: uploaded resume > sample_resume.txt > placeholder.
    If force=False, existing resume_custom values are left untouched.
    """
    db = SessionLocal()
    try:
        task_int = int(task_id)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="task_id must be an integer")
    run = db.get(PipelineRun, task_int)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    base_q = db.query(ScrapedJob).filter(ScrapedJob.run_id == run.id)
    jobs = base_q.all() if payload.all else base_q.limit(max(payload.limit, 1) if payload.limit else 50).all()
    from app.services.resume_service import generate_resumes_for_jobs
    processed, skipped = generate_resumes_for_jobs(run, jobs, force=payload.force)
    for j in jobs:
        db.add(j)
    db.commit()
    # Write resumes to disk (text + docx) similar to pipeline behavior
    import os
    from coverletter_convertion import convert_cover_letter
    def _project_root() -> str:
        return os.path.abspath(os.getcwd())
    output_dir = os.path.join(_project_root(), 'generated_docs', f'run_{run.id}')
    os.makedirs(output_dir, exist_ok=True)
    written = 0
    for j in jobs:
        if not j.resume_custom:
            continue
        resume_txt_path = os.path.join(output_dir, f"resume_job{j.id}.txt")
        resume_docx_path = os.path.join(output_dir, f"resume_job{j.id}.docx")
        try:
            with open(resume_txt_path, 'w', encoding='utf-8') as f:
                f.write(j.resume_custom)
            try:
                convert_cover_letter(resume_txt_path, resume_docx_path)
            except Exception:
                pass
            written += 1
            # Mirror to Supabase Storage
            if settings.supabase_storage_enabled:
                try:
                    key_txt = f"runs/{task_id}/resume_job{j.id}.txt"
                    key_docx = f"runs/{task_id}/resume_job{j.id}.docx"
                    with open(resume_txt_path, 'rb') as fh:
                        upload_bytes(settings.SUPABASE_STORAGE_BUCKET_DOCS, key_txt, fh.read(), content_type='text/plain', upsert=True)
                    if os.path.exists(resume_docx_path):
                        with open(resume_docx_path, 'rb') as fh:
                            upload_bytes(settings.SUPABASE_STORAGE_BUCKET_DOCS, key_docx, fh.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', upsert=True)
                except Exception:
                    pass
        except Exception:
            continue
    return {"ok": True, "processed": processed, "skipped": skipped, "files_written": written, "total_in_run": base_q.count(), "touched": len(jobs), "force": payload.force}

@router.post("/runs/{task_id}/generate")
async def generate_docs(task_id: str, payload: GenerateRequest):
    db = SessionLocal()
    run = db.get(PipelineRun, int(task_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    import json as _json
    meta = (run.metadata_json and _json.loads(run.metadata_json)) or {}
    resume_text = meta.get('resume_text')
    used_placeholder = False
    if not resume_text:
        resume_text = "PLACEHOLDER RESUME TEXT - upload a real resume for better tailoring."  # fallback
        used_placeholder = True
    base_q = db.query(ScrapedJob).filter(ScrapedJob.run_id == run.id)
    total_jobs = base_q.count()
    # Always operate on either all jobs (if flag) or limited subset, but we'll regenerate regardless of existing docs.
    if payload.all:
        jobs = base_q.all()
    else:
        jobs = base_q.limit(payload.limit).all()
    generated = 0
    regenerated = 0
    openai_key = settings.OPENAI_API_KEY or ''
    openai_timeout = 8  # seconds per job for analysis/generation helpers

    def call_with_timeout(func, *args, timeout: int, default=None, **kwargs):
        if not openai_key:
            return default
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(func, *args, **kwargs)
                return fut.result(timeout=timeout)
        except Exception:
            return default
    for j in jobs:
        try:
            # Always regenerate cover letter & resume customization (ignore previous state)
            already_had = bool(j.cover_letter or j.resume_custom)

            # Handle missing descriptions with a synthetic JD
            raw_desc = j.description or ''
            jd_plain = clean_html(raw_desc) if raw_desc else f"{j.title} role at {j.company or 'the company'}"
            analysis = {}
            if openai_key:
                analysis = call_with_timeout(
                    analyze_job_match_with_openai,
                    resume_text,
                    jd_plain,
                    j.title,
                    j.company or '',
                    str(j.id),
                    openai_key,
                    timeout=openai_timeout,
                    default={},
                ) or {}
            optimized_resume = resume_text
            if openai_key and analysis:
                optimized_resume = call_with_timeout(
                    generate_ats_optimized_resume_with_analysis,
                    resume_text,
                    analysis,
                    openai_key,
                    timeout=openai_timeout,
                    default=resume_text,
                ) or resume_text
            cover_letter = None
            if openai_key:
                cover_letter = call_with_timeout(
                    generate_optimized_cover_letter,
                    j.title,
                    j.company or '',
                    j.recruiter_name or 'Hiring Manager',
                    jd_plain,
                    resume_text,
                    openai_key,
                    timeout=openai_timeout,
                    default=None,
                )
            if not cover_letter:
                # Deterministic fallback when OpenAI key missing or timeout
                snippet = jd_plain[:260].rstrip()
                cover_letter = (
                    f"Dear {j.recruiter_name or 'Hiring Manager'},\n\n"
                    f"I'm writing to express strong interest in the {j.title} role at {j.company or 'your company'}. "
                    f"My background aligns with the position requirements and I'd welcome the opportunity to contribute.\n\n"
                    f"Role Focus (excerpt): {snippet}\n\n"
                    "Thank you for your time and consideration.\n\nBest Regards,\nCandidate"
                )
            j.cover_letter = cover_letter[:20000]
            j.resume_custom = (optimized_resume or '')[:20000]
            if already_had:
                regenerated += 1
            else:
                generated += 1
        except Exception:  # noqa: BLE001
            continue
    db.commit()
    return {
        "ok": True,
        "generated": generated,
        "regenerated": regenerated,
        "placeholder": used_placeholder,
        "processed": len(jobs),
        "total_jobs": total_jobs,
    }


class SendRequest(BaseModel):
    max_emails: int = 5
    dry_run: bool = True
    force: bool = False  # future use: send even if missing recruiter_email (skips now)

@router.post("/runs/{task_id}/send")
async def send_emails(task_id: str, payload: SendRequest):
    if not settings.SENDGRID_API_KEY:
        raise HTTPException(status_code=400, detail="SENDGRID_API_KEY not configured")
    db = SessionLocal()
    run = db.get(PipelineRun, int(task_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    # Load optional template (only first entry used) for subject/body skeleton; ignore static 'to'.
    template_subject = None
    template_html = None
    tmpl_path = os.path.join(os.getcwd(), 'email_template.json')
    if os.path.exists(tmpl_path):
        try:
            with open(tmpl_path, 'r', encoding='utf-8') as f:
                _tmpl_data = json.load(f)
            if isinstance(_tmpl_data, list) and _tmpl_data:
                first = _tmpl_data[0]
                if isinstance(first, dict):
                    template_subject = (first.get('subject') or None)
                    template_html = first.get('html') or first.get('body') or None
        except Exception:  # noqa: BLE001
            pass  # Non-fatal

    # Fetch all jobs for the run to aggregate recruiter contacts.
    jobs = db.query(ScrapedJob).filter(ScrapedJob.run_id == run.id).all()
    total_jobs = len(jobs)
    sent = 0  # successful sends (or dry-run counted as success)
    failures = 0
    skipped = 0  # jobs with zero usable emails
    events: list[dict] = []
    unique_recipients_processed = 0
    # Cap across ALL individual emails (not jobs)
    max_total_emails = max(0, payload.max_emails)

    import re, json as _json
    for j in jobs:
        if max_total_emails and sent + failures >= max_total_emails:
            break  # reached overall limit
        # Build set of email addresses: primary recruiter_email + recruiter_contacts entries
        emails_set: list[str] = []
        if j.recruiter_email and j.recruiter_email not in emails_set:
            emails_set.append(j.recruiter_email)
        # Extract recruiter_contacts from per-job metadata_json (NOT run metadata)
        job_meta = None
        try:
            job_meta = j.metadata_json and _json.loads(j.metadata_json)
        except Exception:  # noqa: BLE001
            job_meta = None
        if isinstance(job_meta, dict) and isinstance(job_meta.get('recruiter_contacts'), list):
            for c in job_meta.get('recruiter_contacts'):
                if isinstance(c, dict):
                    em = (c.get('email') or '').strip()
                    if em and em not in emails_set:
                        emails_set.append(em)
        if not emails_set:
            skipped += 1
            continue
        # For each email send separately (respecting global max)
        for em in emails_set:
            if max_total_emails and sent + failures >= max_total_emails:
                break
            try:
                # Build subject/body
                subject = template_subject or f"Application: {j.title} - {j.company or ''}"[:120]
                # Use existing personalized cover letter else template_html (stripped to text) else fallback.
                body_plain = j.cover_letter or None
                if not body_plain and template_html:
                    # crude html -> text
                    body_plain = re.sub('<[^<]+?>', '', template_html).strip() or template_html
                if not body_plain:
                    body_plain = f"Dear Recruiter,\n\nI'm interested in the {j.title} role at {j.company or 'your company'}.\nBest,\nCandidate"
                resume_part = (j.resume_custom or '')[:5000]
                send_email_via_sendgrid(
                    settings.SENDGRID_API_KEY,
                    em,
                    subject,
                    body_plain,
                    resume_part,
                    dry_run=payload.dry_run,
                )
                status = 'sent' if not payload.dry_run else 'dry-run'
                events.append({
                    'job_id': j.id,
                    'email': em,
                    'subject': subject,
                    'dry_run': payload.dry_run,
                    'status': status,
                })
                _record_tracked_email(em, subject, status)
                sent += 1 if status == 'sent' or status == 'dry-run' else 0
                unique_recipients_processed += 1
            except Exception as e:  # noqa: BLE001
                failures += 1
                events.append({
                    'job_id': j.id,
                    'email': em,
                    'subject': subject if 'subject' in locals() else None,
                    'dry_run': payload.dry_run,
                    'status': 'error',
                    'error': str(e)[:160],
                })
                _record_tracked_email(em, subject if 'subject' in locals() else 'unknown', 'error')

    # Update run counts (count emails, not jobs)
    counts = run.counts or {}
    counts['emails'] = (counts.get('emails') or 0) + sent
    run.counts = counts
    # Append events to run metadata log
    run_meta = (run.metadata_json and _json.loads(run.metadata_json)) or {}
    run_log = run_meta.get('email_events') or []
    run_log.extend(events)
    run_meta['email_events'] = run_log[-200:]
    run.metadata_json = _json.dumps(run_meta)
    db.add(run)
    db.commit()
    return {
        "ok": True,
        "sent": sent,
        "recipients": unique_recipients_processed,
        "dry_run": payload.dry_run,
        "failures": failures,
        "skipped": skipped,
        "candidates": total_jobs,
        "template_used": bool(template_subject or template_html),
    }


class EmailEvent(BaseModel):
    job_id: int
    email: str | None
    subject: str | None
    dry_run: bool | None


@router.get("/runs/{task_id}/emails", response_model=List[EmailEvent])
async def list_email_events(task_id: str):
    db = SessionLocal()
    run = db.get(PipelineRun, int(task_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    import json as _json
    meta = (run.metadata_json and _json.loads(run.metadata_json)) or {}
    return meta.get('email_events') or []


# New: list recent runs
class RunSummary(BaseModel):
    id: int
    query: str
    status: str
    stage: str
    jobs: int


@router.get("/runs", response_model=List[RunSummary])
async def list_runs(limit: int = 20):
    db = SessionLocal()
    runs = db.query(PipelineRun).order_by(PipelineRun.id.desc()).limit(limit).all()
    out = []
    for r in runs:
        out.append(RunSummary(
            id=r.id,
            query=r.query,
            status=r.status.value,
            stage=r.stage,
            jobs=(r.counts or {}).get("jobs", 0)
        ))
    return out

# ---- Email Tracking (global) ----
class TrackedMessage(BaseModel):
    id: str
    to_email: str
    subject: str
    created_at: str
    events: int
    provider_msgid: str | None = None

class TrackedEvent(BaseModel):
    id: int
    msg_id: str
    event: str
    email: str | None
    url: str | None
    reason: str | None
    timestamp: int

@router.get("/emails/tracked", response_model=List[TrackedMessage])
async def list_tracked_emails(limit: int = 100):
    # Use writable conn to auto-create schema if missing and avoid 500s with legacy DBs
    conn = _get_events_conn_writable()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        try:
            rows = cur.execute(
                "SELECT id,to_email,subject,created_at,provider_msgid FROM messages ORDER BY datetime(created_at) DESC LIMIT ?",
                (limit,),
            ).fetchall()
        except Exception:
            # If messages table/columns missing, treat as empty
            return []

        out: list[TrackedMessage] = []
        for r in rows:
            try:
                cnt = cur.execute("SELECT COUNT(*) FROM events WHERE msg_id=?", (r['id'],)).fetchone()[0]
            except Exception:
                cnt = 0
            # created_at may be NULL for legacy rows; coerce to ISO string
            created = r['created_at'] if r['created_at'] is not None else time.strftime('%Y-%m-%d %H:%M:%S')
            out.append(TrackedMessage(
                id=r['id'],
                to_email=r['to_email'],
                subject=r['subject'],
                created_at=created,
                events=cnt,
                provider_msgid=r['provider_msgid'] or None
            ))
        return out
    finally:
        try:
            conn.close()
        except Exception:
            pass

# ---- Resume export helpers ----
@router.get("/runs/{task_id}/resumes/export")
async def export_resumes(task_id: str):
    """Ensure resume files exist on disk for a run and list them.

    Returns JSON with written file names (txt + docx) relative to run folder.
    """
    db = SessionLocal()
    try:
        run_id = int(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="task_id must be an integer")
    run = db.get(PipelineRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    jobs = db.query(ScrapedJob).filter(ScrapedJob.run_id == run.id).all()
    from app.services.resume_export import ensure_resume_files
    written = ensure_resume_files(run, jobs)
    # Return relative names under generated_docs/run_<id>
    import os
    rel_root = os.path.join("generated_docs", f"run_{run.id}")
    rel_files = []
    for p in written:
        try:
            rel_files.append(os.path.relpath(p, start=os.getcwd()))
        except Exception:
            rel_files.append(p)
    return {"ok": True, "files": rel_files, "count": len(rel_files), "root": rel_root}

@router.get("/runs/{task_id}/resumes/archive.zip")
async def download_resumes_zip(task_id: str):
    """Build (or rebuild) a zip of all resume files for the run and return as download."""
    db = SessionLocal()
    try:
        run_id = int(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="task_id must be an integer")
    run = db.get(PipelineRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    # Ensure files exist first
    jobs = db.query(ScrapedJob).filter(ScrapedJob.run_id == run.id).all()
    from app.services.resume_export import ensure_resume_files, create_resume_zip
    ensure_resume_files(run, jobs)
    try:
        zip_path = create_resume_zip(run)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No resume files for run")
    filename = os.path.basename(zip_path)
    return FileResponse(path=zip_path, filename=filename, media_type='application/zip')

@router.get("/emails/tracked/{msg_id}", response_model=List[TrackedEvent])
async def list_tracked_events(msg_id: str):
    # Use writable conn to ensure schema exists and gracefully handle legacy DBs
    conn = _get_events_conn_writable()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        try:
            rows = cur.execute(
                "SELECT id,msg_id,event,email,url,reason,timestamp FROM events WHERE msg_id=? ORDER BY timestamp",
                (msg_id,),
            ).fetchall()
        except Exception:
            return []
        return [TrackedEvent(
            id=r['id'],
            msg_id=r['msg_id'],
            event=r['event'],
            email=r['email'],
            url=r['url'],
            reason=r['reason'],
            timestamp=r['timestamp'],
        ) for r in rows]
    finally:
        try:
            conn.close()
        except Exception:
            pass
