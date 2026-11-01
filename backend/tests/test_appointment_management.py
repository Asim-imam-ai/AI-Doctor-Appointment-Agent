"""Durable cancellation/rescheduling proposal lifecycle and atomic execution tests."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from app.domain.models import (
    AppointmentModel,
    AppointmentStatus,
    AvailabilityStatus,
    DoctorAvailabilityModel,
    DoctorModel,
    PatientModel,
)
from app.domain.proposals.management import (
    create_cancellation_proposal,
    create_rescheduling_proposal,
    execute_atomic_cancellation,
    execute_atomic_rescheduling,
    get_pending_cancellation_proposal,
    get_pending_rescheduling_proposal,
)
from app.domain.proposals.models import ProposalStatus


def _setup():
    patient_id, doctor_id, appointment_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    appointment = AppointmentModel(
        id=appointment_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        start_time=datetime.now(timezone.utc) + timedelta(days=3),
        end_time=datetime.now(timezone.utc) + timedelta(days=3, minutes=30),
        status=AppointmentStatus.CONFIRMED,
    )
    appt_service, patient_service, doctor_service = Mock(), Mock(), Mock()
    appt_service.check_cancellation_eligibility.return_value = appointment
    appt_service.check_reschedule_eligibility.return_value = appointment
    patient_service.get_patient.return_value = PatientModel(
        id=patient_id, name="Jane", email="jane@example.com"
    )
    doctor_service.get_doctor.return_value = DoctorModel(id=doctor_id, name="Dr. Shah")
    return patient_id, appointment, appt_service, patient_service, doctor_service


def test_cancellation_proposal_persists_action_and_owned_payload():
    patient_id, appointment, appt, patients, doctors = _setup()
    proposals = Mock()
    proposal = create_cancellation_proposal(
        appointment.id,
        patient_id,
        appointment_service=appt,
        patient_service=patients,
        doctor_service=doctors,
        proposal_repository=proposals,
    )
    assert proposal.status is ProposalStatus.PENDING_APPROVAL
    proposals.create.assert_called_once()
    assert proposals.create.call_args.args[2] == "CANCELLATION"


def test_cancellation_approval_executes_only_through_durable_rpc():
    patient_id, appointment, appt, patients, doctors = _setup()
    proposals = Mock()
    proposal = create_cancellation_proposal(
        appointment.id,
        patient_id,
        appointment_service=appt,
        patient_service=patients,
        doctor_service=doctors,
        proposal_repository=proposals,
    )
    proposals.get.return_value = {
        "action": "CANCELLATION",
        "status": "PENDING_APPROVAL",
        "payload": proposal.model_dump(mode="json"),
    }
    proposals.execute.return_value = {
        "status": "EXECUTED",
        "appointment": {"id": str(appointment.id)},
    }
    result = execute_atomic_cancellation(
        proposal.cancellation_request_id,
        proposal.proposal_version,
        patient_id,
        proposal_repository=proposals,
    )
    assert result.status is ProposalStatus.BOOKED
    proposals.execute.assert_called_once()
    appt.cancel_appointment.assert_not_called()


def test_cancellation_proposal_cannot_be_read_by_another_patient():
    patient_id, appointment, appt, patients, doctors = _setup()
    proposals = Mock()
    proposal = create_cancellation_proposal(
        appointment.id,
        patient_id,
        appointment_service=appt,
        patient_service=patients,
        doctor_service=doctors,
        proposal_repository=proposals,
    )
    proposals.get.return_value = None
    assert (
        get_pending_cancellation_proposal(
            proposal.cancellation_request_id, uuid.uuid4(), proposals
        )
        is None
    )


def test_rescheduling_proposal_revalidates_and_persists_replacement_slot():
    patient_id, appointment, appt, patients, doctors = _setup()
    slot = DoctorAvailabilityModel(
        doctor_id=appointment.doctor_id,
        start_time=appointment.start_time + timedelta(days=1),
        end_time=appointment.end_time + timedelta(days=1),
        status=AvailabilityStatus.AVAILABLE,
    )
    availability = Mock()
    availability.get_available_slots.return_value = [slot]
    proposals = Mock()
    proposal = create_rescheduling_proposal(
        appointment.id,
        patient_id,
        slot.id,
        appointment_service=appt,
        patient_service=patients,
        doctor_service=doctors,
        availability_service=availability,
        proposal_repository=proposals,
    )
    assert proposal.status is ProposalStatus.PENDING_APPROVAL
    assert proposal.new_slot_id == slot.id
    assert proposals.create.call_args.args[2] == "RESCHEDULING"


def test_rescheduling_rejects_slot_that_is_not_available():
    patient_id, appointment, appt, patients, doctors = _setup()
    slot = DoctorAvailabilityModel(
        doctor_id=appointment.doctor_id,
        start_time=appointment.start_time + timedelta(days=1),
        end_time=appointment.end_time + timedelta(days=1),
        status=AvailabilityStatus.BOOKED,
    )
    availability, proposals = Mock(), Mock()
    availability.get_available_slots.return_value = [slot]
    with pytest.raises(ValueError, match="not available"):
        create_rescheduling_proposal(
            appointment.id,
            patient_id,
            slot.id,
            appointment_service=appt,
            patient_service=patients,
            doctor_service=doctors,
            availability_service=availability,
            proposal_repository=proposals,
        )
    proposals.create.assert_not_called()


def test_rescheduling_execution_uses_atomic_proposal_rpc():
    patient_id, appointment, appt, patients, doctors = _setup()
    slot = DoctorAvailabilityModel(
        doctor_id=appointment.doctor_id,
        start_time=appointment.start_time + timedelta(days=1),
        end_time=appointment.end_time + timedelta(days=1),
        status=AvailabilityStatus.AVAILABLE,
    )
    availability, proposals = Mock(), Mock()
    availability.get_available_slots.return_value = [slot]
    proposal = create_rescheduling_proposal(
        appointment.id,
        patient_id,
        slot.id,
        appointment_service=appt,
        patient_service=patients,
        doctor_service=doctors,
        availability_service=availability,
        proposal_repository=proposals,
    )
    proposals.get.return_value = {
        "action": "RESCHEDULING",
        "status": "PENDING_APPROVAL",
        "payload": proposal.model_dump(mode="json"),
    }
    proposals.execute.return_value = {
        "status": "EXECUTED",
        "appointment": {"id": str(appointment.id)},
    }
    result = execute_atomic_rescheduling(
        proposal.reschedule_request_id,
        proposal.proposal_version,
        patient_id,
        proposal_repository=proposals,
    )
    assert result.status is ProposalStatus.BOOKED
    proposals.execute.assert_called_once()
    appt.atomic_reschedule_appointment.assert_not_called()


def test_rescheduling_proposal_uses_patient_scoped_lookup():
    proposals = Mock()
    assert (
        get_pending_rescheduling_proposal(str(uuid.uuid4()), uuid.uuid4(), proposals)
        is None
    )
