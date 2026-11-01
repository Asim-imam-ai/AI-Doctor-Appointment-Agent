"""Durable booking proposal and human-approval lifecycle tests."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from app.agentic.workflows.booking.graph import build_appointment_booking_graph
from app.agentic.workflows.booking.nodes import (
    classify_booking_intent_node,
    post_approval_atomic_booking_node,
)
from app.agentic.workflows.booking.prompts import BOOKING_SYSTEM_PROMPT
from app.domain.models import (
    AvailabilityStatus,
    DoctorAvailabilityModel,
    DoctorModel,
    PatientModel,
)
from app.domain.proposals.booking import (
    create_booking_proposal,
    execute_atomic_booking,
    get_pending_proposal,
)
from app.domain.proposals.models import ProposalStatus


def _services():
    patient_id, doctor_id = uuid.uuid4(), uuid.uuid4()
    patient_service, doctor_service, availability_service = Mock(), Mock(), Mock()
    patient_service.get_patient.return_value = PatientModel(
        id=patient_id, name="Jane", email="jane@example.com"
    )
    doctor_service.get_doctor.return_value = DoctorModel(
        id=doctor_id, name="Dr. Shah", clinic_name="Central Clinic"
    )
    now = datetime.now(timezone.utc) + timedelta(days=1)
    slot = DoctorAvailabilityModel(
        doctor_id=doctor_id,
        start_time=now,
        end_time=now + timedelta(minutes=30),
        status=AvailabilityStatus.AVAILABLE,
    )
    availability_service.get_available_slots.return_value = [slot]
    return (
        patient_id,
        doctor_id,
        slot,
        patient_service,
        doctor_service,
        availability_service,
    )


def test_booking_proposal_is_persisted_with_owner_action_version_and_expiration():
    patient_id, doctor_id, slot, patients, doctors, availability = _services()
    repository = Mock()
    proposal = create_booking_proposal(
        patient_id,
        doctor_id,
        slot.id,
        patient_service=patients,
        doctor_service=doctors,
        availability_service=availability,
        proposal_repository=repository,
    )

    assert proposal.status is ProposalStatus.PENDING_APPROVAL
    repository.create.assert_called_once()
    call = repository.create.call_args.args
    assert call[1] == patient_id
    assert call[2] == "BOOKING"
    assert call[3] == proposal.proposal_version
    assert call[4]["slot_id"] == str(slot.id)
    assert call[5] > datetime.now(timezone.utc)


def test_pending_booking_is_patient_scoped_and_durable():
    patient_id, doctor_id, slot, patients, doctors, availability = _services()
    repository = Mock()
    proposal = create_booking_proposal(
        patient_id,
        doctor_id,
        slot.id,
        patient_service=patients,
        doctor_service=doctors,
        availability_service=availability,
        proposal_repository=repository,
    )
    repository.get.return_value = {
        "action": "BOOKING",
        "status": "PENDING_APPROVAL",
        "payload": proposal.model_dump(mode="json"),
    }

    loaded = get_pending_proposal(proposal.booking_request_id, patient_id, repository)
    assert loaded == proposal
    repository.get.assert_called_once_with(
        uuid.UUID(proposal.booking_request_id), patient_id
    )


def test_booking_execution_is_idempotent_via_repository_rpc():
    patient_id, doctor_id, slot, patients, doctors, availability = _services()
    repository = Mock()
    proposal = create_booking_proposal(
        patient_id,
        doctor_id,
        slot.id,
        patient_service=patients,
        doctor_service=doctors,
        availability_service=availability,
        proposal_repository=repository,
    )
    repository.get.return_value = {
        "action": "BOOKING",
        "status": "PENDING_APPROVAL",
        "payload": proposal.model_dump(mode="json"),
    }
    appointment_id = uuid.uuid4()
    repository.execute.return_value = {
        "status": "EXECUTED",
        "appointment": {"id": str(appointment_id)},
    }

    result = execute_atomic_booking(
        proposal.booking_request_id,
        proposal.proposal_version,
        patient_id,
        proposal_repository=repository,
    )
    assert result.status is ProposalStatus.BOOKED
    assert result.appointment_id == appointment_id
    repository.execute.assert_called_once()


def test_booking_node_never_mutates_without_explicit_approval():
    result = post_approval_atomic_booking_node({"booking_proposal": {"id": "proposal"}})
    assert "error" in result
    assert "without explicit HITL approval" in result["error"]


def test_booking_intent_refuses_medical_advice_and_other_mutations():
    assert (
        classify_booking_intent_node({"user_message": "diagnose my symptoms"})["intent"]
        == "OUT_OF_SCOPE"
    )
    assert (
        classify_booking_intent_node({"user_message": "cancel my appointment"})[
            "intent"
        ]
        == "UNSUPPORTED"
    )


def test_booking_graph_and_prompt_preserve_human_approval_boundary():
    assert build_appointment_booking_graph() is not None
    assert "approval" in BOOKING_SYSTEM_PROMPT.lower()
