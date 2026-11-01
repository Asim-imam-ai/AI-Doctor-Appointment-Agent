"""Concurrency regression checks for the atomic appointment RPC boundary."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from app.domain import AppointmentService
from app.domain.models import DoctorModel, PatientModel


def test_parallel_booking_attempts_cannot_both_reserve_one_slot():
    patient_id, doctor_id, slot_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    appointments, patients, doctors, availability = (
        type("Repo", (), {})() for _ in range(4)
    )
    patients.get_by_id = lambda _id: PatientModel(
        id=patient_id, name="Patient", email="patient@example.com"
    )
    doctors.get_by_id = lambda _id: DoctorModel(id=doctor_id, name="Doctor")
    lock = Lock()
    reserved = False

    def atomic_book(**_kwargs):
        nonlocal reserved
        with lock:
            if reserved:
                raise ValueError("Selected availability slot is no longer available.")
            reserved = True
            return "created"

    appointments.book_slot = atomic_book
    service = AppointmentService(appointments, patients, doctors, availability)

    def attempt():
        from datetime import datetime, timedelta, timezone

        start = datetime.now(timezone.utc) + timedelta(days=1)
        try:
            return service.atomic_create_appointment_and_update_slot(
                patient_id, doctor_id, slot_id, start, start + timedelta(minutes=30)
            )
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert results.count("created") == 1
    assert results.count(None) == 1


def test_production_migration_uses_row_lock_and_unique_active_slot_constraint():
    migration = (
        Path(__file__).resolve().parents[3]
        / "supabase"
        / "migrations"
        / "003_atomic_appointments_and_proposals.sql"
    ).resolve()
    sql = migration.read_text(encoding="utf-8")
    assert "FOR UPDATE" in sql.upper()
    assert "IDX_APPOINTMENTS_ACTIVE_AVAILABILITY" in sql.upper()
    assert "EXECUTE_APPOINTMENT_PROPOSAL" in sql.upper()
