from __future__ import annotations
import logging
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
import os

def _project_root() -> str:
    """Return absolute project root (directory containing this file's grandparent)."""
    return os.path.abspath(os.getcwd())

from app.models import PipelineRun, Stage, ScrapedJob
from app.services.scrape_indeed import scrape_indeed
from job_application_pipeline import run_apify_job
from app.core.config import settings
from app.services.apollo_enrichment import find_recruiter_contact


class PipelineContext:
    def __init__(self, db: Session, run: PipelineRun):
        self.db = db
        self.run = run
        self.errors: List[str] = []

    def save(self):
        self.db.add(self.run)
        self.db.commit()
        self.db.refresh(self.run)

    def set_counts(self, **delta):
        counts = self.run.counts or {}
        counts.update(delta)
        self.run.counts = counts
        self.save()

    def set_stage(self, stage: Stage):
        self.run.set_stage(stage)
        self.save()


async def run_pipeline(run_id: int, query: str, locations: list[str] | None, sources: list[str] | None):
    from app.core.database import SessionLocal  # avoid circular import
    db = SessionLocal()
    try:
        run: PipelineRun | None = db.get(PipelineRun, run_id)
        if not run:
            return
        run.mark_running()
        run.set_stage(Stage.DISCOVER)
        db.commit()
        db.refresh(run)
        ctx = PipelineContext(db, run)

        jobs_total = 0

        # 1. Indeed scrape (best effort)
        if not sources or "indeed" in sources:
            for loc in (locations or [None]):
                try:
                    indeed_jobs = await scrape_indeed(query=query, location=loc, pages=2)
                except Exception as e:  # noqa: BLE001
                    logging.warning("Indeed scrape failed for %s: %s", loc, e)
                    indeed_jobs = []
                inserted = 0
                for j in indeed_jobs:
                    title = j.get("title")
                    if not title:
                        continue
                    hashv = ScrapedJob.compute_hash("indeed", title, j.get("company"), j.get("location"))
                    exists = db.execute(select(ScrapedJob.id).where(
                        ScrapedJob.hash == hashv,
                        ScrapedJob.run_id == run.id
                    )).scalar()
                    if exists:
                        continue
                    db.add(ScrapedJob(
                        run_id=run.id,
                        source="indeed",
                        job_id_ext=None,
                        title=title,
                        company=j.get("company"),
                        location=j.get("location"),
                        url=j.get("url"),
                        description=j.get("description"),
                        hash=hashv,
                    ))
                    inserted += 1
                if inserted:
                    db.commit()
                    jobs_total += inserted

        # 2. Apify actor (always attempt if token present) to enrich/augment
        if settings.apify_token:
            try:
                actor_id = getattr(settings, 'DEFAULT_ACTOR_ID', 'BHzefUZlZRKWxkTck')
                run_input = {
                    "title": query,
                    "location": (locations or [None])[0] or "United States",
                    "rows": 40,
                    "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
                }
                apify_jobs = run_apify_job(settings.apify_token, actor_id, run_input) or []
                inserted = 0
                for j in apify_jobs[:80]:
                    title = j.get('title') or j.get('jobTitle')
                    if not title:
                        continue
                    company = j.get('companyName') or j.get('company')
                    location = j.get('location') or j.get('jobLocation')
                    url = j.get('jobUrl') or j.get('url')
                    hashv = ScrapedJob.compute_hash('apify', title, company, location)
                    exists = db.execute(select(ScrapedJob.id).where(
                        ScrapedJob.hash == hashv,
                        ScrapedJob.run_id == run.id
                    )).scalar()
                    if exists:
                        continue
                    db.add(ScrapedJob(
                        run_id=run.id,
                        source='apify',
                        job_id_ext=str(j.get('id')) if j.get('id') else None,
                        title=title,
                        company=company,
                        location=location,
                        url=url,
                        description=j.get('description') or j.get('descriptionHtml') or j.get('descriptionHTML'),
                        hash=hashv,
                    ))
                    inserted += 1
                if inserted:
                    db.commit()
                    jobs_total += inserted
                logging.info("Apify actor inserted %s jobs (total now %s) for run %s", inserted, jobs_total, run.id)
            except Exception as e:  # noqa: BLE001
                logging.warning("Apify scrape failed for run %s: %s", run.id, e)
        else:
            logging.info("Apify token missing; skipping Apify scrape for run %s", run.id)

        # Update counts/stages
        ctx.set_counts(jobs=jobs_total, enriched=0, emails=0)
        ctx.set_stage(Stage.PARSE)

        # Seed demo jobs automatically if nothing found (removed settings.DEMO_SEED_JOBS dependency for reliability)
        if jobs_total == 0:
            demo_samples = [
                (f"{query.title()} Engineer", "Acme Corp", "Remote", "https://example.com/job/acme"),
                (f"Senior {query.title()} Developer", "Globex", "USA", "https://example.com/job/globex"),
                (f"{query.title()} Specialist", "Initech", "Europe", "https://example.com/job/initech"),
            ]
            inserted_demo = 0
            for title, company, location, url in demo_samples:
                hashv = ScrapedJob.compute_hash('demo', title, company, location)
                db.add(ScrapedJob(
                    run_id=run.id,
                    source='demo',
                    job_id_ext=None,
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    description=f"Autogenerated demo job for keyword '{query}'. Replace with real scrape.",
                    hash=hashv,
                ))
                inserted_demo += 1
            db.commit()
            jobs_total += inserted_demo
            ctx.set_counts(jobs=jobs_total, enriched=0, emails=0)

        # ENRICH: attempt Apollo enrichment only; do NOT create synthetic recruiter placeholders
        ctx.set_stage(Stage.ENRICH)
        enriched = 0
        if jobs_total:
            jobs = db.query(ScrapedJob).filter(ScrapedJob.run_id == run.id).all()
            for j in jobs:
                if j.recruiter_email:  # already have unlocked email
                    continue
                contact = None
                if not (settings.APOLLO_API_KEY and j.company and j.title):
                    logging.info("Enrichment skip job=%s missing key/company/title", j.id)
                else:
                    try:
                        contact = find_recruiter_contact(j.company, j.title)
                    except Exception as e:  # noqa: BLE001
                        logging.warning("Apollo enrichment exception job=%s: %s", j.id, e)
                        contact = None
                if contact:
                    # Always keep recruiter_name if we found a contact, even if email locked
                    prev_name = j.recruiter_name
                    j.recruiter_name = contact.get("name") or prev_name or None
                    email_val = contact.get("email") or None
                    if email_val:
                        j.recruiter_email = email_val
                        logging.info("Enriched job=%s name=%s email=SET", j.id, j.recruiter_name)
                    else:
                        # Preserve name even without email unlock
                        logging.info("Enriched job=%s name=%s email=LOCKED_OR_EMPTY", j.id, j.recruiter_name)
                else:
                    logging.info("Enrichment no-contact job=%s company=%s title=%s", j.id, j.company, j.title)
                j.enriched_at = datetime.utcnow()
                enriched += 1
            db.commit()
        ctx.set_counts(jobs=jobs_total, enriched=enriched, emails=0)

        # GENERATE: cover letter & resume_custom (using uploaded or sample resume if available)
        ctx.set_stage(Stage.GENERATE)
        generated = 0
        from app.services.resume_service import load_base_resume_text, tailor_resume_for_job
        base_resume_text = load_base_resume_text(run)
        if jobs_total:
            from coverletter_convertion import convert_cover_letter
            import os
            jobs = db.query(ScrapedJob).filter(ScrapedJob.run_id == run.id).all()
            total_jobs = len(jobs)
            output_dir = os.path.join(_project_root(), 'generated_docs', f'run_{run.id}')
            os.makedirs(output_dir, exist_ok=True)
            processed = 0
            for j in jobs:
                processed += 1
                try:
                    # Always regenerate (overwrite) cover letter & resume customization
                    desc_snippet = (j.description or '')[:280]
                    j.cover_letter = f"Cover Letter for {j.title} at {j.company or 'Company'}\n\n{desc_snippet}\n\nThis is an auto-generated cover letter placeholder."
                    j.resume_custom = tailor_resume_for_job(base_resume_text, j)
                    j.generated_at = datetime.utcnow()
                    generated += 1
                    db.add(j)
                    db.commit()
                    # Write text file & convert to docx for UI download
                    base_name = f"cover_letter_job{j.id}"
                    txt_path = os.path.join(output_dir, base_name + '.txt')
                    docx_path = os.path.join(output_dir, base_name + '.docx')
                    resume_txt_path = os.path.join(output_dir, f"resume_job{j.id}.txt")
                    resume_docx_path = os.path.join(output_dir, f"resume_job{j.id}.docx")
                    try:
                        with open(txt_path, 'w', encoding='utf-8') as f:
                            f.write(j.cover_letter or '')
                        convert_cover_letter(txt_path, docx_path)
                        logging.info("[PIPELINE] Wrote cover letter files for job %s -> %s", j.id, base_name)
                        # Mirror to Supabase Storage
                        from app.core.config import settings as _settings
                        if _settings.supabase_storage_enabled:
                            try:
                                from app.services.supabase_storage import upload_bytes
                                key_txt = f"runs/{run.id}/{base_name}.txt"
                                key_docx = f"runs/{run.id}/{base_name}.docx"
                                with open(txt_path, 'rb') as fh:
                                    upload_bytes(_settings.SUPABASE_STORAGE_BUCKET_DOCS, key_txt, fh.read(), content_type='text/plain', upsert=True)
                                if os.path.exists(docx_path):
                                    with open(docx_path, 'rb') as fh:
                                        upload_bytes(_settings.SUPABASE_STORAGE_BUCKET_DOCS, key_docx, fh.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', upsert=True)
                            except Exception:
                                pass
                        # Write resume txt
                        if j.resume_custom:
                            with open(resume_txt_path, 'w', encoding='utf-8') as f:
                                f.write(j.resume_custom)
                            # Re-use converter if it accepts arbitrary text (create temp file)
                            try:
                                # Write temp wrapper file for conversion
                                tmp_resume_source = resume_txt_path  # already plain text
                                convert_cover_letter(tmp_resume_source, resume_docx_path)
                            except Exception:
                                pass
                            logging.info("[PIPELINE] Wrote resume files for job %s", j.id)
                            # Mirror resume files as well
                            if _settings.supabase_storage_enabled:
                                try:
                                    from app.services.supabase_storage import upload_bytes
                                    key_txt = f"runs/{run.id}/resume_job{j.id}.txt"
                                    key_docx = f"runs/{run.id}/resume_job{j.id}.docx"
                                    with open(resume_txt_path, 'rb') as fh:
                                        upload_bytes(_settings.SUPABASE_STORAGE_BUCKET_DOCS, key_txt, fh.read(), content_type='text/plain', upsert=True)
                                    if os.path.exists(resume_docx_path):
                                        with open(resume_docx_path, 'rb') as fh:
                                            upload_bytes(_settings.SUPABASE_STORAGE_BUCKET_DOCS, key_docx, fh.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', upsert=True)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                except Exception:
                    continue
                # Update counts after each iteration so UI can poll and display progress
                ctx.set_counts(jobs=jobs_total, enriched=enriched, emails=0, generated=generated, generation_progress={"processed": processed, "total": total_jobs})
            db.commit()
        # Do not change emails count yet (future stage)
        ctx.set_counts(jobs=jobs_total, enriched=enriched, emails=0)
        ctx.set_stage(Stage.EMAIL)
        run.mark_done()
        db.commit()
    except Exception as e:  # noqa: BLE001
        try:
            run.mark_error(str(e))  # type: ignore[arg-type]
            db.commit()
        except Exception:  # noqa: BLE001
            pass
    finally:
        db.close()

__all__ = ["run_pipeline"]
