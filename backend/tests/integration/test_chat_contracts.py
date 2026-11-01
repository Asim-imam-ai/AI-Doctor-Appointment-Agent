import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import AuthenticatedPatient, get_current_patient
from app.api.v1 import chat as chat_routes
from app.api.v1 import conversations as conversation_routes
from app.domain.conversations.models import ConversationMessageModel, ConversationModel
from app.domain.proposals.models import (
    BookingProposal,
    CancellationProposal,
    ReschedulingProposal,
)
from app.main import app


@pytest.fixture
def chat_client(monkeypatch):
    patient = AuthenticatedPatient(
        id=uuid.uuid4(),
        auth_user_id=uuid.uuid4(),
        email="patient@example.com",
        role="authenticated",
    )
    service, graph = MagicMock(), MagicMock()
    app.dependency_overrides[get_current_patient] = lambda: patient
    monkeypatch.setattr(chat_routes, "get_conversation_service", lambda: service)
    monkeypatch.setattr(chat_routes, "build_orchestrator_graph", lambda: graph)
    try:
        with TestClient(app) as client:
            yield client, patient, service, graph
    finally:
        app.dependency_overrides.pop(get_current_patient, None)


@pytest.mark.parametrize("kind", ["booking", "cancellation", "rescheduling"])
def test_chat_exposes_only_the_patients_pending_proposal(chat_client, kind):
    client, patient, service, graph = chat_client
    now = datetime.now(timezone.utc)
    common = {
        "patient_id": patient.id,
        "patient_name": "Patient",
        "doctor_id": uuid.uuid4(),
        "doctor_name": "Doctor",
        "expires_at": now + timedelta(minutes=15),
    }
    if kind == "booking":
        proposal = BookingProposal(
            **common,
            booking_request_id=str(uuid.uuid4()),
            slot_id=uuid.uuid4(),
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, minutes=30),
        )
    elif kind == "cancellation":
        proposal = CancellationProposal(
            **common,
            cancellation_request_id=str(uuid.uuid4()),
            appointment_id=uuid.uuid4(),
            appointment_start=now + timedelta(days=1),
            appointment_end=now + timedelta(days=1, minutes=30),
        )
    else:
        proposal = ReschedulingProposal(
            **common,
            reschedule_request_id=str(uuid.uuid4()),
            appointment_id=uuid.uuid4(),
            new_slot_id=uuid.uuid4(),
            old_start_time=now + timedelta(days=1),
            old_end_time=now + timedelta(days=1, minutes=30),
            new_start_time=now + timedelta(days=2),
            new_end_time=now + timedelta(days=2, minutes=30),
        )
    key = f"{kind}_proposal"
    graph.invoke.return_value = {
        "intent": kind,
        "response": "Review the request.",
        "result": {key: proposal.model_dump(mode="json")},
    }
    conversation_id = uuid.uuid4()

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": str(conversation_id),
            "message": "Help with my appointment",
        },
    )

    assert response.status_code == 200
    assert response.json()["requires_hitl"] is True
    assert response.json()[key]["patient_id"] == str(patient.id)
    service.get_conversation.assert_called_with(patient.id, conversation_id)
    assert service.append_message.call_count == 2
    reference = service.append_message.call_args_list[-1].kwargs["metadata"][
        "proposal_reference"
    ]
    assert reference["kind"] == kind
    assert reference["id"] == getattr(
        proposal,
        {
            "booking": "booking_request_id",
            "cancellation": "cancellation_request_id",
            "rescheduling": "reschedule_request_id",
        }[kind],
    )


def test_chat_does_not_treat_knowledge_results_as_approval(chat_client):
    client, _, _, graph = chat_client
    graph.invoke.return_value = {
        "intent": "knowledge",
        "response": "Policy answer.",
        "result": {"answer": "Policy answer."},
    }
    response = client.post(
        "/api/v1/chat",
        json={"session_id": str(uuid.uuid4()), "message": "What is the policy?"},
    )
    assert response.status_code == 200
    assert response.json()["requires_hitl"] is False
    assert response.json()["booking_proposal"] is None


def test_chat_does_not_expose_foreign_proposals(chat_client):
    client, _, _, graph = chat_client
    graph.invoke.return_value = {
        "intent": "booking",
        "response": "Review.",
        "result": {
            "booking_proposal": {
                "patient_id": str(uuid.uuid4()),
                "status": "PENDING_APPROVAL",
            }
        },
    }
    response = client.post(
        "/api/v1/chat",
        json={"session_id": str(uuid.uuid4()), "message": "Book an appointment"},
    )
    assert response.status_code == 200
    assert response.json()["requires_hitl"] is False
    assert response.json()["booking_proposal"] is None


@pytest.mark.parametrize("status", ["BOOKED", "REJECTED", "EXPIRED"])
def test_chat_does_not_present_completed_proposals(chat_client, status):
    client, patient, _, graph = chat_client
    graph.invoke.return_value = {
        "intent": "booking",
        "response": "Request processed.",
        "result": {
            "booking_proposal": {"patient_id": str(patient.id), "status": status}
        },
    }
    response = client.post(
        "/api/v1/chat",
        json={"session_id": str(uuid.uuid4()), "message": "Book an appointment"},
    )
    assert response.status_code == 200
    assert response.json()["requires_hitl"] is False
    assert response.json()["booking_proposal"] is None


def test_owned_conversation_returns_only_valid_assistant_proposal_references(
    chat_client, monkeypatch
):
    client, patient, _, _ = chat_client
    service = MagicMock()
    conversation = ConversationModel(patient_id=patient.id)
    proposal_id = uuid.uuid4()
    service.get_conversation.return_value = conversation
    service.get_messages.return_value = [
        ConversationMessageModel(
            conversation_id=conversation.id,
            role="ASSISTANT",
            content="Review.",
            metadata={
                "proposal_reference": {"id": str(proposal_id), "kind": "booking"}
            },
        ),
        ConversationMessageModel(
            conversation_id=conversation.id,
            role="ASSISTANT",
            content="Invalid.",
            metadata={"proposal_reference": {"id": "invalid", "kind": "booking"}},
        ),
        ConversationMessageModel(
            conversation_id=conversation.id,
            role="USER",
            content="User text.",
            metadata={
                "proposal_reference": {"id": str(proposal_id), "kind": "booking"}
            },
        ),
    ]
    monkeypatch.setattr(
        conversation_routes, "get_conversation_service", lambda: service
    )

    response = client.get(f"/api/v1/conversations/{conversation.id}")
    assert response.status_code == 200
    messages = response.json()["messages"]
    assert messages[0]["proposal_reference"] == {
        "id": str(proposal_id),
        "kind": "booking",
    }
    assert messages[1]["proposal_reference"] is None
    assert messages[2]["proposal_reference"] is None
    service.get_messages.assert_called_once_with(patient.id, conversation.id)


def test_foreign_conversation_does_not_expose_proposal_references(
    chat_client, monkeypatch
):
    client, _, _, _ = chat_client
    service = MagicMock()
    service.get_conversation.side_effect = PermissionError("not owned")
    monkeypatch.setattr(
        conversation_routes, "get_conversation_service", lambda: service
    )
    response = client.get(f"/api/v1/conversations/{uuid.uuid4()}")
    assert response.status_code == 404
    service.get_messages.assert_not_called()
