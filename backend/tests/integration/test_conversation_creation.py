from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.api.dependencies.auth as auth
import app.api.v1.conversations as routes
from app.api.dependencies.auth import AuthenticatedIdentity, AuthenticatedPatient
from app.domain.conversations.service import ConversationService
from app.main import app


def test_create_and_read_conversation_respects_patient_ownership(monkeypatch):
    first, second = uuid4(), uuid4()
    repo = Mock()
    records = {}
    repo.create.side_effect = lambda item: records.setdefault(item.id, item)
    repo.get_by_id.side_effect = records.get
    messages = Mock()
    messages.list_by_conversation.return_value = []
    service = ConversationService(repo, messages)
    monkeypatch.setattr(routes, "get_conversation_service", lambda: service)

    def identity(patient_id):
        return AuthenticatedPatient(
            patient_id, uuid4(), "test@example.com", "authenticated"
        )

    app.dependency_overrides[auth.get_current_patient] = lambda: identity(first)
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/conversations", json={"title": "Test chat"})
            assert response.status_code == 201
            conversation_id = response.json()["id"]
            assert response.json()["patient_id"] == str(first)
            assert (
                client.get(f"/api/v1/conversations/{conversation_id}").status_code
                == 200
            )
            app.dependency_overrides[auth.get_current_patient] = lambda: identity(
                second
            )
            assert (
                client.get(f"/api/v1/conversations/{conversation_id}").status_code
                == 404
            )
    finally:
        app.dependency_overrides.pop(auth.get_current_patient, None)


@pytest.mark.asyncio
async def test_legacy_patient_id_cannot_override_a_different_linked_user(monkeypatch):
    auth_id = uuid4()
    service = Mock()
    service.get_by_external_id.return_value = None
    service.get_patient.return_value = SimpleNamespace(
        id=auth_id, external_user_id=str(uuid4())
    )
    monkeypatch.setattr(auth, "get_patient_service", lambda: service)
    with pytest.raises(HTTPException) as error:
        await auth.get_current_patient(
            AuthenticatedIdentity(auth_id, "test@example.com", "authenticated")
        )
    assert error.value.status_code == 403
