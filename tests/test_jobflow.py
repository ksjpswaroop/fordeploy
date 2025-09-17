import time
from fastapi.testclient import TestClient
from app.main import app

def test_start_run_and_list_jobs():
    client = TestClient(app)
    # Start a run
    resp = client.post('/api/jobs/run', json={'query':'python developer'})
    assert resp.status_code == 200
    run_id = resp.json()['task_id']
    # Poll jobs (pipeline runs async)
    jobs = []
    for _ in range(6):
        time.sleep(0.5)
        jr = client.get(f'/api/runs/{run_id}/jobs')
        assert jr.status_code == 200
        jobs = jr.json()
        if jobs:
            break
    # We allow empty (scrape may fail without external deps); just assert shape when present
    if jobs:
        first = jobs[0]
        assert 'id' in first and 'title' in first
