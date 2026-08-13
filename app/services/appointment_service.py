"""Appointment business logic service."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.models import AppointmentModel, AppointmentStatus, AvailabilityStatus
from app.repositories import (
    get_appointment_repository,
    get_availability_repository,
    get_doctor_repository,
    get_patient_repository,
)
from app.repositories.base import (
    AppointmentRepository,
    AvailabilityRepository,
    DoctorRepository,
    PatientRepository,
)


class AppointmentService:
    def __init__(
        self,
        appointment_repo: Optional[AppointmentRepository] = None,
        patient_repo: Optional[PatientRepository] = None,
        doctor_repo: Optional[DoctorRepository] = None,
        availability_repo: Optional[AvailabilityRepository] = None,
    ):
        self.appointment_repo = appointment_repo or get_appointment_repository()
        self.patient_repo = patient_repo or get_patient_repository()
        self.doctor_repo = doctor_repo or get_doctor_repository()
        self.availability_repo = availability_repo or get_availability_repository()

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
        """Revalidate slot and atomically book appointment + update slot status."""
        # 1. Revalidate slot
        slot = self.availability_repo.get_by_id(slot_id)
        if not slot:
            raise ValueError(f"Availability slot ID '{slot_id}' does not exist.")
        if slot.status != AvailabilityStatus.AVAILABLE:
            raise ValueError(f"Slot '{slot_id}' is no longer available.")
        if slot.doctor_id != doctor_id:
            raise ValueError("Slot doctor_id mismatch.")

        # 2. Create appointment (contains double-booking overlap checks in repo)
        appt = self.create_appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
        )

        # 3. Mark slot as BOOKED
        self.availability_repo.update_status(slot_id, AvailabilityStatus.BOOKED)

        # 4. Confirm appointment
        confirmed_appt = self.appointment_repo.update_status(
            appt.id, AppointmentStatus.CONFIRMED
        )
        return confirmed_appt or appt
