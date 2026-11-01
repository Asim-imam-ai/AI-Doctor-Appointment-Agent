"""Scheduling persistence contract."""

import uuid
from datetime import datetime
from typing import Protocol

from app.domain.models import AvailabilityStatus, DoctorAvailabilityModel


class AvailabilityRepository(Protocol):
    def create(
        self, availability: DoctorAvailabilityModel
    ) -> DoctorAvailabilityModel: ...
    def get_by_id(
        self, availability_id: uuid.UUID
    ) -> DoctorAvailabilityModel | None: ...
    def get_available_slots(
        self, doctor_id: uuid.UUID
    ) -> list[DoctorAvailabilityModel]: ...
    def get_by_doctor(self, doctor_id: uuid.UUID) -> list[DoctorAvailabilityModel]: ...
    def search_available_slots(
        self,
        doctor_id: uuid.UUID | None = None,
        start_after: datetime | None = None,
        end_before: datetime | None = None,
        limit: int = 20,
    ) -> list[DoctorAvailabilityModel]: ...
    def update_status(
        self, availability_id: uuid.UUID, status: AvailabilityStatus
    ) -> DoctorAvailabilityModel | None: ...
