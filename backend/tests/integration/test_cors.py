from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

import app.api.dependencies.auth as auth
import app.api.v1.patients as patients
from app.main import app


def test_patient_preflight_allows_local_frontend_and_auth_headers():
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/patients/me",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:5173"
        )
        allowed = response.headers["access-control-allow-headers"].lower()
        assert "authorization" in allowed and "content-type" in allowed
        unauthorized = client.get(
            "/api/v1/patients/me", headers={"Origin": "http://localhost:5173"}
        )
        assert unauthorized.status_code == 401
        assert (
            unauthorized.headers["access-control-allow-origin"]
            == "http://localhost:5173"
        )


def test_patient_preflight_rejects_unknown_origins():
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/patients/me",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers


def test_patient_profile_uses_verified_bearer_and_reports_missing_profile(monkeypatch):
    user_id, patient_id = uuid4(), uuid4()
    user = SimpleNamespace(id=user_id, email="test@example.com", app_metadata={})
    seen = []

    def verify(token):
        seen.append(token)
        return user, {"sub": str(user_id)}

    profile = SimpleNamespace(
        id=patient_id, name="Test Patient", email=user.email, phone=None, timezone="UTC"
    )
    service = SimpleNamespace(
        get_by_external_id=lambda _: profile, get_patient=lambda _: profile
    )
    monkeypatch.setattr(auth, "verify_access_token", verify)
    monkeypatch.setattr(auth, "get_patient_service", lambda: service)
    monkeypatch.setattr(patients, "get_patient_service", lambda: service)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/patients/me", headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Test Patient"
        assert seen == ["test-token"]
        service.get_by_external_id = lambda _: None
        service.get_patient = lambda _: None
        assert (
            client.get(
                "/api/v1/patients/me", headers={"Authorization": "Bearer test-token"}
            ).status_code
            == 403
        )
