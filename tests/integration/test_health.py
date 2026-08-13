"""Integration test for health check endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_v1_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "doctor-appointment-agent"
    # Ensure no internal secrets exposed
    assert "OPENAI_API_KEY" not in data
    assert "SUPABASE_KEY" not in data


def test_root_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "doctor-appointment-agent"
