"""Repository factory / central dependency retriever."""

from typing import Optional

from app.infrastructure.supabase.client import get_supabase_client
from app.repositories.base import (
    AppointmentRepository,
    AvailabilityRepository,
    DoctorRepository,
    PatientRepository,
    SpecialtyRepository,
)
from app.repositories.in_memory import (
    InMemoryAppointmentRepository,
    InMemoryAvailabilityRepository,
    InMemoryDoctorRepository,
    InMemoryPatientRepository,
    InMemorySpecialtyRepository,
)
from app.repositories.supabase import (
    SupabaseAppointmentRepository,
    SupabaseAvailabilityRepository,
    SupabaseDoctorRepository,
    SupabasePatientRepository,
    SupabaseSpecialtyRepository,
)

# Global fallback singletons for in-memory mode when Supabase credentials are missing
_in_memory_patient_repo = InMemoryPatientRepository()
_in_memory_specialty_repo = InMemorySpecialtyRepository()
_in_memory_doctor_repo = InMemoryDoctorRepository()
_in_memory_doctor_repo.set_specialty_repo(_in_memory_specialty_repo)
_in_memory_availability_repo = InMemoryAvailabilityRepository(_in_memory_doctor_repo)
_in_memory_appointment_repo = InMemoryAppointmentRepository(
    patient_repo=_in_memory_patient_repo, doctor_repo=_in_memory_doctor_repo
)


def get_patient_repository(client: Optional[object] = None) -> PatientRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabasePatientRepository(supabase_client)
    return _in_memory_patient_repo


def get_doctor_repository(client: Optional[object] = None) -> DoctorRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseDoctorRepository(supabase_client)
    return _in_memory_doctor_repo


def get_specialty_repository(client: Optional[object] = None) -> SpecialtyRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseSpecialtyRepository(supabase_client)
    return _in_memory_specialty_repo


def get_availability_repository(
    client: Optional[object] = None,
) -> AvailabilityRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseAvailabilityRepository(supabase_client)
    return _in_memory_availability_repo


def get_appointment_repository(
    client: Optional[object] = None,
) -> AppointmentRepository:
    supabase_client = client or get_supabase_client()
    if supabase_client is not None:
        return SupabaseAppointmentRepository(supabase_client)
    return _in_memory_appointment_repo
