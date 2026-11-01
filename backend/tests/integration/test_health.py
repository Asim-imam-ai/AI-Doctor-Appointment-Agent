"""FastAPI runtime and OpenAPI surface integration checks."""

from fastapi.testclient import TestClient

from app.main import app


def test_app_lifespan_and_versioned_health():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "doctor-appointment-agent",
    }


def test_health_is_public_and_other_patient_routes_require_auth():
    client = TestClient(app)
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/appointments").status_code == 401


def test_openapi_contains_required_v1_route_groups():
    paths = app.openapi()["paths"]
    for path in (
        "/api/v1/health",
        "/api/v1/chat",
        "/api/v1/doctors/search",
        "/api/v1/availability/search",
        "/api/v1/appointments",
        "/api/v1/approvals/{proposal_id}",
        "/api/v1/conversations",
        "/api/v1/knowledge/search",
    ):
        assert path in paths


def test_unversioned_health_is_not_published():
    assert TestClient(app).get("/health").status_code == 404
