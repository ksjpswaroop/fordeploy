import json
from datetime import datetime

from app.models.pipeline import (
    PipelineRequest,
    PipelineRun,
    PipelineStatus,
    PipelineStatusResponse,
)


def test_pipeline_request_defaults_and_validation():
    req = PipelineRequest()
    assert req.actor_id == "BHzefUZlZRKWxkTck"
    assert req.title == ""
    assert req.location == "United States"
    assert isinstance(req.company_name, list) and req.company_name == []
    assert isinstance(req.company_id, list) and req.company_id == []
    assert req.rows == 50
    assert req.database == "jobs.db"
    assert req.threshold == 30.0
    assert req.dry_run is False


def test_pipeline_run_defaults_and_json_encoding():
    req = PipelineRequest(title="Data Engineer")
    run = PipelineRun(request=req)
    # run_id generated, status pending
    assert isinstance(run.run_id, str) and len(run.run_id) > 0
    assert run.status == PipelineStatus.PENDING
    assert isinstance(run.start_time, datetime)
    # JSON encoding should convert datetimes
    dumped = run.model_dump_json()
    payload = json.loads(dumped)
    assert "start_time" in payload and isinstance(payload["start_time"], str)


def test_pipeline_status_response_defaults_and_serialization():
    now = datetime.utcnow()
    resp = PipelineStatusResponse(
        run_id="abc123",
        status=PipelineStatus.SCRAPING,
        start_time=now,
        end_time=None,
        jobs_scraped=10,
        jobs_matched=2,
        emails_sent=1,
        error=None,
    )
    assert resp.progress_percent == 0
    dumped = resp.model_dump()
    assert dumped["run_id"] == "abc123"
    assert dumped["status"] == PipelineStatus.SCRAPING