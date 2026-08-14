"""Base and interface definitions for repository layer."""

import uuid
from datetime import datetime
from typing import List, Optional

from app.models import (
    AppointmentModel,
    AppointmentStatus,
    AvailabilityStatus,
    DoctorAvailabilityModel,
    DoctorModel,
    NotificationDeliveryModel,
    NotificationPreferenceModel,
    NotificationStatus,
    PatientModel,
    ReminderModel,
    ReminderStatus,
    SpecialtyModel,
)


class BaseRepository:
    """Base repository abstraction for Supabase or in-memory operations."""

    def __init__(self, client: Optional[object] = None):
        self.client = client


class PatientRepository(BaseRepository):
    def create(self, patient: PatientModel) -> PatientModel:
        raise NotImplementedError

    def get_by_id(self, patient_id: uuid.UUID) -> Optional[PatientModel]:
        raise NotImplementedError

    def get_by_email(self, email: str) -> Optional[PatientModel]:
        raise NotImplementedError

    def get_by_external_id(self, external_user_id: str) -> Optional[PatientModel]:
        raise NotImplementedError


class DoctorRepository(BaseRepository):
    def create(self, doctor: DoctorModel) -> DoctorModel:
        raise NotImplementedError

    def get_by_id(self, doctor_id: uuid.UUID) -> Optional[DoctorModel]:
        raise NotImplementedError

    def list_active(self) -> List[DoctorModel]:
        raise NotImplementedError

    def search(
        self,
        specialty: Optional[str] = None,
        doctor_name: Optional[str] = None,
        location: Optional[str] = None,
        clinic_name: Optional[str] = None,
        is_active: Optional[bool] = True,
        limit: int = 10,
    ) -> List[DoctorModel]:
        raise NotImplementedError

    def add_specialty(self, doctor_id: uuid.UUID, specialty_id: uuid.UUID) -> None:
        raise NotImplementedError

    def get_specialties(self, doctor_id: uuid.UUID) -> List[SpecialtyModel]:
        raise NotImplementedError


class SpecialtyRepository(BaseRepository):
    def create(self, specialty: SpecialtyModel) -> SpecialtyModel:
        raise NotImplementedError

    def get_by_id(self, specialty_id: uuid.UUID) -> Optional[SpecialtyModel]:
        raise NotImplementedError

    def get_by_name(self, name: str) -> Optional[SpecialtyModel]:
        raise NotImplementedError

    def list_all(self) -> List[SpecialtyModel]:
        raise NotImplementedError


class AvailabilityRepository(BaseRepository):
    def create(self, availability: DoctorAvailabilityModel) -> DoctorAvailabilityModel:
        raise NotImplementedError

    def get_by_id(
        self, availability_id: uuid.UUID
    ) -> Optional[DoctorAvailabilityModel]:
        raise NotImplementedError

    def get_available_slots(
        self, doctor_id: uuid.UUID
    ) -> List[DoctorAvailabilityModel]:
        raise NotImplementedError

    def get_by_doctor(self, doctor_id: uuid.UUID) -> List[DoctorAvailabilityModel]:
        raise NotImplementedError

    def search_available_slots(
        self,
        doctor_id: Optional[uuid.UUID] = None,
        start_after: Optional[datetime] = None,
        end_before: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[DoctorAvailabilityModel]:
        raise NotImplementedError

    def update_status(
        self, availability_id: uuid.UUID, status: AvailabilityStatus
    ) -> Optional[DoctorAvailabilityModel]:
        raise NotImplementedError


class AppointmentRepository(BaseRepository):
    def create(self, appointment: AppointmentModel) -> AppointmentModel:
        raise NotImplementedError

    def get_by_id(self, appointment_id: uuid.UUID) -> Optional[AppointmentModel]:
        raise NotImplementedError

    def list_for_patient(self, patient_id: uuid.UUID) -> List[AppointmentModel]:
        raise NotImplementedError

    def list_for_doctor(self, doctor_id: uuid.UUID) -> List[AppointmentModel]:
        raise NotImplementedError

    def update_status(
        self, appointment_id: uuid.UUID, status: AppointmentStatus
    ) -> Optional[AppointmentModel]:
        raise NotImplementedError

    def reschedule(
        self,
        appointment_id: uuid.UUID,
        new_start_time: datetime,
        new_end_time: datetime,
        status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    ) -> Optional[AppointmentModel]:
        raise NotImplementedError


class ReminderRepository(BaseRepository):
    def create(self, reminder: ReminderModel) -> ReminderModel:
        raise NotImplementedError

    def get_by_id(self, reminder_id: uuid.UUID) -> Optional[ReminderModel]:
        raise NotImplementedError

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[ReminderModel]:
        raise NotImplementedError

    def list_for_appointment(self, appointment_id: uuid.UUID) -> List[ReminderModel]:
        raise NotImplementedError

    def list_for_patient(self, patient_id: uuid.UUID) -> List[ReminderModel]:
        raise NotImplementedError

    def find_due_reminders(
        self, as_of_time: Optional[datetime] = None, limit: int = 50
    ) -> List[ReminderModel]:
        raise NotImplementedError

    def claim_reminder(self, reminder_id: uuid.UUID) -> Optional[ReminderModel]:
        raise NotImplementedError

    def update_status(
        self,
        reminder_id: uuid.UUID,
        status: ReminderStatus,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
    ) -> Optional[ReminderModel]:
        raise NotImplementedError

    def cancel_for_appointment(self, appointment_id: uuid.UUID) -> int:
        raise NotImplementedError


class NotificationPreferenceRepository(BaseRepository):
    def get_by_patient_id(
        self, patient_id: uuid.UUID
    ) -> Optional[NotificationPreferenceModel]:
        raise NotImplementedError

    def create_or_update(
        self, preference: NotificationPreferenceModel
    ) -> NotificationPreferenceModel:
        raise NotImplementedError


class NotificationDeliveryRepository(BaseRepository):
    def create(self, delivery: NotificationDeliveryModel) -> NotificationDeliveryModel:
        raise NotImplementedError

    def get_by_id(self, delivery_id: uuid.UUID) -> Optional[NotificationDeliveryModel]:
        raise NotImplementedError

    def update_status(
        self,
        delivery_id: uuid.UUID,
        status: NotificationStatus,
        provider_response_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[NotificationDeliveryModel]:
        raise NotImplementedError
