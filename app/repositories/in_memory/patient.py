"""In-memory Patient repository implementation."""

import uuid
from typing import Dict, Optional

from app.models import PatientModel
from app.repositories.base import PatientRepository


class InMemoryPatientRepository(PatientRepository):
    def __init__(self) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, PatientModel] = {}

    def create(self, patient: PatientModel) -> PatientModel:
        if any(p.email == patient.email for p in self._storage.values()):
            raise ValueError(f"Patient with email '{patient.email}' already exists.")
        if patient.external_user_id and any(
            p.external_user_id == patient.external_user_id
            for p in self._storage.values()
        ):
            raise ValueError(
                f"Patient with external_user_id "
                f"'{patient.external_user_id}' already exists."
            )
        self._storage[patient.id] = patient
        return patient

    def get_by_id(self, patient_id: uuid.UUID) -> Optional[PatientModel]:
        return self._storage.get(patient_id)

    def get_by_email(self, email: str) -> Optional[PatientModel]:
        for patient in self._storage.values():
            if patient.email.lower() == email.lower():
                return patient
        return None

    def get_by_external_id(self, external_user_id: str) -> Optional[PatientModel]:
        for patient in self._storage.values():
            if patient.external_user_id == external_user_id:
                return patient
        return None
