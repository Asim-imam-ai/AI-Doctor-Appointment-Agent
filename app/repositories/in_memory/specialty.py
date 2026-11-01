"""In-memory Specialty repository implementation."""

import uuid
from typing import Dict, List, Optional

from app.models import SpecialtyModel
from app.repositories.base import SpecialtyRepository


class InMemorySpecialtyRepository(SpecialtyRepository):
    def __init__(self) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, SpecialtyModel] = {}

    def create(self, specialty: SpecialtyModel) -> SpecialtyModel:
        if any(
            s.name.lower() == specialty.name.lower() for s in self._storage.values()
        ):
            raise ValueError(f"Specialty '{specialty.name}' already exists.")
        self._storage[specialty.id] = specialty
        return specialty

    def get_by_id(self, specialty_id: uuid.UUID) -> Optional[SpecialtyModel]:
        return self._storage.get(specialty_id)

    def get_by_name(self, name: str) -> Optional[SpecialtyModel]:
        for spec in self._storage.values():
            if spec.name.lower() == name.lower():
                return spec
        return None

    def list_all(self) -> List[SpecialtyModel]:
        return list(self._storage.values())
