"""In-memory Appointment repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models import AppointmentModel, AppointmentStatus
from app.repositories.base import (
    AppointmentRepository,
    DoctorRepository,
    PatientRepository,
)


class InMemoryAppointmentRepository(AppointmentRepository):
    def __init__(
        self,
        patient_repo: Optional[PatientRepository] = None,
        doctor_repo: Optional[DoctorRepository] = None,
    ) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, AppointmentModel] = {}
        self.patient_repo = patient_repo
        self.doctor_repo = doctor_repo

    def create(self, appointment: AppointmentModel) -> AppointmentModel:
        if self.patient_repo and not self.patient_repo.get_by_id(
            appointment.patient_id
        ):
            raise ValueError(f"Patient ID '{appointment.patient_id}' does not exist.")
        if self.doctor_repo:
            doctor = self.doctor_repo.get_by_id(appointment.doctor_id)
            if not doctor:
                raise ValueError(f"Doctor ID '{appointment.doctor_id}' does not exist.")
            if not doctor.is_active:
                raise ValueError(f"Doctor '{doctor.name}' is not active.")

        # Double-booking guard: same doctor, overlapping non-cancelled/expired slots
        for appt in self._storage.values():
            if appt.doctor_id == appointment.doctor_id and appt.status in (
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
            ):
                if (
                    appointment.start_time < appt.end_time
                    and appt.start_time < appointment.end_time
                ):
                    raise ValueError(
                        "Appointment time conflict for doctor "
                        f"'{appointment.doctor_id}'"
                    )

        self._storage[appointment.id] = appointment
        return appointment

    def get_by_id(self, appointment_id: uuid.UUID) -> Optional[AppointmentModel]:
        return self._storage.get(appointment_id)

    def list_for_patient(self, patient_id: uuid.UUID) -> List[AppointmentModel]:
        return [
            appt for appt in self._storage.values() if appt.patient_id == patient_id
        ]

    def list_for_doctor(self, doctor_id: uuid.UUID) -> List[AppointmentModel]:
        return [appt for appt in self._storage.values() if appt.doctor_id == doctor_id]

    def update_status(
        self, appointment_id: uuid.UUID, status: AppointmentStatus
    ) -> Optional[AppointmentModel]:
        appt = self._storage.get(appointment_id)
        if not appt:
            return None
        updated = appt.model_copy(
            update={"status": status, "updated_at": datetime.now(timezone.utc)}
        )
        self._storage[appointment_id] = updated
        return updated

    def reschedule(
        self,
        appointment_id: uuid.UUID,
        new_start_time: datetime,
        new_end_time: datetime,
        status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    ) -> Optional[AppointmentModel]:
        appt = self._storage.get(appointment_id)
        if not appt:
            return None
        updated = appt.model_copy(
            update={
                "start_time": new_start_time,
                "end_time": new_end_time,
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._storage[appointment_id] = updated
        return updated
