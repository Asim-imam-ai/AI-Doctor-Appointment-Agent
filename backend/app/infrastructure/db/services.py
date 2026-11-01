"""Application composition for domain services and persistence adapters."""

from app.domain.appointments.service import AppointmentService
from app.domain.conversations.service import ConversationService
from app.domain.doctors.service import DoctorService
from app.domain.patients.service import PatientService
from app.domain.scheduling.availability_service import AvailabilityService
from app.infrastructure.db.repositories import (
    get_appointment_repository,
    get_availability_repository,
    get_conversation_message_repository,
    get_conversation_repository,
    get_doctor_repository,
    get_knowledge_chunk_repository,
    get_knowledge_document_repository,
    get_memory_repository,
    get_patient_repository,
    get_specialty_repository,
    get_supabase_client,
)
from app.knowledge.embeddings import EmbeddingsService
from app.knowledge.ingestion import IngestionPipeline
from app.knowledge.retriever import RAGService
from app.memory.context_builder import ContextBuilder
from app.memory.preferences import MemoryService


def get_patient_service() -> PatientService:
    return PatientService(get_patient_repository())


def get_doctor_service() -> DoctorService:
    return DoctorService(get_doctor_repository(), get_specialty_repository())


def get_availability_service() -> AvailabilityService:
    return AvailabilityService(get_availability_repository(), get_doctor_repository())


def get_appointment_service() -> AppointmentService:
    return AppointmentService(
        get_appointment_repository(),
        get_patient_repository(),
        get_doctor_repository(),
        get_availability_repository(),
    )


def get_memory_service() -> MemoryService:
    return MemoryService(get_memory_repository())


def get_conversation_service() -> ConversationService:
    return ConversationService(
        get_conversation_repository(), get_conversation_message_repository()
    )


def get_context_builder() -> ContextBuilder:
    return ContextBuilder()


def get_rag_service() -> RAGService:
    return RAGService(
        chunk_repo=get_knowledge_chunk_repository(),
        doc_repo=get_knowledge_document_repository(),
        embeddings_service=EmbeddingsService(),
    )


def get_ingestion_pipeline() -> IngestionPipeline:
    return IngestionPipeline(
        doc_repo=get_knowledge_document_repository(),
        chunk_repo=get_knowledge_chunk_repository(),
        embeddings_service=EmbeddingsService(),
    )


def get_client_for_auth():
    return get_supabase_client()
