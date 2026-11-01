"""Base and interface definitions for repository layer."""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, List, Optional

from app.models import (
    AppointmentModel,
    AppointmentStatus,
    AvailabilityStatus,
    ConversationMessageModel,
    ConversationModel,
    DoctorAvailabilityModel,
    DoctorModel,
    KnowledgeCategory,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentStatus,
    MemoryItemModel,
    NotificationDeliveryModel,
    NotificationPreferenceModel,
    NotificationStatus,
    PatientModel,
    ReminderModel,
    ReminderStatus,
    SpecialtyModel,
)


class BaseRepository(ABC):  # noqa: B024 - shared client holder; domain subclasses define abstract methods
    """Base repository abstraction for Supabase or in-memory operations."""

    def __init__(self, client: Optional[object] = None) -> None:
        self.client = client


class PatientRepository(BaseRepository, ABC):
    """Abstract interface for Patient data operations."""

    @abstractmethod
    def create(self, patient: PatientModel) -> PatientModel:
        """Create a new patient record."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, patient_id: uuid.UUID) -> Optional[PatientModel]:
        """Fetch patient by primary key ID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[PatientModel]:
        """Fetch patient by unique email address."""
        raise NotImplementedError

    @abstractmethod
    def get_by_external_id(self, external_user_id: str) -> Optional[PatientModel]:
        """Fetch patient by external system user ID."""
        raise NotImplementedError


class DoctorRepository(BaseRepository, ABC):
    """Abstract interface for Doctor data operations."""

    @abstractmethod
    def create(self, doctor: DoctorModel) -> DoctorModel:
        """Create a new doctor record."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, doctor_id: uuid.UUID) -> Optional[DoctorModel]:
        """Fetch doctor by primary key ID."""
        raise NotImplementedError

    @abstractmethod
    def list_active(self) -> List[DoctorModel]:
        """List all active doctors."""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        specialty: Optional[str] = None,
        doctor_name: Optional[str] = None,
        location: Optional[str] = None,
        clinic_name: Optional[str] = None,
        is_active: Optional[bool] = True,
        limit: int = 10,
    ) -> List[DoctorModel]:
        """Search doctors using criteria filters."""
        raise NotImplementedError

    @abstractmethod
    def add_specialty(self, doctor_id: uuid.UUID, specialty_id: uuid.UUID) -> None:
        """Associate a specialty with a doctor."""
        raise NotImplementedError

    @abstractmethod
    def get_specialties(self, doctor_id: uuid.UUID) -> List[SpecialtyModel]:
        """Fetch all specialties for a given doctor."""
        raise NotImplementedError


class SpecialtyRepository(BaseRepository, ABC):
    """Abstract interface for Medical Specialty data operations."""

    @abstractmethod
    def create(self, specialty: SpecialtyModel) -> SpecialtyModel:
        """Create a new medical specialty record."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, specialty_id: uuid.UUID) -> Optional[SpecialtyModel]:
        """Fetch specialty by primary key ID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[SpecialtyModel]:
        """Fetch specialty by unique name."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> List[SpecialtyModel]:
        """List all medical specialties."""
        raise NotImplementedError


class AvailabilityRepository(BaseRepository, ABC):
    """Abstract interface for Doctor Availability Slot operations."""

    @abstractmethod
    def create(self, availability: DoctorAvailabilityModel) -> DoctorAvailabilityModel:
        """Create a new availability slot record."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(
        self, availability_id: uuid.UUID
    ) -> Optional[DoctorAvailabilityModel]:
        """Fetch availability slot by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_available_slots(
        self, doctor_id: uuid.UUID
    ) -> List[DoctorAvailabilityModel]:
        """List future AVAILABLE slots for a doctor."""
        raise NotImplementedError

    @abstractmethod
    def get_by_doctor(self, doctor_id: uuid.UUID) -> List[DoctorAvailabilityModel]:
        """List all slots for a doctor."""
        raise NotImplementedError

    @abstractmethod
    def search_available_slots(
        self,
        doctor_id: Optional[uuid.UUID] = None,
        start_after: Optional[datetime] = None,
        end_before: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[DoctorAvailabilityModel]:
        """Search available slots with time range filters."""
        raise NotImplementedError

    @abstractmethod
    def update_status(
        self, availability_id: uuid.UUID, status: AvailabilityStatus
    ) -> Optional[DoctorAvailabilityModel]:
        """Update slot status (e.g. AVAILABLE -> BOOKED)."""
        raise NotImplementedError


class AppointmentRepository(BaseRepository, ABC):
    """Abstract interface for Patient-Doctor Appointment operations."""

    @abstractmethod
    def create(self, appointment: AppointmentModel) -> AppointmentModel:
        """Create a new appointment record."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, appointment_id: uuid.UUID) -> Optional[AppointmentModel]:
        """Fetch appointment by ID."""
        raise NotImplementedError

    @abstractmethod
    def list_for_patient(self, patient_id: uuid.UUID) -> List[AppointmentModel]:
        """List appointments for a specific patient."""
        raise NotImplementedError

    @abstractmethod
    def list_for_doctor(self, doctor_id: uuid.UUID) -> List[AppointmentModel]:
        """List appointments for a specific doctor."""
        raise NotImplementedError

    @abstractmethod
    def update_status(
        self, appointment_id: uuid.UUID, status: AppointmentStatus
    ) -> Optional[AppointmentModel]:
        """Update appointment lifecycle status."""
        raise NotImplementedError

    @abstractmethod
    def reschedule(
        self,
        appointment_id: uuid.UUID,
        new_start_time: datetime,
        new_end_time: datetime,
        status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    ) -> Optional[AppointmentModel]:
        """Reschedule an existing appointment to a new time window."""
        raise NotImplementedError


class ReminderRepository(BaseRepository, ABC):
    """Abstract interface for Appointment Reminder operations."""

    @abstractmethod
    def create(self, reminder: ReminderModel) -> ReminderModel:
        """Create a new appointment reminder."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, reminder_id: uuid.UUID) -> Optional[ReminderModel]:
        """Fetch reminder by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[ReminderModel]:
        """Fetch reminder by unique idempotency key."""
        raise NotImplementedError

    @abstractmethod
    def list_for_appointment(self, appointment_id: uuid.UUID) -> List[ReminderModel]:
        """List reminders associated with an appointment."""
        raise NotImplementedError

    @abstractmethod
    def list_for_patient(self, patient_id: uuid.UUID) -> List[ReminderModel]:
        """List reminders associated with a patient."""
        raise NotImplementedError

    @abstractmethod
    def find_due_reminders(
        self, as_of_time: Optional[datetime] = None, limit: int = 50
    ) -> List[ReminderModel]:
        """Find pending reminders due for dispatch as of specified timestamp."""
        raise NotImplementedError

    @abstractmethod
    def claim_reminder(self, reminder_id: uuid.UUID) -> Optional[ReminderModel]:
        """Atomically claim a pending reminder for processing."""
        raise NotImplementedError

    @abstractmethod
    def update_status(
        self,
        reminder_id: uuid.UUID,
        status: ReminderStatus,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
    ) -> Optional[ReminderModel]:
        """Update reminder status and outcome timestamps."""
        raise NotImplementedError

    @abstractmethod
    def cancel_for_appointment(self, appointment_id: uuid.UUID) -> int:
        """Cancel all pending reminders for an appointment."""
        raise NotImplementedError


class NotificationPreferenceRepository(BaseRepository, ABC):
    """Abstract interface for Patient Notification Preference operations."""

    @abstractmethod
    def get_by_patient_id(
        self, patient_id: uuid.UUID
    ) -> Optional[NotificationPreferenceModel]:
        """Fetch notification preferences for a patient."""
        raise NotImplementedError

    @abstractmethod
    def create_or_update(
        self, preference: NotificationPreferenceModel
    ) -> NotificationPreferenceModel:
        """Create or update patient notification preferences."""
        raise NotImplementedError


class NotificationDeliveryRepository(BaseRepository, ABC):
    """Abstract interface for Notification Audit Delivery operations."""

    @abstractmethod
    def create(self, delivery: NotificationDeliveryModel) -> NotificationDeliveryModel:
        """Create a notification delivery audit record."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, delivery_id: uuid.UUID) -> Optional[NotificationDeliveryModel]:
        """Fetch delivery audit record by ID."""
        raise NotImplementedError

    @abstractmethod
    def update_status(
        self,
        delivery_id: uuid.UUID,
        status: NotificationStatus,
        provider_response_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[NotificationDeliveryModel]:
        """Update delivery status and provider details."""
        raise NotImplementedError


class ConversationRepository(BaseRepository, ABC):
    """Abstract interface for Conversation session operations."""

    @abstractmethod
    def create(self, conversation: ConversationModel) -> ConversationModel:
        """Create a new conversation session."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, conversation_id: uuid.UUID) -> Optional[ConversationModel]:
        """Fetch conversation by ID."""
        raise NotImplementedError

    @abstractmethod
    def list_for_patient(
        self, patient_id: uuid.UUID, limit: int = 50
    ) -> List[ConversationModel]:
        """List conversations for a patient."""
        raise NotImplementedError

    @abstractmethod
    def update_summary(
        self, conversation_id: uuid.UUID, summary: str
    ) -> Optional[ConversationModel]:
        """Update conversation summary."""
        raise NotImplementedError

    @abstractmethod
    def update_status(
        self, conversation_id: uuid.UUID, status: Any
    ) -> Optional[ConversationModel]:
        """Update conversation status."""
        raise NotImplementedError

    @abstractmethod
    def delete_conversation(self, conversation_id: uuid.UUID) -> bool:
        """Soft delete or purge conversation."""
        raise NotImplementedError


class ConversationMessageRepository(BaseRepository, ABC):
    """Abstract interface for Conversation Message operations."""

    @abstractmethod
    def create(self, message: ConversationMessageModel) -> ConversationMessageModel:
        """Create a new conversation message record."""
        raise NotImplementedError

    @abstractmethod
    def list_by_conversation(
        self, conversation_id: uuid.UUID, limit: int = 100
    ) -> List[ConversationMessageModel]:
        """List messages belonging to a conversation session."""
        raise NotImplementedError

    @abstractmethod
    def delete_by_conversation(self, conversation_id: uuid.UUID) -> int:
        """Delete all messages for a conversation session."""
        raise NotImplementedError


class MemoryRepository(BaseRepository, ABC):
    """Abstract interface for Long-term Patient Memory operations."""

    @abstractmethod
    def create_or_update(self, item: MemoryItemModel) -> MemoryItemModel:
        """Create or update a patient memory key-value item."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, memory_id: uuid.UUID) -> Optional[MemoryItemModel]:
        """Fetch memory item by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_key(self, patient_id: uuid.UUID, key: str) -> Optional[MemoryItemModel]:
        """Fetch memory item by patient ID and key."""
        raise NotImplementedError

    @abstractmethod
    def list_for_patient(
        self, patient_id: uuid.UUID, active_only: bool = True
    ) -> List[MemoryItemModel]:
        """List memory items for a patient."""
        raise NotImplementedError

    @abstractmethod
    def delete_memory(self, memory_id: uuid.UUID) -> bool:
        """Delete a memory item by ID."""
        raise NotImplementedError

    @abstractmethod
    def delete_by_key(self, patient_id: uuid.UUID, key: str) -> bool:
        """Delete a memory item by patient ID and key."""
        raise NotImplementedError


class KnowledgeDocumentRepository(BaseRepository, ABC):
    """Abstract interface for Knowledge Base Document operations."""

    @abstractmethod
    def create(self, doc: KnowledgeDocumentModel) -> KnowledgeDocumentModel:
        """Ingest a new knowledge base document."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, doc_id: uuid.UUID) -> Optional[KnowledgeDocumentModel]:
        """Fetch knowledge document by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_hash(self, content_hash: str) -> Optional[KnowledgeDocumentModel]:
        """Fetch knowledge document by SHA-256 content hash."""
        raise NotImplementedError

    @abstractmethod
    def list_documents(
        self,
        category: Optional[KnowledgeCategory] = None,
        status: Optional[KnowledgeDocumentStatus] = None,
    ) -> List[KnowledgeDocumentModel]:
        """List knowledge documents with optional category and status filters."""
        raise NotImplementedError

    @abstractmethod
    def update_status(
        self, doc_id: uuid.UUID, status: KnowledgeDocumentStatus
    ) -> Optional[KnowledgeDocumentModel]:
        """Update knowledge document status (ACTIVE/INACTIVE)."""
        raise NotImplementedError


class KnowledgeChunkRepository(BaseRepository, ABC):
    """Abstract interface for Knowledge Base Chunk & Vector Operations."""

    @abstractmethod
    def save_chunks(
        self, chunks: List[KnowledgeChunkModel]
    ) -> List[KnowledgeChunkModel]:
        """Save a batch of document vector chunks."""
        raise NotImplementedError

    @abstractmethod
    def search_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 4,
        category: Optional[KnowledgeCategory] = None,
        min_similarity: float = 0.0,
    ) -> List[KnowledgeChunkModel]:
        """Perform vector search for similar document chunks."""
        raise NotImplementedError

    @abstractmethod
    def delete_chunks_by_document(self, document_id: uuid.UUID) -> bool:
        """Delete all vector chunks associated with a document."""
        raise NotImplementedError
