"""Availability business logic service."""

import uuid
from datetime import datetime
from typing import List, Optional

from app.models import AvailabilityStatus, DoctorAvailabilityModel
from app.repositories import get_availability_repository, get_doctor_repository
from app.repositories.base import AvailabilityRepository, DoctorRepository


class AvailabilityService:
    def __init__(
        self,
        availability_repo: Optional[AvailabilityRepository] = None,
        doctor_repo: Optional[DoctorRepository] = None,
    ):
        self.availability_repo = availability_repo or get_availability_repository()
        self.doctor_repo = doctor_repo or get_doctor_repository()

    def add_availability(
        self, doctor_id: uuid.UUID, start_time: datetime, end_time: datetime
    ) -> DoctorAvailabilityModel:
        if start_time >= end_time:
            raise ValueError("start_time must be before end_time")

        doctor = self.doctor_repo.get_by_id(doctor_id)
        if not doctor:
            raise ValueError(f"Doctor with ID '{doctor_id}' does not exist.")
        if not doctor.is_active:
            raise ValueError(f"Doctor '{doctor.name}' is inactive.")

        availability = DoctorAvailabilityModel(
            doctor_id=doctor_id,
            start_time=start_time,
            end_time=end_time,
            status=AvailabilityStatus.AVAILABLE,
        )
        return self.availability_repo.create(availability)

    def get_available_slots(
        self, doctor_id: uuid.UUID
    ) -> List[DoctorAvailabilityModel]:
        return self.availability_repo.get_available_slots(doctor_id)
