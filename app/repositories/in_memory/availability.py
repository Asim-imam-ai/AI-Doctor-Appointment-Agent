"""In-memory Availability repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models import AvailabilityStatus, DoctorAvailabilityModel
from app.repositories.base import AvailabilityRepository, DoctorRepository


class InMemoryAvailabilityRepository(AvailabilityRepository):
    def __init__(self, doctor_repo: Optional[DoctorRepository] = None) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, DoctorAvailabilityModel] = {}
        self.doctor_repo = doctor_repo

    def create(self, availability: DoctorAvailabilityModel) -> DoctorAvailabilityModel:
        if self.doctor_repo and not self.doctor_repo.get_by_id(availability.doctor_id):
            raise ValueError(f"Doctor ID '{availability.doctor_id}' does not exist.")
        self._storage[availability.id] = availability
        return availability

    def get_by_id(
        self, availability_id: uuid.UUID
    ) -> Optional[DoctorAvailabilityModel]:
        return self._storage.get(availability_id)

    def get_available_slots(
        self, doctor_id: uuid.UUID
    ) -> List[DoctorAvailabilityModel]:
        return [
            slot
            for slot in self._storage.values()
            if slot.doctor_id == doctor_id
            and slot.status == AvailabilityStatus.AVAILABLE
        ]

    def get_by_doctor(self, doctor_id: uuid.UUID) -> List[DoctorAvailabilityModel]:
        return [slot for slot in self._storage.values() if slot.doctor_id == doctor_id]

    def search_available_slots(
        self,
        doctor_id: Optional[uuid.UUID] = None,
        start_after: Optional[datetime] = None,
        end_before: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[DoctorAvailabilityModel]:
        matching = []
        for slot in self._storage.values():
            if slot.status != AvailabilityStatus.AVAILABLE:
                continue
            if doctor_id and slot.doctor_id != doctor_id:
                continue
            if start_after and slot.start_time < start_after:
                continue
            if end_before and slot.end_time > end_before:
                continue
            matching.append(slot)
        matching.sort(key=lambda s: s.start_time)
        return matching[:limit]

    def update_status(
        self, availability_id: uuid.UUID, status: AvailabilityStatus
    ) -> Optional[DoctorAvailabilityModel]:
        slot = self._storage.get(availability_id)
        if not slot:
            return None
        updated = slot.model_copy(
            update={"status": status, "updated_at": datetime.now(timezone.utc)}
        )
        self._storage[availability_id] = updated
        return updated
