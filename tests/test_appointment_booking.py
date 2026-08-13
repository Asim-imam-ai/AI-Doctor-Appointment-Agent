"""Unit, graph, API, HITL boundary, and safety tests for Phase 5 Booking Agent."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.agents import AppointmentBookingState, build_appointment_booking_graph
from app.agents.appointment_booking import classify_booking_intent_node
from app.core.prompts import BOOKING_SYSTEM_PROMPT
from app.main import app
from app.models import AvailabilityStatus, DoctorAvailabilityModel
from app.repositories import (
    get_appointment_repository,
    get_availability_repository,
    get_doctor_repository,
    get_patient_repository,
)
from app.schemas.booking_agent import (
    ProposalStatus,
)
from app.services import (
    AppointmentService,
    AvailabilityService,
    DoctorService,
    PatientService,
)
from app.tools.booking_proposal import (
    _PENDING_PROPOSALS,
    create_booking_proposal,
    execute_atomic_booking,
    prepare_booking_proposal_tool,
)


@pytest.fixture
def seeded_booking_services():
    p_repo = get_patient_repository()
    d_repo = get_doctor_repository()
    a_repo = get_availability_repository()
    appt_repo = get_appointment_repository()

    if hasattr(p_repo, "_storage"):
        p_repo._storage.clear()
    if hasattr(d_repo, "_storage"):
        d_repo._storage.clear()
    if hasattr(a_repo, "_storage"):
        a_repo._storage.clear()
    if hasattr(appt_repo, "_storage"):
        appt_repo._storage.clear()

    _PENDING_PROPOSALS.clear()

    p_service = PatientService(repository=p_repo)
    d_service = DoctorService(doctor_repo=d_repo)
    a_service = AvailabilityService(availability_repo=a_repo, doctor_repo=d_repo)
    appt_service = AppointmentService(
        appointment_repo=appt_repo,
        patient_repo=p_repo,
        doctor_repo=d_repo,
        availability_repo=a_repo,
    )

    patient = p_service.register_patient(
        name="John Doe", email="john@example.com", phone="+1234567890"
    )

    doctor = d_service.register_doctor(
        name="Dr. Ahmed Khan", clinic_name="Heart Clinic", location="Lahore"
    )

    now = datetime.now(timezone.utc)
    t_tomorrow = (now + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )

    slot = DoctorAvailabilityModel(
        doctor_id=doctor.id,
        start_time=t_tomorrow,
        end_time=t_tomorrow + timedelta(minutes=30),
        status=AvailabilityStatus.AVAILABLE,
    )
    a_repo.create(slot)

    return p_service, d_service, a_service, appt_service, patient, doctor, slot


# ---------------------------------------------------------------------------
# 1. Proposal Creation & Expiration Unit Tests
# ---------------------------------------------------------------------------


def test_create_booking_proposal_success(seeded_booking_services):
    p_service, d_service, a_service, appt_service, patient, doctor, slot = (
        seeded_booking_services
    )

    proposal = create_booking_proposal(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        patient_service=p_service,
        doctor_service=d_service,
        availability_service=a_service,
    )

    assert proposal.status == ProposalStatus.PENDING_APPROVAL
    assert proposal.doctor_name == "Dr. Ahmed Khan"
    assert proposal.patient_name == "John Doe"
    assert proposal.booking_request_id in _PENDING_PROPOSALS


def test_prepare_booking_proposal_tool_invocation(seeded_booking_services):
    p_service, d_service, a_service, appt_service, patient, doctor, slot = (
        seeded_booking_services
    )

    output = prepare_booking_proposal_tool.invoke(
        {
            "patient_id": str(patient.id),
            "doctor_id": str(doctor.id),
            "slot_id": str(slot.id),
        }
    )
    assert isinstance(output, str)
    assert "PENDING_APPROVAL" in output
    assert "Dr. Ahmed Khan" in output


# ---------------------------------------------------------------------------
# 2. HITL Approval & Rejection Execution Tests
# ---------------------------------------------------------------------------


def test_atomic_booking_with_explicit_approval(seeded_booking_services):
    p_service, d_service, a_service, appt_service, patient, doctor, slot = (
        seeded_booking_services
    )

    proposal = create_booking_proposal(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        patient_service=p_service,
        doctor_service=d_service,
        availability_service=a_service,
    )

    result = execute_atomic_booking(
        booking_request_id=proposal.booking_request_id,
        proposal_version=1,
        patient_id=patient.id,
        appointment_service=appt_service,
    )

    assert result.status == ProposalStatus.BOOKED
    assert result.appointment_id is not None
    assert "successfully booked" in result.message

    # Verify slot is updated to BOOKED
    updated_slot = a_service.get_available_slots(doctor.id)
    assert len(updated_slot) == 0


def test_atomic_booking_unauthorized_patient(seeded_booking_services):
    p_service, d_service, a_service, appt_service, patient, doctor, slot = (
        seeded_booking_services
    )

    proposal = create_booking_proposal(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        patient_service=p_service,
        doctor_service=d_service,
        availability_service=a_service,
    )

    other_patient_id = uuid.uuid4()
    result = execute_atomic_booking(
        booking_request_id=proposal.booking_request_id,
        proposal_version=1,
        patient_id=other_patient_id,
        appointment_service=appt_service,
    )

    assert result.status == ProposalStatus.FAILED
    assert "Unauthorized" in result.message


def test_atomic_booking_expired_proposal(seeded_booking_services):
    p_service, d_service, a_service, appt_service, patient, doctor, slot = (
        seeded_booking_services
    )

    proposal = create_booking_proposal(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        ttl_minutes=-5,  # Force immediate expiration
        patient_service=p_service,
        doctor_service=d_service,
        availability_service=a_service,
    )

    result = execute_atomic_booking(
        booking_request_id=proposal.booking_request_id,
        proposal_version=1,
        patient_id=patient.id,
        appointment_service=appt_service,
    )

    assert result.status == ProposalStatus.EXPIRED
    assert "expired" in result.message


def test_atomic_booking_slot_no_longer_available(seeded_booking_services):
    p_service, d_service, a_service, appt_service, patient, doctor, slot = (
        seeded_booking_services
    )

    proposal = create_booking_proposal(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        patient_service=p_service,
        doctor_service=d_service,
        availability_service=a_service,
    )

    # Manually mark slot BOOKED prior to approval
    a_repo = get_availability_repository()
    a_repo.update_status(slot.id, AvailabilityStatus.BOOKED)

    result = execute_atomic_booking(
        booking_request_id=proposal.booking_request_id,
        proposal_version=1,
        patient_id=patient.id,
        appointment_service=appt_service,
    )

    assert result.status == ProposalStatus.SLOT_UNAVAILABLE
    assert "no longer available" in result.message


# ---------------------------------------------------------------------------
# 3. Idempotency & Safety Boundary Tests
# ---------------------------------------------------------------------------


def test_atomic_booking_idempotent_retry(seeded_booking_services):
    p_service, d_service, a_service, appt_service, patient, doctor, slot = (
        seeded_booking_services
    )

    proposal = create_booking_proposal(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        patient_service=p_service,
        doctor_service=d_service,
        availability_service=a_service,
    )

    res1 = execute_atomic_booking(
        booking_request_id=proposal.booking_request_id,
        proposal_version=1,
        patient_id=patient.id,
        appointment_service=appt_service,
    )
    assert res1.status == ProposalStatus.BOOKED

    # Duplicate retry
    res2 = execute_atomic_booking(
        booking_request_id=proposal.booking_request_id,
        proposal_version=1,
        patient_id=patient.id,
        appointment_service=appt_service,
    )
    assert res2.status == ProposalStatus.BOOKED
    assert "already booked" in res2.message


def test_booking_intent_classification_safety():
    state: AppointmentBookingState = {
        "user_message": "Can you prescribe medicine for my cough?",
        "patient_id": uuid.uuid4(),
        "doctor_id": None,
        "slot_id": None,
        "user_timezone": "UTC",
        "reason": None,
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "proposal_version": 1,
        "metadata": {},
    }
    res = classify_booking_intent_node(state)
    assert res["intent"] == "OUT_OF_SCOPE"
    assert "cannot provide medical" in res["response"]


# ---------------------------------------------------------------------------
# 4. Graph Workflow Tests
# ---------------------------------------------------------------------------


def test_graph_prepare_proposal_flow(seeded_booking_services):
    p_service, d_service, a_service, appt_service, patient, doctor, slot = (
        seeded_booking_services
    )

    graph = build_appointment_booking_graph()
    initial_state = {
        "user_message": "Book an appointment with Dr. Ahmed",
        "patient_id": patient.id,
        "doctor_id": doctor.id,
        "slot_id": slot.id,
        "user_timezone": "UTC",
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "proposal_version": 1,
        "metadata": {},
    }

    final_state = graph.invoke(initial_state)

    assert final_state.get("booking_proposal") is not None
    assert final_state["approval_status"] == "PENDING"
    assert "Requires approval" in final_state["response"]


def test_graph_resume_with_approval_executes_booking(seeded_booking_services):
    p_service, d_service, a_service, appt_service, patient, doctor, slot = (
        seeded_booking_services
    )

    proposal = create_booking_proposal(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        patient_service=p_service,
        doctor_service=d_service,
        availability_service=a_service,
    )

    graph = build_appointment_booking_graph()
    resume_state = {
        "booking_proposal": proposal,
        "approval_status": "APPROVED",
        "proposal_version": 1,
        "patient_id": patient.id,
        "messages": [],
        "iteration_count": 0,
        "tool_call_count": 0,
        "metadata": {},
    }

    final_state = graph.invoke(resume_state)

    assert final_state.get("booking_result") is not None
    assert final_state["booking_result"].status == ProposalStatus.BOOKED


# ---------------------------------------------------------------------------
# 5. FastAPI Endpoints Integration Tests
# ---------------------------------------------------------------------------


client = TestClient(app)


def test_api_prepare_and_approve_booking_flow(seeded_booking_services):
    p_service, d_service, a_service, appt_service, patient, doctor, slot = (
        seeded_booking_services
    )

    # 1. Prepare endpoint
    prep_res = client.post(
        "/api/v1/appointments/prepare",
        json={
            "patient_id": str(patient.id),
            "doctor_id": str(doctor.id),
            "slot_id": str(slot.id),
            "message": "I would like to book Dr. Ahmed for tomorrow morning",
        },
    )

    assert prep_res.status_code == 200
    prep_data = prep_res.json()
    assert prep_data["status"] == "success"
    assert prep_data["requires_approval"] is True
    proposal = prep_data["proposal"]
    req_id = proposal["booking_request_id"]

    # 2. Approve endpoint
    appr_res = client.post(
        f"/api/v1/appointments/{req_id}/approve",
        json={
            "booking_request_id": req_id,
            "proposal_version": 1,
            "decision": "APPROVE",
            "patient_id": str(patient.id),
        },
    )

    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["status"] == "success"
    assert appr_data["booking_result"]["status"] == "BOOKED"


def test_api_reject_booking_proposal(seeded_booking_services):
    p_service, d_service, a_service, appt_service, patient, doctor, slot = (
        seeded_booking_services
    )

    proposal = create_booking_proposal(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        patient_service=p_service,
        doctor_service=d_service,
        availability_service=a_service,
    )

    req_id = proposal.booking_request_id

    rej_res = client.post(
        f"/api/v1/appointments/{req_id}/approve",
        json={
            "booking_request_id": req_id,
            "proposal_version": 1,
            "decision": "REJECT",
            "patient_id": str(patient.id),
        },
    )

    assert rej_res.status_code == 200
    rej_data = rej_res.json()
    assert rej_data["status"] == "success"
    assert "rejected" in rej_data["message"]


def test_booking_system_prompt_contains_hitl_rules():
    assert "Human-in-the-Loop (HITL) protection" in BOOKING_SYSTEM_PROMPT
    assert (
        "NEVER claim or inform the user that an appointment is booked"
        in BOOKING_SYSTEM_PROMPT
    )
    assert "prepare_booking_proposal_tool" in BOOKING_SYSTEM_PROMPT
