"""Supabase Doctor repository implementation."""

import uuid
from typing import List, Optional

from app.domain.doctors.repository import DoctorRepository
from app.domain.models import DoctorModel, SpecialtyModel
from app.infrastructure.repositories.supabase.base import SupabaseRepository


class SupabaseDoctorRepository(SupabaseRepository, DoctorRepository):
    def create(self, doctor: DoctorModel) -> DoctorModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = doctor.model_dump(mode="json")
        res = self.client.table("doctors").insert(data).execute()
        return DoctorModel.model_validate(res.data[0])

    def get_by_id(self, doctor_id: uuid.UUID) -> Optional[DoctorModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctors").select("*").eq("id", str(doctor_id)).execute()
        )
        if not res.data:
            return None
        return DoctorModel.model_validate(res.data[0])

    def list_active(self) -> List[DoctorModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = self.client.table("doctors").select("*").eq("is_active", True).execute()
        return [DoctorModel.model_validate(item) for item in res.data]

    def search(
        self,
        specialty: Optional[str] = None,
        doctor_name: Optional[str] = None,
        location: Optional[str] = None,
        clinic_name: Optional[str] = None,
        is_active: Optional[bool] = True,
        limit: int = 10,
    ) -> List[DoctorModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        query = self.client.table("doctors").select("*")
        if is_active is not None:
            query = query.eq("is_active", is_active)
        if doctor_name:
            query = query.ilike("name", f"%{doctor_name}%")
        if location:
            query = query.ilike("location", f"%{location}%")
        if clinic_name:
            query = query.ilike("clinic_name", f"%{clinic_name}%")
        query = query.limit(limit)
        res = query.execute()
        doctors = [DoctorModel.model_validate(item) for item in res.data]
        if specialty:
            filtered = []
            for doc in doctors:
                specs = self.get_specialties(doc.id)
                if any(specialty.lower() in s.name.lower() for s in specs):
                    filtered.append(doc)
            return filtered
        return doctors

    def add_specialty(self, doctor_id: uuid.UUID, specialty_id: uuid.UUID) -> None:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        self.client.table("doctor_specialties").insert(
            {"doctor_id": str(doctor_id), "specialty_id": str(specialty_id)}
        ).execute()

    def get_specialties(self, doctor_id: uuid.UUID) -> List[SpecialtyModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("doctor_specialties")
            .select("specialties(*)")
            .eq("doctor_id", str(doctor_id))
            .execute()
        )
        specialties = []
        for item in res.data:
            if "specialties" in item and item["specialties"]:
                specialties.append(SpecialtyModel.model_validate(item["specialties"]))
        return specialties
