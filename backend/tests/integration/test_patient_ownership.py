import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import AuthenticatedPatient, get_current_patient
from app.api.v1 import appointments as appointment_routes
from app.domain.appointments.models import AppointmentModel
from app.infrastructure.repositories.supabase.proposal import SupabaseProposalRepository
from app.main import app


@pytest.fixture
def patient_client():
    patient_id = uuid.uuid4()
    identity = AuthenticatedPatient(
        id=patient_id,
        auth_user_id=uuid.uuid4(),
        email="patient@example.com",
        role="authenticated",
    )
    app.dependency_overrides[get_current_patient] = lambda: identity
    try:
        with TestClient(app) as client:
            yield client, patient_id
    finally:
        app.dependency_overrides.pop(get_current_patient, None)


def test_patient_cannot_read_another_patients_appointment(patient_client, monkeypatch):
    client, patient_id = patient_client
    now = datetime.now(timezone.utc)
    appointment = AppointmentModel(
        patient_id=uuid.uuid4(),
        doctor_id=uuid.uuid4(),
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=1, minutes=30),
    )
    service = MagicMock()
    service.get_appointment.return_value = appointment
    monkeypatch.setattr(appointment_routes, "get_appointment_service", lambda: service)

    response = client.get(f"/api/v1/appointments/{appointment.id}")
    assert response.status_code == 404
    assert str(appointment.patient_id) not in response.text

    appointment.patient_id = patient_id
    response = client.get(f"/api/v1/appointments/{appointment.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(appointment.id)
    assert response.json()["patient_id"] == str(patient_id)
    assert response.json()["doctor_id"] == str(appointment.doctor_id)

    service.list_patient_appointments.return_value = [appointment]
    response = client.get("/api/v1/appointments")
    assert response.status_code == 200
    assert response.json()[0]["id"] == str(appointment.id)
    service.list_patient_appointments.assert_called_once_with(patient_id)


@pytest.mark.parametrize(
    ("path", "body_key"),
    [
        ("/api/v1/appointments/{id}/approve", "booking_request_id"),
        ("/api/v1/appointments/cancel/{id}/approve", "cancellation_request_id"),
        ("/api/v1/appointments/reschedule/{id}/approve", "reschedule_request_id"),
    ],
)
@pytest.mark.parametrize("decision", ["APPROVE", "REJECT"])
def test_patient_cannot_decide_another_patients_proposal(
    patient_client, monkeypatch, path, body_key, decision
):
    client, patient_id = patient_client
    proposal_id = uuid.uuid4()
    repository = MagicMock()
    repository.get.return_value = None
    monkeypatch.setattr(
        appointment_routes, "get_proposal_repository", lambda: repository
    )

    response = client.post(
        path.format(id=proposal_id),
        json={body_key: str(proposal_id), "proposal_version": 1, "decision": decision},
    )

    assert response.status_code == 404
    repository.get.assert_called_once_with(proposal_id, patient_id)
    repository.reject.assert_not_called()
    repository.execute.assert_not_called()


def test_supabase_proposal_lookup_scopes_query_to_patient():
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.eq.return_value = query
    query.maybe_single.return_value.execute.return_value.data = None
    proposal_id, patient_id = uuid.uuid4(), uuid.uuid4()

    assert SupabaseProposalRepository(client).get(proposal_id, patient_id) is None
    assert query.eq.call_args_list == [
        call("id", str(proposal_id)),
        call("patient_id", str(patient_id)),
    ]
