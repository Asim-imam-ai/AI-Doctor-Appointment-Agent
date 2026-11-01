"""Supabase Appointment repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.appointments.repository import AppointmentRepository
from app.domain.models import AppointmentModel, AppointmentStatus
from app.infrastructure.db.transactions import execute_postgres_transaction
from app.infrastructure.repositories.supabase.base import SupabaseRepository


class SupabaseAppointmentRepository(SupabaseRepository, AppointmentRepository):
    def _atomic_appointment(self, function: str, params: dict) -> AppointmentModel:
        result = execute_postgres_transaction(self.client, function, params)
        if result.get("error"):
            raise ValueError(str(result["error"]))
        appointment = result.get("appointment", result)
        if not isinstance(appointment, dict):
            raise RuntimeError(f"{function} did not return an appointment.")
        return AppointmentModel.model_validate(appointment)

    def book_slot(
        self,
        patient_id: uuid.UUID,
        doctor_id: uuid.UUID,
        slot_id: uuid.UUID,
        reason: str | None,
    ) -> AppointmentModel:
        return self._atomic_appointment(
            "book_appointment_slot",
            {
                "p_patient_id": str(patient_id),
                "p_doctor_id": str(doctor_id),
                "p_slot_id": str(slot_id),
                "p_reason": reason,
            },
        )

    def cancel_atomically(
        self,
        appointment_id: uuid.UUID,
        patient_id: uuid.UUID,
        cancellation_window_minutes: int,
    ) -> AppointmentModel:
        return self._atomic_appointment(
            "cancel_appointment_atomic",
            {
                "p_appointment_id": str(appointment_id),
                "p_patient_id": str(patient_id),
                "p_cancellation_window_minutes": cancellation_window_minutes,
            },
        )

    def reschedule_atomically(
        self,
        appointment_id: uuid.UUID,
        patient_id: uuid.UUID,
        slot_id: uuid.UUID,
    ) -> AppointmentModel:
        return self._atomic_appointment(
            "reschedule_appointment_atomic",
            {
                "p_appointment_id": str(appointment_id),
                "p_patient_id": str(patient_id),
                "p_new_slot_id": str(slot_id),
            },
        )

    def create(self, appointment: AppointmentModel) -> AppointmentModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = appointment.model_dump(mode="json")
        res = self.client.table("appointments").insert(data).execute()
        return AppointmentModel.model_validate(res.data[0])

    def get_by_id(self, appointment_id: uuid.UUID) -> Optional[AppointmentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("appointments")
            .select("*")
            .eq("id", str(appointment_id))
            .execute()
        )
        if not res.data:
            return None
        return AppointmentModel.model_validate(res.data[0])

    def list_for_patient(self, patient_id: uuid.UUID) -> List[AppointmentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("appointments")
            .select("*")
            .eq("patient_id", str(patient_id))
            .execute()
        )
        return [AppointmentModel.model_validate(item) for item in res.data]

    def list_for_doctor(self, doctor_id: uuid.UUID) -> List[AppointmentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("appointments")
            .select("*")
            .eq("doctor_id", str(doctor_id))
            .execute()
        )
        return [AppointmentModel.model_validate(item) for item in res.data]

    def update_status(
        self, appointment_id: uuid.UUID, status: AppointmentStatus
    ) -> Optional[AppointmentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("appointments")
            .update({"status": status.value})
            .eq("id", str(appointment_id))
            .execute()
        )
        if not res.data:
            return None
        return AppointmentModel.model_validate(res.data[0])

    def reschedule(
        self,
        appointment_id: uuid.UUID,
        new_start_time: datetime,
        new_end_time: datetime,
        status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    ) -> Optional[AppointmentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("appointments")
            .update(
                {
                    "start_time": new_start_time.isoformat(),
                    "end_time": new_end_time.isoformat(),
                    "status": status.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", str(appointment_id))
            .execute()
        )
        if not res.data:
            return None
        return AppointmentModel.model_validate(res.data[0])
