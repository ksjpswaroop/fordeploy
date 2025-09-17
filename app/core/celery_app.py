from celery import Celery
import os
from app.core.config import settings

celery_app = Celery(
    "pipeline",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_routes={
        "tasks.run_pipeline": {"queue": "pipeline"},
    },
    task_track_started=True,
    result_expires=3600,
)

@celery_app.task(bind=True)
def run_pipeline(self, run_id: int):
    """Background pipeline task stub: update counts progressively.
    Replace stubs with real scraping/enrichment/email logic.
    """
    from app.core.database import SessionLocal
    from app.models.run import PipelineRun, RunStatus
    from time import sleep
    db = SessionLocal()
    try:
        run = db.query(PipelineRun).get(run_id)
        if not run:
            return {"error": "run not found"}
        run.mark_running()
        db.add(run)
        db.commit()
        counts = {"jobs": 0, "enriched": 0, "emails": 0}
        stages = ["scrape", "enrich", "generate", "send"]
        for stage in stages:
            sleep(0.5)
            if stage == "scrape":
                counts["jobs"] = 10
            elif stage == "enrich":
                counts["enriched"] = 7
            elif stage == "generate":
                counts["emails"] = 0
            elif stage == "send":
                counts["emails"] = 5
            run.counts = counts
            db.add(run)
            db.commit()
        run.mark_done()
        db.add(run)
        db.commit()
        return {"status": run.status, "counts": run.counts}
    except Exception as e:
        db.rollback()
        try:
            run = db.query(PipelineRun).get(run_id)
            if run:
                run.mark_error(str(e))
                db.add(run)
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
