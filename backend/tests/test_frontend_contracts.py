"""API contracts required by the patient frontend."""

import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.dependencies.auth import AuthenticatedIdentity
from app.api.schemas.appointment import AppointmentResponse
from app.api.v1.conversations import router
from app.api.v1.patients import PatientSetupRequest, setup_my_profile
from app.domain.patients.models import PatientModel


def test_memory_routes_precede_dynamic_conversation_route():
    paths = [route.path for route in router.routes]
    assert paths.index("/memory") < paths.index("/{conversation_id}")


def test_appointment_response_accepts_domain_status():
    payload = {
        "id": "a",
        "doctor_id": "d",
        "patient_id": "p",
        "start_time": "2026-11-05T10:00:00Z",
        "end_time": "2026-11-05T10:30:00Z",
        "status": "CONFIRMED",
        "created_at": "2026-11-01T10:00:00Z",
    }
    assert AppointmentResponse.model_validate(payload).status.value == "CONFIRMED"


def test_knowledge_factories_supply_embeddings(monkeypatch):
    import app.api.v1.knowledge as module

    monkeypatch.setattr(module, "get_knowledge_chunk_repository", lambda: object())
    monkeypatch.setattr(module, "get_knowledge_document_repository", lambda: object())
    assert module._get_rag_service().embeddings_service is not None
    assert module._get_ingestion_pipeline().embeddings_service is not None


@pytest.mark.asyncio
async def test_patient_setup_uses_verified_identity(monkeypatch):
    import app.api.v1.patients as module

    identity = AuthenticatedIdentity(
        auth_user_id=uuid.uuid4(), email="patient@example.com", role="authenticated"
    )

    class Service:
        def get_by_external_id(self, _external_id):
            return None

        def get_by_email(self, _email):
            return None

        def register_patient(self, **kwargs):
            assert kwargs["external_user_id"] == str(identity.auth_user_id)
            assert kwargs["email"] == identity.email
            return PatientModel(**kwargs)

    monkeypatch.setattr(module, "get_patient_service", lambda: Service())
    response = await setup_my_profile(
        PatientSetupRequest(name="Amira Khan", timezone="Asia/Karachi"), identity
    )
    assert response.name == "Amira Khan"
    assert response.email == "patient@example.com"


@pytest.mark.asyncio
async def test_patient_setup_rejects_missing_verified_email():
    identity = AuthenticatedIdentity(
        auth_user_id=uuid.uuid4(), email=None, role="authenticated"
    )
    with pytest.raises(HTTPException) as exc:
        await setup_my_profile(PatientSetupRequest(name="Amira Khan"), identity)
    assert exc.value.status_code == 403


def test_patient_setup_rejects_client_identity_and_blank_names():
    with pytest.raises(ValidationError):
        PatientSetupRequest.model_validate(
            {"name": "Amira Khan", "patient_id": str(uuid.uuid4())}
        )
    with pytest.raises(ValidationError):
        PatientSetupRequest.model_validate({"name": "   "})
