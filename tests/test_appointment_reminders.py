"""Comprehensive unit and integration test suite for Phase 7 Reminders & Notifications Subsystem."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    AppointmentModel,
    AppointmentStatus,
    DoctorModel,
    PatientModel,
    ReminderStatus,
    ReminderType,
)
from app.repositories import (
    _in_memory_appointment_repo,
    _in_memory_availability_repo,
    _in_memory_doctor_repo,
    _in_memory_notification_delivery_repo,
    _in_memory_notification_preference_repo,
    _in_memory_patient_repo,
    _in_memory_reminder_repo,
)
from app.services.appointment_service import AppointmentService
from app.services.notification_service import (
    MockNotificationProvider,
    NotificationService,
)
from app.services.reminder_service import ReminderService


@pytest.fixture(autouse=True)
def setup_in_memory_repos():
    """Resets in-memory storage before each test."""
    _in_memory_patient_repo._storage.clear()
    _in_memory_doctor_repo._storage.clear()
    _in_memory_availability_repo._storage.clear()
    _in_memory_appointment_repo._storage.clear()
    _in_memory_reminder_repo._storage.clear()
    _in_memory_notification_preference_repo._storage.clear()
    _in_memory_notification_delivery_repo._storage.clear()

    patient = PatientModel(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        name="Alice Smith",
        email="alice@example.com",
        timezone="UTC",
    )
    _in_memory_patient_repo.create(patient)

    doctor = DoctorModel(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        name="Dr. Sarah Connor",
        clinic_name="Metro Clinic",
        is_active=True,
    )
    _in_memory_doctor_repo.create(doctor)

    return {"patient": patient, "doctor": doctor}


def test_reminder_calculation_and_scheduling(setup_in_memory_repos):
    """Test calculation of 24h and 2h reminder times and creation after booking."""
    patient = setup_in_memory_repos["patient"]
    r_service = ReminderService()

    now_utc = datetime.now(timezone.utc)
    appt_start = now_utc + timedelta(days=2)
    appt = AppointmentModel(
        patient_id=patient.id,
        doctor_id=setup_in_memory_repos["doctor"].id,
        start_time=appt_start,
        end_time=appt_start + timedelta(minutes=30),
        status=AppointmentStatus.CONFIRMED,
    )
    _in_memory_appointment_repo.create(appt)

    reminders = r_service.schedule_reminders_for_appointment(appt)
    assert len(reminders) == 2
    types = [r.reminder_type for r in reminders]
    assert ReminderType.TWENTY_FOUR_HOURS_BEFORE in types
    assert ReminderType.TWO_HOURS_BEFORE in types

    for r in reminders:
        assert r.status == ReminderStatus.PENDING
        assert r.patient_id == patient.id


def test_due_reminder_processing_success(setup_in_memory_repos):
    """Test worker claiming and processing due reminder to SENT status."""
    patient = setup_in_memory_repos["patient"]
    mock_provider = MockNotificationProvider()
    n_service = NotificationService(provider=mock_provider)
    r_service = ReminderService(notification_service=n_service)

    now_utc = datetime.now(timezone.utc)
    # Appointment starts in 3 hours -> 2h reminder is scheduled for (now_utc + 1 hour)
    appt_start = now_utc + timedelta(hours=3)
    appt = AppointmentModel(
        patient_id=patient.id,
        doctor_id=setup_in_memory_repos["doctor"].id,
        start_time=appt_start,
        end_time=appt_start + timedelta(minutes=30),
        status=AppointmentStatus.CONFIRMED,
    )
    _in_memory_appointment_repo.create(appt)

    reminders = r_service.schedule_reminders_for_appointment(appt)
    assert len(reminders) >= 1

    # Fast forward as_of_time to (now_utc + 2 hours) when 2h reminder is due
    due_time = now_utc + timedelta(hours=2)
    results = r_service.process_due_reminders(as_of_time=due_time)
    assert len(results) >= 1
    sent_res = next((res for res in results if res["status"] == "SENT"), None)
    assert sent_res is not None

    # Verify provider received message
    assert len(mock_provider.sent_messages) == 1
    assert mock_provider.sent_messages[0]["recipient"] == patient.email


def test_cancelled_appointment_skips_reminder(setup_in_memory_repos):
    """Test that cancelling an appointment invalidates reminders and worker skips invalid appointments."""
    patient = setup_in_memory_repos["patient"]
    appt_service = AppointmentService()
    r_service = ReminderService()

    now_utc = datetime.now(timezone.utc)
    appt_start = now_utc + timedelta(hours=5)
    appt = AppointmentModel(
        patient_id=patient.id,
        doctor_id=setup_in_memory_repos["doctor"].id,
        start_time=appt_start,
        end_time=appt_start + timedelta(minutes=30),
        status=AppointmentStatus.CONFIRMED,
    )
    _in_memory_appointment_repo.create(appt)

    # Schedule reminders
    reminders = r_service.schedule_reminders_for_appointment(appt)
    assert len(reminders) > 0

    # Cancel appointment
    appt_service.cancel_appointment(appt.id, patient.id)

    # Verify reminders cancelled
    updated_rems = _in_memory_reminder_repo.list_for_appointment(appt.id)
    assert all(r.status == ReminderStatus.CANCELLED for r in updated_rems)

    # Process due reminders
    results = r_service.process_due_reminders(as_of_time=now_utc + timedelta(hours=4))
    assert not any(res.get("status") == "SENT" for res in results)


def test_user_preference_disabled_skips_reminder(setup_in_memory_repos):
    """Test that disabling notifications in preferences causes reminders to be SKIPPED."""
    patient = setup_in_memory_repos["patient"]
    mock_provider = MockNotificationProvider()
    n_service = NotificationService(provider=mock_provider)
    r_service = ReminderService(notification_service=n_service)

    # Disable reminders
    r_service.update_user_preferences(patient.id, reminders_enabled=False)

    now_utc = datetime.now(timezone.utc)
    appt_start = now_utc + timedelta(hours=3)
    appt = AppointmentModel(
        patient_id=patient.id,
        doctor_id=setup_in_memory_repos["doctor"].id,
        start_time=appt_start,
        end_time=appt_start + timedelta(minutes=30),
        status=AppointmentStatus.CONFIRMED,
    )
    _in_memory_appointment_repo.create(appt)
    r_service.schedule_reminders_for_appointment(appt)

    due_time = now_utc + timedelta(hours=2)
    results = r_service.process_due_reminders(as_of_time=due_time)
    assert any(res["status"] == "SKIPPED" for res in results)
    assert len(mock_provider.sent_messages) == 0


def test_provider_transient_failure_and_retry_limit(setup_in_memory_repos):
    """Test bounded retry logic upon provider failure."""
    patient = setup_in_memory_repos["patient"]
    failing_provider = MockNotificationProvider(should_fail=True, is_transient=True)
    n_service = NotificationService(provider=failing_provider)
    r_service = ReminderService(notification_service=n_service)

    now_utc = datetime.now(timezone.utc)
    appt_start = now_utc + timedelta(hours=3)
    appt = AppointmentModel(
        patient_id=patient.id,
        doctor_id=setup_in_memory_repos["doctor"].id,
        start_time=appt_start,
        end_time=appt_start + timedelta(minutes=30),
        status=AppointmentStatus.CONFIRMED,
    )
    _in_memory_appointment_repo.create(appt)
    reminders = r_service.schedule_reminders_for_appointment(appt)
    assert len(reminders) > 0

    due_time = now_utc + timedelta(hours=2)
    # Attempt 1
    res1 = r_service.process_due_reminders(as_of_time=due_time)
    assert res1[0]["status"] == "RETRYING"
    assert res1[0]["attempt"] == 1

    # Attempt 2
    res2 = r_service.process_due_reminders(as_of_time=due_time)
    assert res2[0]["status"] == "RETRYING"
    assert res2[0]["attempt"] == 2

    # Attempt 3 -> exceeds max_retries (3) -> FAILED
    res3 = r_service.process_due_reminders(as_of_time=due_time)
    assert res3[0]["status"] == "FAILED"


def test_idempotency_prevents_duplicate_scheduling(setup_in_memory_repos):
    """Test that duplicate scheduling calls for the same appointment use idempotency keys."""
    patient = setup_in_memory_repos["patient"]
    r_service = ReminderService()

    now_utc = datetime.now(timezone.utc)
    appt_start = now_utc + timedelta(days=2)
    appt = AppointmentModel(
        patient_id=patient.id,
        doctor_id=setup_in_memory_repos["doctor"].id,
        start_time=appt_start,
        end_time=appt_start + timedelta(minutes=30),
        status=AppointmentStatus.CONFIRMED,
    )
    _in_memory_appointment_repo.create(appt)

    r1 = r_service.schedule_reminders_for_appointment(appt)
    r2 = r_service.schedule_reminders_for_appointment(appt)
    assert len(r1) == 2
    assert len(r2) == 2
    # All returned IDs match
    assert [r.id for r in r1] == [r.id for r in r2]
