"""Composition helpers for the single production persistence backend."""

from typing import Any

from app.infrastructure.db.supabase import get_supabase_client
from app.infrastructure.repositories.supabase import (
    SupabaseAppointmentRepository,
    SupabaseAvailabilityRepository,
    SupabaseConversationMessageRepository,
    SupabaseConversationRepository,
    SupabaseDoctorRepository,
    SupabaseKnowledgeChunkRepository,
    SupabaseKnowledgeDocumentRepository,
    SupabaseMemoryRepository,
    SupabasePatientRepository,
    SupabaseProposalRepository,
    SupabaseSpecialtyRepository,
)


def _client(client: Any = None) -> Any:
    return client if client is not None else get_supabase_client()


def get_patient_repository(client: Any = None) -> SupabasePatientRepository:
    return SupabasePatientRepository(_client(client))


def get_doctor_repository(client: Any = None) -> SupabaseDoctorRepository:
    return SupabaseDoctorRepository(_client(client))


def get_specialty_repository(client: Any = None) -> SupabaseSpecialtyRepository:
    return SupabaseSpecialtyRepository(_client(client))


def get_availability_repository(client: Any = None) -> SupabaseAvailabilityRepository:
    return SupabaseAvailabilityRepository(_client(client))


def get_appointment_repository(client: Any = None) -> SupabaseAppointmentRepository:
    return SupabaseAppointmentRepository(_client(client))


def get_proposal_repository(client: Any = None) -> SupabaseProposalRepository:
    return SupabaseProposalRepository(_client(client))


def get_conversation_repository(client: Any = None) -> SupabaseConversationRepository:
    return SupabaseConversationRepository(_client(client))


def get_conversation_message_repository(
    client: Any = None,
) -> SupabaseConversationMessageRepository:
    return SupabaseConversationMessageRepository(_client(client))


def get_memory_repository(client: Any = None) -> SupabaseMemoryRepository:
    return SupabaseMemoryRepository(_client(client))


def get_knowledge_document_repository(
    client: Any = None,
) -> SupabaseKnowledgeDocumentRepository:
    return SupabaseKnowledgeDocumentRepository(_client(client))


def get_knowledge_chunk_repository(
    client: Any = None,
) -> SupabaseKnowledgeChunkRepository:
    return SupabaseKnowledgeChunkRepository(_client(client))
