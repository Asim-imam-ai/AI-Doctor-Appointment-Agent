"""Conversation and preference behavior tested with per-test repository mocks."""

import uuid
from unittest.mock import Mock

import pytest

from app.domain.conversations.service import ConversationService
from app.domain.models import (
    ConversationModel,
    MemoryItemModel,
    MemoryType,
)
from app.memory.preferences import MemoryService


def test_memory_allowlist_persists_only_supported_preferences():
    repository = Mock()
    repository.create_or_update.side_effect = lambda item: item
    service = MemoryService(repository)
    patient_id = uuid.uuid4()

    item = service.save_preference(patient_id, "preferred_specialty", " Cardiology ")
    assert item.patient_id == patient_id
    assert item.memory_type is MemoryType.PREFERRED_SPECIALTY
    assert item.value == "Cardiology"
    repository.create_or_update.assert_called_once_with(item)

    with pytest.raises(ValueError, match="is not allowed"):
        service.save_preference(patient_id, "home_address", "123 Main Street")
    repository.create_or_update.assert_called_once()


@pytest.mark.parametrize("medical", ["diagnosis", "chest pain", "prescription"])
def test_memory_rejects_sensitive_medical_content(medical: str):
    repository = Mock()
    service = MemoryService(repository)
    with pytest.raises(ValueError, match="sensitive/medical content"):
        service.save_preference(uuid.uuid4(), "preferred_specialty", medical)
    repository.create_or_update.assert_not_called()


def test_memory_delete_checks_owner_before_repository_mutation():
    repository = Mock()
    owner = uuid.uuid4()
    memory = MemoryItemModel(
        patient_id=owner,
        memory_type=MemoryType.PREFERRED_SPECIALTY,
        key="preferred_specialty",
        value="Cardiology",
    )
    repository.get_by_id.return_value = memory
    service = MemoryService(repository)

    with pytest.raises(PermissionError, match="do not own"):
        service.delete_memory(uuid.uuid4(), memory.id)
    repository.delete_memory.assert_not_called()


def test_conversation_service_enforces_owner_and_updates_last_message():
    conversation_repo, message_repo = Mock(), Mock()
    owner = uuid.uuid4()
    conversation = ConversationModel(patient_id=owner, title="Visit")
    conversation_repo.get_by_id.return_value = conversation
    message_repo.create.side_effect = lambda message: message
    service = ConversationService(conversation_repo, message_repo)

    saved = service.append_message(owner, conversation.id, "USER", "Find a doctor")
    assert saved.content == "Find a doctor"
    message_repo.create.assert_called_once()
    conversation_repo.touch.assert_called_once()

    with pytest.raises(PermissionError):
        service.append_message(uuid.uuid4(), conversation.id, "USER", "Private")
    assert message_repo.create.call_count == 1


def test_conversation_message_is_bounded_before_repository_write():
    conversation_repo, message_repo = Mock(), Mock()
    owner = uuid.uuid4()
    conversation = ConversationModel(patient_id=owner)
    conversation_repo.get_by_id.return_value = conversation
    message_repo.create.side_effect = lambda message: message
    service = ConversationService(conversation_repo, message_repo)
    saved = service.append_message(owner, conversation.id, "USER", "x" * 5000)
    assert len(saved.content) == 4000
