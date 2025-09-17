import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_scrape_invalid_rows_validation():
    # rows must be >=1
    payload = {
        "actor_id": "actor",
        "title": "",
        "location": "US",
        "company_name": [],
        "company_id": [],
        "rows": 0,
    }
    resp = client.post("/pipeline/scrape", json=payload)
    assert resp.status_code == 422


def test_match_invalid_threshold_validation():
    # threshold must be between 0 and 100
    payload = {
        "resume_path": "resume.pdf",
        "database_path": "jobs.db",
        "threshold": 101.0,
    }
    resp = client.post("/pipeline/match", json=payload)
    assert resp.status_code == 422


def test_send_requires_job_ids_and_resume():
    # missing required fields triggers validation error
    resp = client.post("/pipeline/send", json={"job_ids": [], "resume_path": ""})
    assert resp.status_code == 422


def test_enrich_service_error_returns_500(monkeypatch):
    # Simulate service raising an exception
    from app.services import pipeline as svc

    def _boom(_db_path: str):
        raise RuntimeError("enrich failed")

    monkeypatch.setattr(svc.PipelineService, "enrich_jobs", staticmethod(_boom))

    resp = client.post("/pipeline/enrich", json={"database_path": "jobs.db"})
    assert resp.status_code == 500
    body = resp.json()
    assert "Error enriching jobs" in body["detail"]
