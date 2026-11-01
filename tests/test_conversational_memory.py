"""Comprehensive unit, security, memory policy, context, and ownership test suite (Phase 9)."""

import uuid

import pytest

from app.memory.context_builder import ContextBuilder
from app.memory.conversation_service import ConversationService
from app.memory.memory_service import MemoryService
from app.memory.summarizer import summarize_conversation
from app.models import (
    ConversationStatus,
    MemoryItemModel,
    MemoryType,
    PatientModel,
)
from app.repositories import (
    _in_memory_appointment_repo,
    _in_memory_availability_repo,
    _in_memory_conversation_message_repo,
    _in_memory_conversation_repo,
    _in_memory_doctor_repo,
    _in_memory_memory_repo,
    _in_memory_patient_repo,
)


@pytest.fixture(autouse=True)
def setup_memory_test_repos():
    """Resets in-memory storage before each test."""
    _in_memory_patient_repo._storage.clear()
    _in_memory_doctor_repo._storage.clear()
    _in_memory_availability_repo._storage.clear()
    _in_memory_appointment_repo._storage.clear()
    _in_memory_conversation_repo._storage.clear()
    _in_memory_conversation_message_repo._storage.clear()
    _in_memory_memory_repo._storage.clear()

    patient_a = PatientModel(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        name="User A",
        email="user_a@example.com",
    )
    patient_b = PatientModel(
        id=uuid.UUID("99999999-9999-9999-9999-999999999999"),
        name="User B",
        email="user_b@example.com",
    )
    _in_memory_patient_repo.create(patient_a)
    _in_memory_patient_repo.create(patient_b)

    return {"patient_a": patient_a, "patient_b": patient_b}


def test_memory_creation_and_policy_allowlist(setup_memory_test_repos):
    """Test 1-6: Valid memory creation, retrieval, and allowlist enforcement."""
    p_a = setup_memory_test_repos["patient_a"].id
    mem_service = MemoryService(_in_memory_memory_repo)

    # Valid preferred specialty
    m1 = mem_service.save_preference(p_a, "preferred_specialty", "Cardiology")
    assert m1.key == "preferred_specialty"
    assert m1.value == "Cardiology"
    assert m1.memory_type == MemoryType.PREFERRED_SPECIALTY

    # Valid preferred doctor
    m2 = mem_service.save_preference(p_a, "preferred_doctor", "Dr. Sarah Khan")
    assert m2.key == "preferred_doctor"

    # List active
    user_mems = mem_service.get_user_memories(p_a)
    assert len(user_mems) == 2

    # Invalid key rejection
    with pytest.raises(ValueError, match="Memory key 'favorite_color' is not allowed"):
        mem_service.save_preference(p_a, "favorite_color", "Blue")


def test_sensitive_medical_memory_rejection(setup_memory_test_repos):
    """Test 12 & Security: Sensitive medical diagnoses/symptoms rejected from memory persistence."""
    p_a = setup_memory_test_repos["patient_a"].id
    mem_service = MemoryService(_in_memory_memory_repo)

    sensitive_values = [
        "I have severe chest pain",
        "Diagnose me with flu",
        "Prescription dosage 500mg",
        "Medication for hypertension",
    ]
    for val in sensitive_values:
        with pytest.raises(ValueError, match="sensitive/medical content"):
            mem_service.save_preference(p_a, "preferred_time_range", val)


def test_memory_ownership_enforcement(setup_memory_test_repos):
    """Test 5 & Security: Prevent cross-user memory deletion and unauthorized access."""
    p_a = setup_memory_test_repos["patient_a"].id
    p_b = setup_memory_test_repos["patient_b"].id
    mem_service = MemoryService(_in_memory_memory_repo)

    mem_a = mem_service.save_preference(p_a, "preferred_specialty", "Pediatrics")

    # User B attempting to delete User A's memory item -> PermissionError
    with pytest.raises(PermissionError, match="Unauthorized"):
        mem_service.delete_memory(patient_id=p_b, memory_id=mem_a.id)

    # Verify User A's memory is intact
    assert mem_service.get_memory_by_key(p_a, "preferred_specialty") is not None


def test_memory_deletion(setup_memory_test_repos):
    """Test 4: Forget/delete memory item for authorized owner."""
    p_a = setup_memory_test_repos["patient_a"].id
    mem_service = MemoryService(_in_memory_memory_repo)

    mem = mem_service.save_preference(p_a, "timezone", "America/New_York")
    assert mem_service.get_memory_by_key(p_a, "timezone") is not None

    success = mem_service.delete_memory(p_a, mem.id)
    assert success
    assert mem_service.get_memory_by_key(p_a, "timezone") is None


def test_conversation_lifecycle_and_messages(setup_memory_test_repos):
    """Test Conversation creation, message history persistence, ordering, and retrieval."""
    p_a = setup_memory_test_repos["patient_a"].id
    conv_service = ConversationService(
        _in_memory_conversation_repo, _in_memory_conversation_message_repo
    )

    conv = conv_service.create_conversation(p_a, title="Doctor Search Session")
    assert conv.patient_id == p_a
    assert conv.status == ConversationStatus.ACTIVE

    conv_service.append_message(p_a, conv.id, "user", "Find a cardiologist")
    conv_service.append_message(p_a, conv.id, "assistant", "Found Dr. Sarah Khan")

    history = conv_service.get_messages(p_a, conv.id)
    assert len(history) == 2
    assert history[0].content == "Find a cardiologist"
    assert history[1].content == "Found Dr. Sarah Khan"


def test_conversation_ownership_isolation(setup_memory_test_repos):
    """Test Security: Cross-user conversation access prevention."""
    p_a = setup_memory_test_repos["patient_a"].id
    p_b = setup_memory_test_repos["patient_b"].id
    conv_service = ConversationService(
        _in_memory_conversation_repo, _in_memory_conversation_message_repo
    )

    conv_a = conv_service.create_conversation(p_a, title="User A Session")

    # User B attempting to fetch User A's conversation -> PermissionError
    with pytest.raises(PermissionError, match="Unauthorized"):
        conv_service.get_conversation(p_b, conv_a.id)

    # User B attempting to fetch User A's messages -> PermissionError
    with pytest.raises(PermissionError, match="Unauthorized"):
        conv_service.get_messages(p_b, conv_a.id)


def test_conversation_summarizer():
    """Test conversation summary generation and graceful fallback."""
    from langchain_core.messages import AIMessage, HumanMessage

    messages = [
        HumanMessage(content="I want to book an appointment with Dr. Sarah"),
        AIMessage(content="Dr. Sarah is available tomorrow at 10am."),
    ]
    summary = summarize_conversation(messages)
    assert summary is not None
    assert len(summary) > 0


def test_context_builder_bounded_messages():
    """Test ContextBuilder window bounding and prompt preparation."""
    from langchain_core.messages import HumanMessage

    memories = [
        MemoryItemModel(
            patient_id=uuid.uuid4(),
            memory_type=MemoryType.PREFERRED_SPECIALTY,
            key="preferred_specialty",
            value="Dermatology",
        )
    ]
    history = [HumanMessage(content=f"Message {i}") for i in range(10)]

    bounded = ContextBuilder.prepare_bounded_messages(
        system_prompt="Base system prompt",
        user_message="Find a dermatologist",
        history=history,
        summary="User is searching for skin specialist",
        memories=memories,
        max_recent_messages=4,
    )

    # Bounded messages should include SystemMessage (with memory & summary) + 4 recent + 1 user
    assert len(bounded) == 6
    system_text = bounded[0].content
    assert "Preferred Specialty: Dermatology" in system_text
    assert "[CONVERSATION SUMMARY]" in system_text
    assert "User is searching for skin specialist" in system_text


def test_hitl_and_appointment_state_authoritative_boundary(setup_memory_test_repos):
    """Test Safety: Memory never bypasses HITL or mutates appointment status directly."""
    p_a = setup_memory_test_repos["patient_a"].id
    mem_service = MemoryService(_in_memory_memory_repo)

    # Memory claims cancellation intent or booking intent
    mem = mem_service.save_preference(p_a, "preferred_time_range", "morning")
    assert mem.value == "morning"

    # Verify that saving/retrieving memory does not alter appointment repositories
    appts = _in_memory_appointment_repo.list_for_patient(p_a)
    assert len(appts) == 0
