"""Patient business logic service."""

import uuid
from typing import Optional

from app.models import PatientModel
from app.repositories import get_patient_repository
from app.repositories.base import PatientRepository


class PatientService:
    def __init__(self, repository: Optional[PatientRepository] = None):
        self.repository = repository or get_patient_repository()

    def register_patient(
        self,
        name: str,
        email: str,
        phone: Optional[str] = None,
        external_user_id: Optional[str] = None,
        timezone: str = "UTC",
    ) -> PatientModel:
        patient = PatientModel(
            name=name,
            email=email,
            phone=phone,
            external_user_id=external_user_id,
            timezone=timezone,
        )
        return self.repository.create(patient)

    def get_patient(self, patient_id: uuid.UUID) -> Optional[PatientModel]:
        return self.repository.get_by_id(patient_id)

    def get_by_email(self, email: str) -> Optional[PatientModel]:
        return self.repository.get_by_email(email)
