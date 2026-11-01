"""In-memory repository implementations package.

Re-exports all InMemory* classes and the module-level singleton instances
so that existing imports such as::

    from app.repositories.in_memory import InMemoryPatientRepository

continue to work after the split into individual files.
"""

from app.repositories.in_memory.appointment import InMemoryAppointmentRepository
from app.repositories.in_memory.availability import InMemoryAvailabilityRepository
from app.repositories.in_memory.conversation import InMemoryConversationRepository
from app.repositories.in_memory.conversation_message import (
    InMemoryConversationMessageRepository,
)
from app.repositories.in_memory.doctor import InMemoryDoctorRepository
from app.repositories.in_memory.knowledge_chunk import InMemoryKnowledgeChunkRepository
from app.repositories.in_memory.knowledge_document import (
    InMemoryKnowledgeDocumentRepository,
)
from app.repositories.in_memory.memory import InMemoryMemoryRepository
from app.repositories.in_memory.notification_delivery import (
    InMemoryNotificationDeliveryRepository,
)
from app.repositories.in_memory.notification_preference import (
    InMemoryNotificationPreferenceRepository,
)
from app.repositories.in_memory.patient import InMemoryPatientRepository
from app.repositories.in_memory.reminder import InMemoryReminderRepository
from app.repositories.in_memory.specialty import InMemorySpecialtyRepository

# ---------------------------------------------------------------------------
# Module-level singletons (conversation / memory / knowledge subsystems).
# These are shared across the process when running without Supabase.
# ---------------------------------------------------------------------------
_in_memory_conversation_repo = InMemoryConversationRepository()
_in_memory_conversation_message_repo = InMemoryConversationMessageRepository()
_in_memory_memory_repo = InMemoryMemoryRepository()
_in_memory_knowledge_doc_repo = InMemoryKnowledgeDocumentRepository()
_in_memory_knowledge_chunk_repo = InMemoryKnowledgeChunkRepository(
    _in_memory_knowledge_doc_repo
)

__all__ = [
    "InMemoryAppointmentRepository",
    "InMemoryAvailabilityRepository",
    "InMemoryConversationMessageRepository",
    "InMemoryConversationRepository",
    "InMemoryDoctorRepository",
    "InMemoryKnowledgeChunkRepository",
    "InMemoryKnowledgeDocumentRepository",
    "InMemoryMemoryRepository",
    "InMemoryNotificationDeliveryRepository",
    "InMemoryNotificationPreferenceRepository",
    "InMemoryPatientRepository",
    "InMemoryReminderRepository",
    "InMemorySpecialtyRepository",
    "_in_memory_conversation_repo",
    "_in_memory_conversation_message_repo",
    "_in_memory_knowledge_chunk_repo",
    "_in_memory_knowledge_doc_repo",
    "_in_memory_memory_repo",
]
