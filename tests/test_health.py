import os
from fastapi.testclient import TestClient
from app.main import app

def test_health_endpoint():
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    data = r.json()
    # Minimum keys (service or status depending on implementation variant)
    assert 'status' in data or 'ok' in data
