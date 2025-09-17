import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_healthz(client: TestClient, monkeypatch):
    # Monkeypatch PipelineService.check_health to avoid network/DB
    from app.services import pipeline as svc

    def _fake_health():
        return {
            "status": "healthy",
            "version": "1.0.0",
            "database_connection": True,
            "api_connections": {"apify": False, "apollo": False, "sendgrid": False, "openai": False},
        }

    monkeypatch.setattr(svc.PipelineService, "check_health", staticmethod(_fake_health))
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert "api_connections" in body


def test_pipeline_scrape_enrich_match_send(client: TestClient, monkeypatch, tmp_path):
    # Monkeypatch service methods to return canned responses
    from app.services import pipeline as svc

    def _scrape(**kwargs):
        return {"jobs_scraped": 3, "output_path": str(tmp_path / "jobs.json"), "message": "ok"}

    def _enrich(db):
        return {"enriched_count": 5, "message": "ok"}

    def _match(resume_path, database_path, threshold):
        return {"matches_found": 1, "jobs": [], "message": "ok"}

    def _send(job_ids, resume_path, database_path, dry_run):
        return {"emails_sent": 0, "jobs_processed": 1, "message": "ok"}

    monkeypatch.setattr(svc.PipelineService, "scrape_jobs", staticmethod(lambda **kw: _scrape(**kw)))
    monkeypatch.setattr(svc.PipelineService, "enrich_jobs", staticmethod(lambda db: _enrich(db)))
    monkeypatch.setattr(
        svc.PipelineService, "match_jobs", staticmethod(lambda resume_path, database_path, threshold: _match(resume_path, database_path, threshold))
    )
    monkeypatch.setattr(
        svc.PipelineService, "send_applications", staticmethod(lambda job_ids, resume_path, database_path, dry_run: _send(job_ids, resume_path, database_path, dry_run))
    )

    # scrape
    r1 = client.post(
        "/pipeline/scrape",
        json={"actor_id": "actor", "title": "Engineer", "rows": 5, "location": "US"},
    )
    assert r1.status_code == 200
    assert r1.json()["jobs_scraped"] == 3

    # enrich
    r2 = client.post("/pipeline/enrich", json={"database_path": str(tmp_path / "jobs.db")})
    assert r2.status_code == 200
    assert r2.json()["enriched_count"] == 5

    # match
    r3 = client.post(
        "/pipeline/match",
        json={"resume_path": str(tmp_path / "resume.txt"), "database_path": str(tmp_path / "jobs.db"), "threshold": 30.0},
    )
    assert r3.status_code == 200
    assert r3.json()["matches_found"] == 1

    # send
    r4 = client.post(
        "/pipeline/send",
        json={
            "job_ids": ["1"],
            "resume_path": str(tmp_path / "resume.txt"),
            "database_path": str(tmp_path / "jobs.db"),
            "dry_run": True,
        },
    )
    assert r4.status_code == 200
    assert r4.json()["jobs_processed"] == 1