"""InMemory implementation of repository interfaces for testing and fallback."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models import (
    AppointmentModel,
    AppointmentStatus,
    AvailabilityStatus,
    DoctorAvailabilityModel,
    DoctorModel,
    PatientModel,
    SpecialtyModel,
)
from app.repositories.base import (
    AppointmentRepository,
    AvailabilityRepository,
    DoctorRepository,
    PatientRepository,
    SpecialtyRepository,
)


class InMemoryPatientRepository(PatientRepository):
    def __init__(self):
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


class InMemoryDoctorRepository(DoctorRepository):
    def __init__(self):
        super().__init__()
        self._storage: Dict[uuid.UUID, DoctorModel] = {}
        self._doctor_specialties: Dict[uuid.UUID, List[uuid.UUID]] = {}
        self._specialty_repo: Optional[SpecialtyRepository] = None

    def set_specialty_repo(self, repo: SpecialtyRepository):
        self._specialty_repo = repo

    def create(self, doctor: DoctorModel) -> DoctorModel:
        self._storage[doctor.id] = doctor
        self._doctor_specialties[doctor.id] = []
        return doctor

    def get_by_id(self, doctor_id: uuid.UUID) -> Optional[DoctorModel]:
        return self._storage.get(doctor_id)

    def list_active(self) -> List[DoctorModel]:
        return [doc for doc in self._storage.values() if doc.is_active]

    def search_by_name(self, name_query: str) -> List[DoctorModel]:
        query = name_query.lower()
        return [doc for doc in self._storage.values() if query in doc.name.lower()]

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


class InMemorySpecialtyRepository(SpecialtyRepository):
    def __init__(self):
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


class InMemoryAvailabilityRepository(AvailabilityRepository):
    def __init__(self, doctor_repo: Optional[DoctorRepository] = None):
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


class InMemoryAppointmentRepository(AppointmentRepository):
    def __init__(
        self,
        patient_repo: Optional[PatientRepository] = None,
        doctor_repo: Optional[DoctorRepository] = None,
    ):
        super().__init__()
        self._storage: Dict[uuid.UUID, AppointmentModel] = {}
        self.patient_repo = patient_repo
        self.doctor_repo = doctor_repo

    def create(self, appointment: AppointmentModel) -> AppointmentModel:
        if self.patient_repo and not self.patient_repo.get_by_id(
            appointment.patient_id
        ):
            raise ValueError(f"Patient ID '{appointment.patient_id}' does not exist.")
        if self.doctor_repo:
            doctor = self.doctor_repo.get_by_id(appointment.doctor_id)
            if not doctor:
                raise ValueError(f"Doctor ID '{appointment.doctor_id}' does not exist.")
            if not doctor.is_active:
                raise ValueError(f"Doctor '{doctor.name}' is not active.")

        # Double-booking check for same doctor with overlapping non-cancelled
        # or non-expired appointments
        for appt in self._storage.values():
            if appt.doctor_id == appointment.doctor_id and appt.status in (
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
            ):
                # Overlap condition: start1 < end2 AND start2 < end1
                if (
                    appointment.start_time < appt.end_time
                    and appt.start_time < appointment.end_time
                ):
                    raise ValueError(
                        "Appointment time conflict for doctor "
                        f"'{appointment.doctor_id}'"
                    )

        self._storage[appointment.id] = appointment
        return appointment

    def get_by_id(self, appointment_id: uuid.UUID) -> Optional[AppointmentModel]:
        return self._storage.get(appointment_id)

    def list_for_patient(self, patient_id: uuid.UUID) -> List[AppointmentModel]:
        return [
            appt for appt in self._storage.values() if appt.patient_id == patient_id
        ]

    def list_for_doctor(self, doctor_id: uuid.UUID) -> List[AppointmentModel]:
        return [appt for appt in self._storage.values() if appt.doctor_id == doctor_id]

    def update_status(
        self, appointment_id: uuid.UUID, status: AppointmentStatus
    ) -> Optional[AppointmentModel]:
        appt = self._storage.get(appointment_id)
        if not appt:
            return None
        updated_appt = appt.model_copy(
            update={"status": status, "updated_at": datetime.now(timezone.utc)}
        )
        self._storage[appointment_id] = updated_appt
        return updated_appt
