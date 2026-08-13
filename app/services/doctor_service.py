"""Doctor business logic service."""

import uuid
from typing import List, Optional

from app.models import DoctorModel, SpecialtyModel
from app.repositories import get_doctor_repository, get_specialty_repository
from app.repositories.base import DoctorRepository, SpecialtyRepository


class DoctorService:
    def __init__(
        self,
        doctor_repo: Optional[DoctorRepository] = None,
        specialty_repo: Optional[SpecialtyRepository] = None,
    ):
        self.doctor_repo = doctor_repo or get_doctor_repository()
        self.specialty_repo = specialty_repo or get_specialty_repository()

    def register_doctor(
        self,
        name: str,
        bio: Optional[str] = None,
        clinic_name: Optional[str] = None,
        location: Optional[str] = None,
        consultation_duration: int = 30,
    ) -> DoctorModel:
        doctor = DoctorModel(
            name=name,
            bio=bio,
            clinic_name=clinic_name,
            location=location,
            consultation_duration=consultation_duration,
        )
        return self.doctor_repo.create(doctor)

    def get_doctor(self, doctor_id: uuid.UUID) -> Optional[DoctorModel]:
        return self.doctor_repo.get_by_id(doctor_id)

    def list_active_doctors(self) -> List[DoctorModel]:
        return self.doctor_repo.list_active()

    def search_doctors(
        self,
        specialty: Optional[str] = None,
        doctor_name: Optional[str] = None,
        location: Optional[str] = None,
        clinic_name: Optional[str] = None,
        is_active: Optional[bool] = True,
        limit: int = 10,
    ) -> List[DoctorModel]:
        return self.doctor_repo.search(
            specialty=specialty,
            doctor_name=doctor_name,
            location=location,
            clinic_name=clinic_name,
            is_active=is_active,
            limit=limit,
        )

    def search_by_name(self, query: str) -> List[DoctorModel]:
        return self.doctor_repo.search_by_name(query)

    def add_specialty_to_doctor(
        self, doctor_id: uuid.UUID, specialty_name: str
    ) -> SpecialtyModel:
        doctor = self.get_doctor(doctor_id)
        if not doctor:
            raise ValueError(f"Doctor with ID '{doctor_id}' does not exist.")

        specialty = self.specialty_repo.get_by_name(specialty_name)
        if not specialty:
            specialty = self.specialty_repo.create(SpecialtyModel(name=specialty_name))

        self.doctor_repo.add_specialty(doctor_id, specialty.id)
        return specialty

    def get_doctor_specialties(self, doctor_id: uuid.UUID) -> List[SpecialtyModel]:
        return self.doctor_repo.get_specialties(doctor_id)
