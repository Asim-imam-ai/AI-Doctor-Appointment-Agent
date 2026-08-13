"""Unit and integration tests for domain models, repositories, and services."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    AppointmentModel,
    AppointmentStatus,
    DoctorModel,
    PatientModel,
    SpecialtyModel,
)
from app.repositories.in_memory import (
    InMemoryAppointmentRepository,
    InMemoryAvailabilityRepository,
    InMemoryDoctorRepository,
    InMemoryPatientRepository,
    InMemorySpecialtyRepository,
)
from app.services import (
    AppointmentService,
    DoctorService,
    PatientService,
)

# ---------------------------------------------------------------------------
# Domain Model Tests
# ---------------------------------------------------------------------------


def test_patient_model_creation():
    patient = PatientModel(
        name="Jane Doe",
        email="jane@example.com",
        timezone="America/New_York",
    )
    assert isinstance(patient.id, uuid.UUID)
    assert patient.name == "Jane Doe"
    assert patient.email == "jane@example.com"
    assert patient.timezone == "America/New_York"


def test_doctor_model_defaults():
    doctor = DoctorModel(name="Dr. Smith")
    assert isinstance(doctor.id, uuid.UUID)
    assert doctor.consultation_duration == 30
    assert doctor.is_active is True


def test_appointment_model_status_enum():
    now = datetime.now(timezone.utc)
    appt = AppointmentModel(
        patient_id=uuid.uuid4(),
        doctor_id=uuid.uuid4(),
        start_time=now,
        end_time=now + timedelta(minutes=30),
        status=AppointmentStatus.PENDING,
    )
    assert appt.status == AppointmentStatus.PENDING


# ---------------------------------------------------------------------------
# Repository Tests
# ---------------------------------------------------------------------------


def test_patient_repository_crud():
    repo = InMemoryPatientRepository()
    patient = PatientModel(name="Alice", email="alice@example.com")
    created = repo.create(patient)
    assert created.id == patient.id

    fetched = repo.get_by_id(patient.id)
    assert fetched is not None
    assert fetched.name == "Alice"

    by_email = repo.get_by_email("alice@example.com")
    assert by_email is not None
    assert by_email.id == patient.id


def test_patient_repository_duplicate_email():
    repo = InMemoryPatientRepository()
    p1 = PatientModel(name="Alice", email="alice@example.com")
    p2 = PatientModel(name="Bob", email="alice@example.com")
    repo.create(p1)
    with pytest.raises(ValueError, match="already exists"):
        repo.create(p2)


def test_doctor_and_specialty_repository():
    doc_repo = InMemoryDoctorRepository()
    spec_repo = InMemorySpecialtyRepository()
    doc_repo.set_specialty_repo(spec_repo)

    doctor = DoctorModel(name="Dr. Gregory House")
    doc_repo.create(doctor)

    specialty = SpecialtyModel(name="Diagnostics")
    spec_repo.create(specialty)

    doc_repo.add_specialty(doctor.id, specialty.id)
    specs = doc_repo.get_specialties(doctor.id)
    assert len(specs) == 1
    assert specs[0].name == "Diagnostics"


def test_appointment_repository_conflict():
    p_repo = InMemoryPatientRepository()
    d_repo = InMemoryDoctorRepository()
    appt_repo = InMemoryAppointmentRepository(patient_repo=p_repo, doctor_repo=d_repo)

    patient = p_repo.create(PatientModel(name="Patient 1", email="p1@example.com"))
    doctor = d_repo.create(DoctorModel(name="Dr. Smith"))

    now = datetime.now(timezone.utc) + timedelta(days=1)
    t1 = now
    t2 = now + timedelta(minutes=30)

    appt1 = AppointmentModel(
        patient_id=patient.id,
        doctor_id=doctor.id,
        start_time=t1,
        end_time=t2,
        status=AppointmentStatus.CONFIRMED,
    )
    appt_repo.create(appt1)

    # Overlapping appointment for same doctor
    appt2 = AppointmentModel(
        patient_id=patient.id,
        doctor_id=doctor.id,
        start_time=t1 + timedelta(minutes=15),
        end_time=t2 + timedelta(minutes=15),
        status=AppointmentStatus.PENDING,
    )
    with pytest.raises(ValueError, match="Appointment time conflict"):
        appt_repo.create(appt2)


# ---------------------------------------------------------------------------
# Service Business Rules Tests
# ---------------------------------------------------------------------------


def test_patient_service():
    service = PatientService(repository=InMemoryPatientRepository())
    patient = service.register_patient(name="John Doe", email="john@example.com")
    assert patient.name == "John Doe"

    fetched = service.get_patient(patient.id)
    assert fetched is not None
    assert fetched.email == "john@example.com"


def test_doctor_service_registration_and_search():
    doc_repo = InMemoryDoctorRepository()
    spec_repo = InMemorySpecialtyRepository()
    doc_repo.set_specialty_repo(spec_repo)

    service = DoctorService(doctor_repo=doc_repo, specialty_repo=spec_repo)
    doctor = service.register_doctor(name="Dr. Sarah Connor")

    results = service.search_doctors("Sarah")
    assert len(results) == 1
    assert results[0].id == doctor.id

    spec = service.add_specialty_to_doctor(doctor.id, "Cardiology")
    assert spec.name == "Cardiology"

    specs = service.get_doctor_specialties(doctor.id)
    assert len(specs) == 1
    assert specs[0].name == "Cardiology"


def test_appointment_service_validation():
    p_repo = InMemoryPatientRepository()
    d_repo = InMemoryDoctorRepository()
    appt_repo = InMemoryAppointmentRepository(patient_repo=p_repo, doctor_repo=d_repo)
    avail_repo = InMemoryAvailabilityRepository(doctor_repo=d_repo)

    patient = p_repo.create(PatientModel(name="Patient", email="patient@example.com"))
    doctor = d_repo.create(DoctorModel(name="Active Doctor", is_active=True))

    service = AppointmentService(
        appointment_repo=appt_repo,
        patient_repo=p_repo,
        doctor_repo=d_repo,
        availability_repo=avail_repo,
    )

    now = datetime.now(timezone.utc)
    future_start = now + timedelta(days=1)
    future_end = future_start + timedelta(minutes=30)

    # Test start >= end
    with pytest.raises(ValueError, match="must be strictly before"):
        service.create_appointment(patient.id, doctor.id, future_end, future_start)

    # Test past datetime
    past_start = now - timedelta(days=1)
    past_end = past_start + timedelta(minutes=30)
    with pytest.raises(ValueError, match="in the past"):
        service.create_appointment(patient.id, doctor.id, past_start, past_end)

    # Test non-existent patient
    with pytest.raises(ValueError, match="Patient with ID"):
        service.create_appointment(uuid.uuid4(), doctor.id, future_start, future_end)

    # Test inactive doctor
    inactive_doctor = d_repo.create(
        DoctorModel(name="Inactive Doctor", is_active=False)
    )
    with pytest.raises(ValueError, match="not currently active"):
        service.create_appointment(
            patient.id, inactive_doctor.id, future_start, future_end
        )

    # Test valid appointment creation
    appt = service.create_appointment(
        patient.id, doctor.id, future_start, future_end, reason="Checkup"
    )
    assert appt.status == AppointmentStatus.PENDING

    # Test status update
    updated = service.update_appointment_status(appt.id, AppointmentStatus.CONFIRMED)
    assert updated is not None
    assert updated.status == AppointmentStatus.CONFIRMED
