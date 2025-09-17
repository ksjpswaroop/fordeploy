from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from app.core.database import SessionLocal
from app.models.run import PipelineRun, RunStatus
from app.core.celery_app import run_pipeline
import asyncio
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])

class RunCreateRequest(BaseModel):
    query: str = Field(..., max_length=500)
    locations: List[str] = []
    sources: List[str] = ["linkedin"]
    auto_send: bool = False

class RunCreateResponse(BaseModel):
    task_id: str
    run_id: int

class RunStatusResponse(BaseModel):
    id: int
    status: str
    counts: dict
    error: Optional[str] = None

@router.post("/start", response_model=RunCreateResponse)
def start_run(payload: RunCreateRequest):
    db = SessionLocal()
    try:
        run = PipelineRun(query=payload.query, locations=payload.locations, sources=payload.sources, counts={"jobs":0,"enriched":0,"emails":0})
        db.add(run)
        db.commit()
        db.refresh(run)
        try:
            async_result = run_pipeline.delay(run.id)  # type: ignore[attr-defined]
            run.task_id = async_result.id
            db.add(run)
            db.commit()
            return RunCreateResponse(task_id=run.task_id, run_id=run.id)
        except Exception as e:  # noqa: BLE001
            # Fallback: run synchronously (non-blocking) using thread/async task for dev when broker absent.
            logger.warning(f"Celery dispatch failed, falling back to local task execution: {e}")
            run.task_id = f"local-{run.id}"
            db.add(run); db.commit()
            # Inline lightweight simulation using the celery task function directly in a thread to avoid blocking.
            def _local_exec(rid: int):
                try:
                    run_pipeline(rid)  # call the celery task function directly
                except Exception as ex:  # noqa: BLE001
                    logger.error(f"Local run_pipeline execution error: {ex}")
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                loop.create_task(asyncio.to_thread(_local_exec, run.id))
            else:
                # If no running loop (unlikely in FastAPI), start thread directly
                import threading
                threading.Thread(target=_local_exec, args=(run.id,), daemon=True).start()
            return RunCreateResponse(task_id=run.task_id, run_id=run.id)
    finally:
        db.close()

@router.get("/{run_id}", response_model=RunStatusResponse)
def get_run(run_id: int):
    db = SessionLocal()
    try:
        run = db.query(PipelineRun).get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return RunStatusResponse(id=run.id, status=run.status.value, counts=run.counts or {}, error=run.error)
    finally:
        db.close()
