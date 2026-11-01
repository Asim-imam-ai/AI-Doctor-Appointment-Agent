"""Supabase-backed repository adapters."""

from app.infrastructure.repositories.supabase.appointment import (
    SupabaseAppointmentRepository,
)
from app.infrastructure.repositories.supabase.availability import (
    SupabaseAvailabilityRepository,
)
from app.infrastructure.repositories.supabase.conversation import (
    SupabaseConversationRepository,
)
from app.infrastructure.repositories.supabase.conversation_message import (
    SupabaseConversationMessageRepository,
)
from app.infrastructure.repositories.supabase.doctor import SupabaseDoctorRepository
from app.infrastructure.repositories.supabase.knowledge_chunk import (
    SupabaseKnowledgeChunkRepository,
)
from app.infrastructure.repositories.supabase.knowledge_document import (
    SupabaseKnowledgeDocumentRepository,
)
from app.infrastructure.repositories.supabase.memory import SupabaseMemoryRepository
from app.infrastructure.repositories.supabase.patient import SupabasePatientRepository
from app.infrastructure.repositories.supabase.proposal import SupabaseProposalRepository
from app.infrastructure.repositories.supabase.specialty import (
    SupabaseSpecialtyRepository,
)

__all__ = [
    "SupabaseAppointmentRepository",
    "SupabaseAvailabilityRepository",
    "SupabaseConversationRepository",
    "SupabaseConversationMessageRepository",
    "SupabaseDoctorRepository",
    "SupabaseKnowledgeChunkRepository",
    "SupabaseKnowledgeDocumentRepository",
    "SupabaseMemoryRepository",
    "SupabasePatientRepository",
    "SupabaseProposalRepository",
    "SupabaseSpecialtyRepository",
]
