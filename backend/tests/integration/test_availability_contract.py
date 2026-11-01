import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.schemas.availability_agent import (
    AvailabilitySearchResult,
    AvailableSlotDetail,
)
from app.api.v1 import availability as availability_routes
from app.main import app


def test_exact_availability_search_uses_selected_doctor_date_and_timezone(monkeypatch):
    doctor_id, slot_id = uuid.uuid4(), uuid.uuid4()
    now = datetime(2099, 1, 2, 10, tzinfo=timezone.utc)
    search = MagicMock()
    search.side_effect = lambda criteria: AvailabilitySearchResult(
        criteria=criteria,
        total=1,
        slots=[
            AvailableSlotDetail(
                id=slot_id,
                doctor_id=doctor_id,
                doctor_name="Doctor",
                start_time=now,
                end_time=now + timedelta(minutes=30),
                timezone="Asia/Karachi",
            )
        ],
    )
    graph = MagicMock()
    monkeypatch.setattr(availability_routes, "execute_availability_search", search)
    monkeypatch.setattr(availability_routes, "build_doctor_availability_graph", graph)

    response = TestClient(app).post(
        "/api/v1/availability/search",
        json={
            "message": "Find available times",
            "doctor_id": str(doctor_id),
            "appointment_date": "2099-01-02",
            "user_timezone": "Asia/Karachi",
        },
    )

    assert response.status_code == 200
    assert response.json()["slots"][0]["id"] == str(slot_id)
    criteria = search.call_args.args[0]
    assert criteria.doctor_id == doctor_id
    assert criteria.date == "2099-01-02"
    assert criteria.user_timezone == "Asia/Karachi"
    graph.assert_not_called()


def test_natural_language_availability_still_uses_agent(monkeypatch):
    graph = MagicMock()
    graph.invoke.return_value = {"response": "No slots found."}
    build = MagicMock(return_value=graph)
    monkeypatch.setattr(availability_routes, "build_doctor_availability_graph", build)
    response = TestClient(app).post(
        "/api/v1/availability/search", json={"message": "Find a doctor tomorrow"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "No slots found."
    assert graph.invoke.call_args.args[0]["user_message"] == "Find a doctor tomorrow"


def test_exact_search_preserves_availability_guardrails(monkeypatch):
    search = MagicMock()
    monkeypatch.setattr(availability_routes, "execute_availability_search", search)
    response = TestClient(app).post(
        "/api/v1/availability/search",
        json={
            "message": "Book this appointment",
            "doctor_id": str(uuid.uuid4()),
            "appointment_date": "2099-01-02",
        },
    )
    assert response.status_code == 200
    assert response.json()["slots"] == []
    assert "cannot complete a booking" in response.json()["message"]
    search.assert_not_called()


def test_exact_availability_rejects_invalid_identifiers_and_dates():
    client = TestClient(app)
    assert (
        client.post(
            "/api/v1/availability/search",
            json={
                "message": "Find times",
                "doctor_id": "invalid",
                "appointment_date": "2099-01-02",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/availability/search",
            json={
                "message": "Find times",
                "doctor_id": str(uuid.uuid4()),
                "appointment_date": "not-a-date",
            },
        ).status_code
        == 422
    )
