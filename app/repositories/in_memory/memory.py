"""In-memory Memory repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models import MemoryItemModel
from app.repositories.base import MemoryRepository


class InMemoryMemoryRepository(MemoryRepository):
    def __init__(self) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, MemoryItemModel] = {}

    def create_or_update(self, item: MemoryItemModel) -> MemoryItemModel:
        existing = self.get_by_key(item.patient_id, item.key)
        if existing:
            updated = existing.model_copy(
                update={
                    "value": item.value,
                    "memory_type": item.memory_type,
                    "source": item.source,
                    "is_active": item.is_active,
                    "expires_at": item.expires_at,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._storage[existing.id] = updated
            return updated
        self._storage[item.id] = item
        return item

    def get_by_id(self, memory_id: uuid.UUID) -> Optional[MemoryItemModel]:
        return self._storage.get(memory_id)

    def get_by_key(self, patient_id: uuid.UUID, key: str) -> Optional[MemoryItemModel]:
        for m in self._storage.values():
            if m.patient_id == patient_id and m.key == key and m.is_active:
                return m
        return None

    def list_for_patient(
        self, patient_id: uuid.UUID, active_only: bool = True
    ) -> List[MemoryItemModel]:
        now_utc = datetime.now(timezone.utc)
        items = []
        for m in self._storage.values():
            if m.patient_id != patient_id:
                continue
            if active_only and not m.is_active:
                continue
            if (
                active_only
                and m.expires_at is not None
                and m.expires_at.tzinfo is not None
                and m.expires_at < now_utc
            ):
                continue
            items.append(m)
        return items

    def delete_memory(self, memory_id: uuid.UUID) -> bool:
        m = self._storage.get(memory_id)
        if not m:
            return False
        updated = m.model_copy(
            update={"is_active": False, "updated_at": datetime.now(timezone.utc)}
        )
        self._storage[memory_id] = updated
        return True

    def delete_by_key(self, patient_id: uuid.UUID, key: str) -> bool:
        m = self.get_by_key(patient_id, key)
        if not m:
            return False
        return self.delete_memory(m.id)
