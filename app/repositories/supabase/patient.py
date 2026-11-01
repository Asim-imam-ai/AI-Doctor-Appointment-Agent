"""Supabase Patient repository implementation."""

import uuid
from typing import Optional

from app.models import PatientModel
from app.repositories.base import PatientRepository


class SupabasePatientRepository(PatientRepository):
    def create(self, patient: PatientModel) -> PatientModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = patient.model_dump(mode="json")
        res = self.client.table("patients").insert(data).execute()
        return PatientModel.model_validate(res.data[0])

    def get_by_id(self, patient_id: uuid.UUID) -> Optional[PatientModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("patients")
            .select("*")
            .eq("id", str(patient_id))
            .execute()
        )
        if not res.data:
            return None
        return PatientModel.model_validate(res.data[0])

    def get_by_email(self, email: str) -> Optional[PatientModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = self.client.table("patients").select("*").eq("email", email).execute()
        if not res.data:
            return None
        return PatientModel.model_validate(res.data[0])

    def get_by_external_id(self, external_user_id: str) -> Optional[PatientModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("patients")
            .select("*")
            .eq("external_user_id", external_user_id)
            .execute()
        )
        if not res.data:
            return None
        return PatientModel.model_validate(res.data[0])
