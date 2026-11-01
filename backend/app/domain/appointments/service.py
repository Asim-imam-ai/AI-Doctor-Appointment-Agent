import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.core.config import settings
from app.domain.appointments.models import AppointmentModel, AppointmentStatus
from app.domain.appointments.repository import AppointmentRepository
from app.domain.doctors.repository import DoctorRepository
from app.domain.patients.repository import PatientRepository
from app.domain.scheduling.repository import AvailabilityRepository


class AppointmentService:
    def __init__(
        self,
        appointment_repo: AppointmentRepository,
        patient_repo: PatientRepository,
        doctor_repo: DoctorRepository,
        availability_repo: AvailabilityRepository,
    ):
        self.appointment_repo = appointment_repo
        self.patient_repo = patient_repo
        self.doctor_repo = doctor_repo
        self.availability_repo = availability_repo

    def create_appointment(
        self,
        patient_id: uuid.UUID,
        doctor_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        reason: Optional[str] = None,
    ) -> AppointmentModel:
        # Deterministic Business Rules Validation
        if start_time >= end_time:
            raise ValueError("Appointment start_time must be strictly before end_time.")

        now_utc = datetime.now(timezone.utc)
        start_compare = (
            start_time
            if start_time.tzinfo is not None
            else start_time.replace(tzinfo=timezone.utc)
        )
        if start_compare < now_utc:
            raise ValueError("Cannot schedule an appointment in the past.")

        patient = self.patient_repo.get_by_id(patient_id)
        if not patient:
            raise ValueError(f"Patient with ID '{patient_id}' does not exist.")

        doctor = self.doctor_repo.get_by_id(doctor_id)
        if not doctor:
            raise ValueError(f"Doctor with ID '{doctor_id}' does not exist.")
        if not doctor.is_active:
            raise ValueError(f"Doctor '{doctor.name}' is not currently active.")

        appointment = AppointmentModel(
            patient_id=patient_id,
            doctor_id=doctor_id,
            start_time=start_time,
            end_time=end_time,
            status=AppointmentStatus.PENDING,
            reason=reason,
        )

        return self.appointment_repo.create(appointment)

    def get_appointment(self, appointment_id: uuid.UUID) -> Optional[AppointmentModel]:
        return self.appointment_repo.get_by_id(appointment_id)

    def list_patient_appointments(
        self, patient_id: uuid.UUID
    ) -> List[AppointmentModel]:
        return self.appointment_repo.list_for_patient(patient_id)

    def list_doctor_appointments(self, doctor_id: uuid.UUID) -> List[AppointmentModel]:
        return self.appointment_repo.list_for_doctor(doctor_id)

    def update_appointment_status(
        self, appointment_id: uuid.UUID, status: AppointmentStatus
    ) -> Optional[AppointmentModel]:
        return self.appointment_repo.update_status(appointment_id, status)

    def atomic_create_appointment_and_update_slot(
        self,
        patient_id: uuid.UUID,
        doctor_id: uuid.UUID,
        slot_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        reason: Optional[str] = None,
    ) -> AppointmentModel:
        """Revalidate patient and doctor, then use one atomic database operation."""
        if start_time >= end_time:
            raise ValueError("Appointment start_time must be strictly before end_time.")
        patient = self.patient_repo.get_by_id(patient_id)
        if patient is None:
            raise ValueError("Authenticated patient profile was not found.")
        doctor = self.doctor_repo.get_by_id(doctor_id)
        if doctor is None or not doctor.is_active:
            raise ValueError("Selected doctor is unavailable.")
        return self.appointment_repo.book_slot(
            patient_id=patient_id,
            doctor_id=doctor_id,
            slot_id=slot_id,
            reason=reason,
        )

    def check_cancellation_eligibility(
        self, appointment_id: uuid.UUID, patient_id: uuid.UUID
    ) -> AppointmentModel:
        """Deterministically validates cancellation eligibility."""
        appt = self.appointment_repo.get_by_id(appointment_id)
        if not appt:
            raise ValueError(f"Appointment ID '{appointment_id}' does not exist.")
        if appt.patient_id != patient_id:
            raise ValueError("Unauthorized: appointment does not belong to user.")
        if appt.status == AppointmentStatus.CANCELLED:
            raise ValueError("Appointment is already cancelled.")

        now_utc = datetime.now(timezone.utc)
        start_compare = (
            appt.start_time
            if appt.start_time.tzinfo is not None
            else appt.start_time.replace(tzinfo=timezone.utc)
        )
        if start_compare < now_utc:
            raise ValueError("Cannot cancel a past or completed appointment.")

        cancellation_window = timedelta(
            minutes=getattr(settings, "CANCELLATION_WINDOW_MINUTES", 120)
        )
        if (start_compare - now_utc) < cancellation_window:
            raise ValueError(
                f"Cancellation window policy violation: appointments must be cancelled "
                f"at least {getattr(settings, 'CANCELLATION_WINDOW_MINUTES', 120)} minutes in advance."
            )
        return appt

    def cancel_appointment(
        self, appointment_id: uuid.UUID, patient_id: uuid.UUID
    ) -> AppointmentModel:
        """Revalidates eligibility and atomically cancels the appointment."""
        self.check_cancellation_eligibility(appointment_id, patient_id)
        return self.appointment_repo.cancel_atomically(
            appointment_id,
            patient_id,
            settings.CANCELLATION_WINDOW_MINUTES,
        )

    def check_reschedule_eligibility(
        self, appointment_id: uuid.UUID, patient_id: uuid.UUID
    ) -> AppointmentModel:
        """Deterministically validates rescheduling eligibility for old appointment."""
        appt = self.appointment_repo.get_by_id(appointment_id)
        if not appt:
            raise ValueError(f"Appointment ID '{appointment_id}' does not exist.")
        if appt.patient_id != patient_id:
            raise ValueError("Unauthorized: appointment does not belong to user.")
        if appt.status == AppointmentStatus.CANCELLED:
            raise ValueError("Cannot reschedule a cancelled appointment.")

        now_utc = datetime.now(timezone.utc)
        start_compare = (
            appt.start_time
            if appt.start_time.tzinfo is not None
            else appt.start_time.replace(tzinfo=timezone.utc)
        )
        if start_compare < now_utc:
            raise ValueError("Cannot reschedule a past or completed appointment.")
        return appt

    def atomic_reschedule_appointment(
        self,
        appointment_id: uuid.UUID,
        patient_id: uuid.UUID,
        new_slot_id: uuid.UUID,
    ) -> AppointmentModel:
        """Revalidates old appointment & new slot, securing new slot and updating appointment."""
        # 1. Revalidate old appointment
        self.check_reschedule_eligibility(appointment_id, patient_id)

        return self.appointment_repo.reschedule_atomically(
            appointment_id, patient_id, new_slot_id
        )
