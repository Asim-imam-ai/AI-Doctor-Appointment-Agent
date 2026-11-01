"""Appointment persistence contract."""

import uuid
from datetime import datetime
from typing import Protocol

from app.domain.models import AppointmentModel, AppointmentStatus


class AppointmentRepository(Protocol):
    def create(self, appointment: AppointmentModel) -> AppointmentModel: ...
    def get_by_id(self, appointment_id: uuid.UUID) -> AppointmentModel | None: ...
    def list_for_patient(self, patient_id: uuid.UUID) -> list[AppointmentModel]: ...
    def list_for_doctor(self, doctor_id: uuid.UUID) -> list[AppointmentModel]: ...
    def update_status(
        self, appointment_id: uuid.UUID, status: AppointmentStatus
    ) -> AppointmentModel | None: ...
    def reschedule(
        self,
        appointment_id: uuid.UUID,
        new_start_time: datetime,
        new_end_time: datetime,
        status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    ) -> AppointmentModel | None: ...
    def book_slot(
        self,
        patient_id: uuid.UUID,
        doctor_id: uuid.UUID,
        slot_id: uuid.UUID,
        reason: str | None,
    ) -> AppointmentModel: ...
    def cancel_atomically(
        self,
        appointment_id: uuid.UUID,
        patient_id: uuid.UUID,
        cancellation_window_minutes: int,
    ) -> AppointmentModel: ...
    def reschedule_atomically(
        self, appointment_id: uuid.UUID, patient_id: uuid.UUID, slot_id: uuid.UUID
    ) -> AppointmentModel: ...
