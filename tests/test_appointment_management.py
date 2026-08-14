"""Comprehensive unit and integration tests for Phase 6 Appointment Cancellation & Rescheduling Agent with HITL."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.agents import (
    build_appointment_cancellation_graph,
    build_appointment_rescheduling_graph,
)
from app.models import (
    AppointmentModel,
    AppointmentStatus,
    AvailabilityStatus,
    DoctorAvailabilityModel,
    DoctorModel,
    PatientModel,
)


@pytest.fixture(autouse=True)
def setup_in_memory_repos():
    """Resets in-memory repositories before each test."""
    from app.repositories import (
        _in_memory_appointment_repo,
        _in_memory_availability_repo,
        _in_memory_doctor_repo,
        _in_memory_patient_repo,
    )
    from app.tools.management_proposal import (
        _PENDING_CANCELLATION_PROPOSALS,
        _PENDING_RESCHEDULING_PROPOSALS,
    )

    _in_memory_patient_repo._storage.clear()
    _in_memory_doctor_repo._storage.clear()
    _in_memory_availability_repo._storage.clear()
    _in_memory_appointment_repo._storage.clear()
    _PENDING_CANCELLATION_PROPOSALS.clear()
    _PENDING_RESCHEDULING_PROPOSALS.clear()

    # Seed sample patient & doctor
    patient = PatientModel(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        name="John Doe",
        email="john@example.com",
    )
    _in_memory_patient_repo.create(patient)

    doctor = DoctorModel(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        name="Dr. Sarah Connor",
        clinic_name="Metro Clinic",
        is_active=True,
    )
    _in_memory_doctor_repo.create(doctor)

    return {
        "patient": patient,
        "doctor": doctor,
        "repos": (
            _in_memory_patient_repo,
            _in_memory_doctor_repo,
            _in_memory_availability_repo,
            _in_memory_appointment_repo,
        ),
    }


def test_cancellation_workflow_happy_path(setup_in_memory_repos):
    """Test full cancellation lifecycle: prepare -> approve -> atomic update."""
    patient = setup_in_memory_repos["patient"]
    doctor = setup_in_memory_repos["doctor"]
    app_repo = setup_in_memory_repos["repos"][3]

    # Create active future appointment (5 hours in future to respect 2hr policy)
    now_utc = datetime.now(timezone.utc)
    appt = AppointmentModel(
        patient_id=patient.id,
        doctor_id=doctor.id,
        start_time=now_utc + timedelta(hours=5),
        end_time=now_utc + timedelta(hours=5, minutes=30),
        status=AppointmentStatus.CONFIRMED,
        reason="General Checkup",
    )
    app_repo.create(appt)

    graph = build_appointment_cancellation_graph()

    # 1. Prepare proposal
    prep_state = graph.invoke(
        {
            "user_message": "Cancel my appointment",
            "patient_id": patient.id,
            "appointment_id": appt.id,
            "user_timezone": "UTC",
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "proposal_version": 1,
            "metadata": {},
        }
    )

    proposal = prep_state.get("cancellation_proposal")
    assert proposal is not None
    assert proposal.appointment_id == appt.id
    assert proposal.status.value == "PENDING_APPROVAL"

    # Verify state NOT mutated before approval
    unmutated_appt = app_repo.get_by_id(appt.id)
    assert unmutated_appt.status == AppointmentStatus.CONFIRMED

    # 2. Execute explicit HITL approval
    approve_state = graph.invoke(
        {
            "cancellation_proposal": proposal,
            "approval_status": "APPROVED",
            "proposal_version": proposal.proposal_version,
            "patient_id": patient.id,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "metadata": {},
        }
    )

    result = approve_state.get("cancellation_result")
    assert result is not None
    assert result.status.value == "BOOKED"

    # Verify atomic state update
    cancelled_appt = app_repo.get_by_id(appt.id)
    assert cancelled_appt.status == AppointmentStatus.CANCELLED


def test_cancellation_policy_violation(setup_in_memory_repos):
    """Test that attempting to cancel within cancellation window (<120m) fails deterministically."""
    patient = setup_in_memory_repos["patient"]
    doctor = setup_in_memory_repos["doctor"]
    app_repo = setup_in_memory_repos["repos"][3]

    now_utc = datetime.now(timezone.utc)
    # Appointment starting in 30 minutes (violates 120min policy)
    appt = AppointmentModel(
        patient_id=patient.id,
        doctor_id=doctor.id,
        start_time=now_utc + timedelta(minutes=30),
        end_time=now_utc + timedelta(minutes=60),
        status=AppointmentStatus.CONFIRMED,
    )
    app_repo.create(appt)

    graph = build_appointment_cancellation_graph()
    prep_state = graph.invoke(
        {
            "user_message": "Cancel my appointment today",
            "patient_id": patient.id,
            "appointment_id": appt.id,
            "user_timezone": "UTC",
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "proposal_version": 1,
            "metadata": {},
        }
    )

    assert prep_state.get("cancellation_proposal") is None
    assert "Cancellation window policy violation" in prep_state.get("error", "")


def test_rescheduling_workflow_happy_path(setup_in_memory_repos):
    """Test full rescheduling lifecycle: find slot -> prepare proposal -> approve -> atomic reschedule."""
    patient = setup_in_memory_repos["patient"]
    doctor = setup_in_memory_repos["doctor"]
    a_repo = setup_in_memory_repos["repos"][2]
    app_repo = setup_in_memory_repos["repos"][3]

    now_utc = datetime.now(timezone.utc)
    old_appt = AppointmentModel(
        patient_id=patient.id,
        doctor_id=doctor.id,
        start_time=now_utc + timedelta(days=1),
        end_time=now_utc + timedelta(days=1, hours=1),
        status=AppointmentStatus.CONFIRMED,
    )
    app_repo.create(old_appt)

    # Seed replacement slot
    new_slot = DoctorAvailabilityModel(
        doctor_id=doctor.id,
        start_time=now_utc + timedelta(days=2),
        end_time=now_utc + timedelta(days=2, hours=1),
        status=AvailabilityStatus.AVAILABLE,
    )
    a_repo.create(new_slot)

    graph = build_appointment_rescheduling_graph()

    # 1. Prepare proposal
    prep_state = graph.invoke(
        {
            "user_message": "Reschedule my appointment",
            "patient_id": patient.id,
            "appointment_id": old_appt.id,
            "new_slot_id": new_slot.id,
            "user_timezone": "UTC",
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "proposal_version": 1,
            "metadata": {},
        }
    )

    proposal = prep_state.get("rescheduling_proposal")
    assert proposal is not None
    assert proposal.appointment_id == old_appt.id
    assert proposal.new_slot_id == new_slot.id

    # Verify no state mutation before approval
    unmutated_appt = app_repo.get_by_id(old_appt.id)
    assert unmutated_appt.start_time == old_appt.start_time

    # 2. Approve proposal
    approve_state = graph.invoke(
        {
            "rescheduling_proposal": proposal,
            "approval_status": "APPROVED",
            "proposal_version": proposal.proposal_version,
            "patient_id": patient.id,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "metadata": {},
        }
    )

    result = approve_state.get("rescheduling_result")
    assert result is not None
    assert result.status.value == "BOOKED"

    # Verify atomic update
    rescheduled_appt = app_repo.get_by_id(old_appt.id)
    assert rescheduled_appt.start_time == new_slot.start_time
    updated_slot = a_repo.get_by_id(new_slot.id)
    assert updated_slot.status == AvailabilityStatus.BOOKED


def test_rescheduling_unauthorized_user(setup_in_memory_repos):
    """Test that users cannot reschedule another patient's appointment."""
    doctor = setup_in_memory_repos["doctor"]
    app_repo = setup_in_memory_repos["repos"][3]

    other_patient = PatientModel(
        id=uuid.uuid4(),
        name="Other Patient",
        email="other@example.com",
    )
    p_repo = setup_in_memory_repos["repos"][0]
    p_repo.create(other_patient)
    attacker_id = setup_in_memory_repos["patient"].id

    now_utc = datetime.now(timezone.utc)
    appt = AppointmentModel(
        patient_id=other_patient.id,
        doctor_id=doctor.id,
        start_time=now_utc + timedelta(days=1),
        end_time=now_utc + timedelta(days=1, hours=1),
        status=AppointmentStatus.CONFIRMED,
    )
    app_repo.create(appt)

    graph = build_appointment_rescheduling_graph()
    prep_state = graph.invoke(
        {
            "user_message": "Reschedule appointment",
            "patient_id": attacker_id,
            "appointment_id": appt.id,
            "user_timezone": "UTC",
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "proposal_version": 1,
            "metadata": {},
        }
    )

    assert prep_state.get("rescheduling_proposal") is None
    assert "Unauthorized" in prep_state.get("error", "")
