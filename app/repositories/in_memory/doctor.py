"""In-memory Doctor repository implementation."""

import uuid
from typing import Dict, List, Optional

from app.models import DoctorModel, SpecialtyModel
from app.repositories.base import DoctorRepository, SpecialtyRepository


class InMemoryDoctorRepository(DoctorRepository):
    def __init__(self) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, DoctorModel] = {}
        self._doctor_specialties: Dict[uuid.UUID, List[uuid.UUID]] = {}
        self._specialty_repo: Optional[SpecialtyRepository] = None

    def set_specialty_repo(self, repo: SpecialtyRepository) -> None:
        """Wire in the specialty repository for join lookups."""
        self._specialty_repo = repo

    def create(self, doctor: DoctorModel) -> DoctorModel:
        self._storage[doctor.id] = doctor
        self._doctor_specialties[doctor.id] = []
        return doctor

    def get_by_id(self, doctor_id: uuid.UUID) -> Optional[DoctorModel]:
        return self._storage.get(doctor_id)

    def list_active(self) -> List[DoctorModel]:
        return [doc for doc in self._storage.values() if doc.is_active]

    def search(
        self,
        specialty: Optional[str] = None,
        doctor_name: Optional[str] = None,
        location: Optional[str] = None,
        clinic_name: Optional[str] = None,
        is_active: Optional[bool] = True,
        limit: int = 10,
    ) -> List[DoctorModel]:
        results = []
        for doc in self._storage.values():
            if is_active is not None and doc.is_active != is_active:
                continue
            if doctor_name and doctor_name.lower() not in doc.name.lower():
                continue
            if location and (
                not doc.location or location.lower() not in doc.location.lower()
            ):
                continue
            if clinic_name and (
                not doc.clinic_name
                or clinic_name.lower() not in doc.clinic_name.lower()
            ):
                continue
            if specialty:
                doc_specs = self.get_specialties(doc.id)
                if not any(
                    specialty.lower() in spec.name.lower() for spec in doc_specs
                ):
                    continue
            results.append(doc)
            if len(results) >= limit:
                break
        return results

    def add_specialty(self, doctor_id: uuid.UUID, specialty_id: uuid.UUID) -> None:
        if doctor_id not in self._storage:
            raise ValueError(f"Doctor with ID '{doctor_id}' does not exist.")
        if doctor_id not in self._doctor_specialties:
            self._doctor_specialties[doctor_id] = []
        if specialty_id not in self._doctor_specialties[doctor_id]:
            self._doctor_specialties[doctor_id].append(specialty_id)

    def get_specialties(self, doctor_id: uuid.UUID) -> List[SpecialtyModel]:
        if doctor_id not in self._storage or not self._specialty_repo:
            return []
        specialty_ids = self._doctor_specialties.get(doctor_id, [])
        result = []
        for sid in specialty_ids:
            spec = self._specialty_repo.get_by_id(sid)
            if spec:
                result.append(spec)
        return result
