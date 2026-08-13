"""Unit tests for foundational Pydantic schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.appointment import AppointmentCreate
from app.schemas.chat import ChatRequest
from app.schemas.common import HealthCheckResponse
from app.schemas.patient import PatientCreate


def test_health_check_schema():
    response = HealthCheckResponse()
    assert response.status == "ok"
    assert response.service == "doctor-appointment-agent"


def test_chat_request_schema():
    req = ChatRequest(session_id="s123", message="Hello Doctor")
    assert req.session_id == "s123"
    assert req.message == "Hello Doctor"

    with pytest.raises(ValidationError):
        ChatRequest(session_id="", message="")


def test_patient_create_schema():
    patient = PatientCreate(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
    )
    assert patient.email == "john@example.com"

    with pytest.raises(ValidationError):
        PatientCreate(first_name="", last_name="Doe", email="invalid-email")


def test_appointment_create_schema():
    now = datetime.now(timezone.utc)
    app = AppointmentCreate(
        doctor_id="doc1",
        patient_id="pat1",
        start_time=now,
        end_time=now,
        reason="Checkup",
    )
    assert app.doctor_id == "doc1"
    assert app.reason == "Checkup"
