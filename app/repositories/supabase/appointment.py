"""Supabase Appointment repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.models import AppointmentModel, AppointmentStatus
from app.repositories.base import AppointmentRepository


class SupabaseAppointmentRepository(AppointmentRepository):
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
