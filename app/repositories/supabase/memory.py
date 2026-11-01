"""Supabase Memory repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.models import MemoryItemModel
from app.repositories.base import MemoryRepository


class SupabaseMemoryRepository(MemoryRepository):
    def create_or_update(self, item: MemoryItemModel) -> MemoryItemModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = item.model_dump(mode="json")
        res = (
            self.client.table("user_memories")
            .upsert(data, on_conflict="patient_id,key")
            .execute()
        )
        return MemoryItemModel.model_validate(res.data[0])

    def get_by_id(self, memory_id: uuid.UUID) -> Optional[MemoryItemModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("user_memories")
            .select("*")
            .eq("id", str(memory_id))
            .execute()
        )
        if not res.data:
            return None
        return MemoryItemModel.model_validate(res.data[0])

    def get_by_key(self, patient_id: uuid.UUID, key: str) -> Optional[MemoryItemModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("user_memories")
            .select("*")
            .eq("patient_id", str(patient_id))
            .eq("key", key)
            .eq("is_active", True)
            .execute()
        )
        if not res.data:
            return None
        return MemoryItemModel.model_validate(res.data[0])

    def list_for_patient(
        self, patient_id: uuid.UUID, active_only: bool = True
    ) -> List[MemoryItemModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        query = (
            self.client.table("user_memories")
            .select("*")
            .eq("patient_id", str(patient_id))
        )
        if active_only:
            query = query.eq("is_active", True)
        res = query.execute()
        return [MemoryItemModel.model_validate(item) for item in res.data]

    def delete_memory(self, memory_id: uuid.UUID) -> bool:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("user_memories")
            .update(
                {
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", str(memory_id))
            .execute()
        )
        return bool(res.data)

    def delete_by_key(self, patient_id: uuid.UUID, key: str) -> bool:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("user_memories")
            .update(
                {
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("patient_id", str(patient_id))
            .eq("key", key)
            .execute()
        )
        return bool(res.data)
