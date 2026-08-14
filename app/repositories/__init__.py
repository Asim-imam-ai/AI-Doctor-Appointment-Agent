"""Repository factory / central dependency retriever."""

from typing import Optional

from app.infrastructure.supabase.client import get_supabase_client
from app.repositories.base import (
    AppointmentRepository,
    AvailabilityRepository,
    ConversationMessageRepository,
    ConversationRepository,
    DoctorRepository,
    MemoryRepository,
    NotificationDeliveryRepository,
    NotificationPreferenceRepository,
    PatientRepository,
    ReminderRepository,
    SpecialtyRepository,
)
from app.repositories.in_memory import (
    InMemoryAppointmentRepository,
    InMemoryAvailabilityRepository,
    InMemoryDoctorRepository,
    InMemoryNotificationDeliveryRepository,
    InMemoryNotificationPreferenceRepository,
    InMemoryPatientRepository,
    InMemoryReminderRepository,
    InMemorySpecialtyRepository,
    _in_memory_conversation_message_repo,
    _in_memory_conversation_repo,
    _in_memory_memory_repo,
)
from app.repositories.in_memory import (
    InMemoryConversationMessageRepository as InMemoryConversationMessageRepository,
)
from app.repositories.in_memory import (
    InMemoryConversationRepository as InMemoryConversationRepository,
)
from app.repositories.in_memory import (
    InMemoryMemoryRepository as InMemoryMemoryRepository,
)
from app.repositories.supabase import (
    SupabaseAppointmentRepository,
    SupabaseAvailabilityRepository,
    SupabaseConversationMessageRepository,
    SupabaseConversationRepository,
    SupabaseDoctorRepository,
    SupabaseMemoryRepository,
    SupabaseNotificationDeliveryRepository,
    SupabaseNotificationPreferenceRepository,
    SupabasePatientRepository,
    SupabaseReminderRepository,
    SupabaseSpecialtyRepository,
)

# Global fallback singletons for in-memory mode when Supabase credentials are missing
_in_memory_patient_repo = InMemoryPatientRepository()
_in_memory_specialty_repo = InMemorySpecialtyRepository()
_in_memory_doctor_repo = InMemoryDoctorRepository()
_in_memory_doctor_repo.set_specialty_repo(_in_memory_specialty_repo)
_in_memory_availability_repo = InMemoryAvailabilityRepository(_in_memory_doctor_repo)
_in_memory_appointment_repo = InMemoryAppointmentRepository(
    patient_repo=_in_memory_patient_repo, doctor_repo=_in_memory_doctor_repo
)
_in_memory_reminder_repo = InMemoryReminderRepository()
_in_memory_notification_preference_repo = InMemoryNotificationPreferenceRepository()
_in_memory_notification_delivery_repo = InMemoryNotificationDeliveryRepository()


def get_patient_repository(client: Optional[object] = None) -> PatientRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabasePatientRepository(supabase_client)
    return _in_memory_patient_repo


def get_doctor_repository(client: Optional[object] = None) -> DoctorRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseDoctorRepository(supabase_client)
    return _in_memory_doctor_repo


def get_specialty_repository(client: Optional[object] = None) -> SpecialtyRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseSpecialtyRepository(supabase_client)
    return _in_memory_specialty_repo


def get_availability_repository(
    client: Optional[object] = None,
) -> AvailabilityRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseAvailabilityRepository(supabase_client)
    return _in_memory_availability_repo


def get_appointment_repository(
    client: Optional[object] = None,
) -> AppointmentRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseAppointmentRepository(supabase_client)
    return _in_memory_appointment_repo


def get_reminder_repository(
    client: Optional[object] = None,
) -> ReminderRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseReminderRepository(supabase_client)
    return _in_memory_reminder_repo


def get_notification_preference_repository(
    client: Optional[object] = None,
) -> NotificationPreferenceRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseNotificationPreferenceRepository(supabase_client)
    return _in_memory_notification_preference_repo


def get_notification_delivery_repository(
    client: Optional[object] = None,
) -> NotificationDeliveryRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseNotificationDeliveryRepository(supabase_client)
    return _in_memory_notification_delivery_repo


def get_conversation_repository(
    client: Optional[object] = None,
) -> ConversationRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseConversationRepository(supabase_client)
    return _in_memory_conversation_repo


def get_conversation_message_repository(
    client: Optional[object] = None,
) -> ConversationMessageRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseConversationMessageRepository(supabase_client)
    return _in_memory_conversation_message_repo


def get_memory_repository(
    client: Optional[object] = None,
) -> MemoryRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseMemoryRepository(supabase_client)
    return _in_memory_memory_repo
