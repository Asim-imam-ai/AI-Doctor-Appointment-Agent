"""Supabase repository implementations package.

Re-exports all Supabase* classes so that existing imports such as::

    from app.repositories.supabase import SupabasePatientRepository

continue to work after the split into individual files.
"""

from app.repositories.supabase.appointment import SupabaseAppointmentRepository
from app.repositories.supabase.availability import SupabaseAvailabilityRepository
from app.repositories.supabase.conversation import SupabaseConversationRepository
from app.repositories.supabase.conversation_message import (
    SupabaseConversationMessageRepository,
)
from app.repositories.supabase.doctor import SupabaseDoctorRepository
from app.repositories.supabase.knowledge_chunk import SupabaseKnowledgeChunkRepository
from app.repositories.supabase.knowledge_document import (
    SupabaseKnowledgeDocumentRepository,
)
from app.repositories.supabase.memory import SupabaseMemoryRepository
from app.repositories.supabase.notification_delivery import (
    SupabaseNotificationDeliveryRepository,
)
from app.repositories.supabase.notification_preference import (
    SupabaseNotificationPreferenceRepository,
)
from app.repositories.supabase.patient import SupabasePatientRepository
from app.repositories.supabase.reminder import SupabaseReminderRepository
from app.repositories.supabase.specialty import SupabaseSpecialtyRepository

__all__ = [
    "SupabaseAppointmentRepository",
    "SupabaseAvailabilityRepository",
    "SupabaseConversationMessageRepository",
    "SupabaseConversationRepository",
    "SupabaseDoctorRepository",
    "SupabaseKnowledgeChunkRepository",
    "SupabaseKnowledgeDocumentRepository",
    "SupabaseMemoryRepository",
    "SupabaseNotificationDeliveryRepository",
    "SupabaseNotificationPreferenceRepository",
    "SupabasePatientRepository",
    "SupabaseReminderRepository",
    "SupabaseSpecialtyRepository",
]
