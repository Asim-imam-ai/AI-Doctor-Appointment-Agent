"""Supabase Availability repository implementation."""

import uuid
from datetime import datetime
from typing import List, Optional

from app.models import AvailabilityStatus, DoctorAvailabilityModel
from app.repositories.base import AvailabilityRepository


class SupabaseAvailabilityRepository(AvailabilityRepository):
    def create(self, availability: DoctorAvailabilityModel) -> DoctorAvailabilityModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = availability.model_dump(mode="json")
        res = self.client.table("doctor_availability").insert(data).execute()
        return DoctorAvailabilityModel.model_validate(res.data[0])

    def get_by_id(
        self, availability_id: uuid.UUID
    ) -> Optional[DoctorAvailabilityModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctor_availability")
            .select("*")
            .eq("id", str(availability_id))
            .execute()
        )
        if not res.data:
            return None
        return DoctorAvailabilityModel.model_validate(res.data[0])

    def get_available_slots(
        self, doctor_id: uuid.UUID
    ) -> List[DoctorAvailabilityModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctor_availability")
            .select("*")
            .eq("doctor_id", str(doctor_id))
            .eq("status", "AVAILABLE")
            .execute()
        )
        return [DoctorAvailabilityModel.model_validate(item) for item in res.data]

    def get_by_doctor(self, doctor_id: uuid.UUID) -> List[DoctorAvailabilityModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctor_availability")
            .select("*")
            .eq("doctor_id", str(doctor_id))
            .execute()
        )
        return [DoctorAvailabilityModel.model_validate(item) for item in res.data]

    def search_available_slots(
        self,
        doctor_id: Optional[uuid.UUID] = None,
        start_after: Optional[datetime] = None,
        end_before: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[DoctorAvailabilityModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        query = (
            self.client.table("doctor_availability")
            .select("*")
            .eq("status", "AVAILABLE")
        )
        if doctor_id:
            query = query.eq("doctor_id", str(doctor_id))
        if start_after:
            query = query.gte("start_time", start_after.isoformat())
        if end_before:
            query = query.lte("end_time", end_before.isoformat())
        query = query.order("start_time", desc=False).limit(limit)
        res = query.execute()
        return [DoctorAvailabilityModel.model_validate(item) for item in res.data]

    def update_status(
        self, availability_id: uuid.UUID, status: AvailabilityStatus
    ) -> Optional[DoctorAvailabilityModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctor_availability")
            .update({"status": status.value})
            .eq("id", str(availability_id))
            .execute()
        )
        if not res.data:
            return None
        return DoctorAvailabilityModel.model_validate(res.data[0])
