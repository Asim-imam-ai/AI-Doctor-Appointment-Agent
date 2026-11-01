"""Domain service contract tests using isolated mocks, never production fallbacks."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from app.domain import AppointmentService, DoctorService, PatientService
from app.domain.models import (
    AppointmentModel,
    AppointmentStatus,
    DoctorModel,
    PatientModel,
    SpecialtyModel,
)


def test_models_validate_identity_and_appointment_order():
    patient = PatientModel(name="Jane Doe", email="jane@example.com")
    now = datetime.now(timezone.utc)
    appointment = AppointmentModel(
        patient_id=patient.id,
        doctor_id=uuid.uuid4(),
        start_time=now,
        end_time=now + timedelta(minutes=30),
        status=AppointmentStatus.PENDING,
    )
    assert patient.id and appointment.patient_id == patient.id
    assert appointment.status is AppointmentStatus.PENDING


def test_patient_service_delegates_create_and_external_identity_lookup():
    repository = Mock()
    patient = PatientModel(name="A", email="a@example.com", external_user_id="auth-1")
    repository.create.return_value = patient
    repository.get_by_external_id.return_value = patient
    service = PatientService(repository)

    assert (
        service.register_patient("A", "a@example.com", external_user_id="auth-1")
        == patient
    )
    assert service.get_by_external_id("auth-1") == patient
    repository.create.assert_called_once()
    repository.get_by_external_id.assert_called_once_with("auth-1")


def test_doctor_service_passes_search_filters_to_repository():
    doctors = Mock()
    specialties = Mock()
    expected = [DoctorModel(name="Dr. Chen")]
    doctors.search.return_value = expected
    service = DoctorService(doctors, specialties)

    assert service.search_doctors(specialty="Cardiology", location="Lahore") == expected
    doctors.search.assert_called_once_with(
        specialty="Cardiology",
        doctor_name=None,
        location="Lahore",
        clinic_name=None,
        is_active=True,
        limit=10,
    )


def test_appointment_atomic_booking_validates_profiles_before_repository_call():
    appointment_repo = Mock()
    patient_repo = Mock()
    doctor_repo = Mock()
    availability_repo = Mock()
    patient_id, doctor_id, slot_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    patient_repo.get_by_id.return_value = PatientModel(
        id=patient_id, name="A", email="a@example.com"
    )
    doctor_repo.get_by_id.return_value = DoctorModel(id=doctor_id, name="Dr. B")
    expected = AppointmentModel(
        patient_id=patient_id,
        doctor_id=doctor_id,
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        end_time=datetime.now(timezone.utc) + timedelta(days=1, minutes=30),
    )
    appointment_repo.book_slot.return_value = expected
    service = AppointmentService(
        appointment_repo, patient_repo, doctor_repo, availability_repo
    )

    result = service.atomic_create_appointment_and_update_slot(
        patient_id,
        doctor_id,
        slot_id,
        expected.start_time,
        expected.end_time,
    )
    assert result == expected
    appointment_repo.book_slot.assert_called_once_with(
        patient_id=patient_id, doctor_id=doctor_id, slot_id=slot_id, reason=None
    )


def test_appointment_atomic_booking_fails_closed_for_missing_patient():
    appointment_repo, patient_repo, doctor_repo, availability_repo = (
        Mock() for _ in range(4)
    )
    patient_repo.get_by_id.return_value = None
    service = AppointmentService(
        appointment_repo, patient_repo, doctor_repo, availability_repo
    )
    now = datetime.now(timezone.utc) + timedelta(days=1)
    with pytest.raises(ValueError, match="Authenticated patient profile"):
        service.atomic_create_appointment_and_update_slot(
            uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), now, now + timedelta(minutes=30)
        )
    appointment_repo.book_slot.assert_not_called()


def test_specialty_model_is_stable():
    specialty = SpecialtyModel(name="Cardiology")
    assert specialty.name == "Cardiology"
