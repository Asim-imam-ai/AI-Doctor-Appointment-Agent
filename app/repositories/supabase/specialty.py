"""Supabase Specialty repository implementation."""

import uuid
from typing import List, Optional

from app.models import SpecialtyModel
from app.repositories.base import SpecialtyRepository


class SupabaseSpecialtyRepository(SpecialtyRepository):
    def create(self, specialty: SpecialtyModel) -> SpecialtyModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = specialty.model_dump(mode="json")
        res = self.client.table("specialties").insert(data).execute()
        return SpecialtyModel.model_validate(res.data[0])

    def get_by_id(self, specialty_id: uuid.UUID) -> Optional[SpecialtyModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("specialties")
            .select("*")
            .eq("id", str(specialty_id))
            .execute()
        )
        if not res.data:
            return None
        return SpecialtyModel.model_validate(res.data[0])

    def get_by_name(self, name: str) -> Optional[SpecialtyModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = self.client.table("specialties").select("*").eq("name", name).execute()
        if not res.data:
            return None
        return SpecialtyModel.model_validate(res.data[0])

    def list_all(self) -> List[SpecialtyModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = self.client.table("specialties").select("*").execute()
        return [SpecialtyModel.model_validate(item) for item in res.data]
