"""Durable cancellation and rescheduling proposal lifecycle."""

import uuid
from datetime import datetime, timedelta, timezone

from app.domain.models import AvailabilityStatus
from app.domain.proposals.lifecycle import ProposalLifecycle
from app.domain.proposals.models import (
    CancellationProposal,
    CancellationResult,
    ProposalStatus,
    ReschedulingProposal,
    ReschedulingResult,
)
from app.domain.proposals.repository import ProposalRepository


def create_cancellation_proposal(
    appointment_id: uuid.UUID,
    patient_id: uuid.UUID,
    *,
    appointment_service,
    patient_service,
    doctor_service,
    proposal_repository: ProposalRepository,
    reason: str | None = None,
    user_timezone: str = "UTC",
    ttl_minutes: int = 15,
) -> CancellationProposal:
    appointment = appointment_service.check_cancellation_eligibility(
        appointment_id, patient_id
    )
    patient = patient_service.get_patient(patient_id)
    doctor = doctor_service.get_doctor(appointment.doctor_id)
    if patient is None or doctor is None:
        raise ValueError("Patient or doctor profile was not found.")
    now = datetime.now(timezone.utc)
    proposal = CancellationProposal(
        cancellation_request_id=str(uuid.uuid4()),
        appointment_id=appointment_id,
        patient_id=patient_id,
        patient_name=patient.name,
        doctor_id=appointment.doctor_id,
        doctor_name=doctor.name,
        appointment_start=appointment.start_time,
        appointment_end=appointment.end_time,
        timezone=user_timezone,
        reason=reason,
        status=ProposalStatus.PENDING_APPROVAL,
        expires_at=now + timedelta(minutes=ttl_minutes),
        created_at=now,
    )
    ProposalLifecycle(proposal_repository).create(
        uuid.UUID(proposal.cancellation_request_id),
        patient_id,
        "CANCELLATION",
        proposal.proposal_version,
        proposal.model_dump(mode="json"),
        proposal.expires_at,
    )
    return proposal


def get_pending_cancellation_proposal(
    request_id: str, patient_id: uuid.UUID, proposal_repository: ProposalRepository
) -> CancellationProposal | None:
    record = ProposalLifecycle(proposal_repository).get_owned(
        uuid.UUID(request_id), patient_id, "CANCELLATION"
    )
    if not record:
        return None
    payload = dict(record["payload"])
    payload["status"] = _status(record.get("status"))
    return CancellationProposal.model_validate(payload)


def execute_atomic_cancellation(
    cancellation_request_id: str,
    proposal_version: int,
    patient_id: uuid.UUID,
    *,
    proposal_repository: ProposalRepository,
    cancellation_window_minutes: int = 120,
) -> CancellationResult:
    proposal = get_pending_cancellation_proposal(
        cancellation_request_id, patient_id, proposal_repository
    )
    if proposal is None:
        raise ValueError("Cancellation proposal was not found for this patient.")
    response = ProposalLifecycle(proposal_repository).execute(
        uuid.UUID(cancellation_request_id),
        patient_id,
        proposal_version,
        cancellation_window_minutes,
    )
    status = _status(response.get("status"))
    appt = response.get("appointment") or {}
    return CancellationResult(
        cancellation_request_id=cancellation_request_id,
        appointment_id=uuid.UUID(appt["id"])
        if appt.get("id")
        else proposal.appointment_id,
        status=status,
        doctor_name=proposal.doctor_name,
        patient_name=proposal.patient_name,
        message=response.get("error") or _message(status, "Appointment cancelled."),
    )


def create_rescheduling_proposal(
    appointment_id: uuid.UUID,
    patient_id: uuid.UUID,
    new_slot_id: uuid.UUID,
    *,
    appointment_service,
    patient_service,
    doctor_service,
    availability_service,
    proposal_repository: ProposalRepository,
    reason: str | None = None,
    user_timezone: str = "UTC",
    ttl_minutes: int = 15,
) -> ReschedulingProposal:
    old = appointment_service.check_reschedule_eligibility(appointment_id, patient_id)
    slot = next(
        (
            s
            for s in availability_service.get_available_slots(old.doctor_id)
            if s.id == new_slot_id and s.status == AvailabilityStatus.AVAILABLE
        ),
        None,
    )
    if slot is None:
        raise ValueError("Replacement slot is not available.")
    patient = patient_service.get_patient(patient_id)
    doctor = doctor_service.get_doctor(old.doctor_id)
    if patient is None or doctor is None:
        raise ValueError("Patient or doctor profile was not found.")
    now = datetime.now(timezone.utc)
    proposal = ReschedulingProposal(
        reschedule_request_id=str(uuid.uuid4()),
        appointment_id=appointment_id,
        patient_id=patient_id,
        patient_name=patient.name,
        doctor_id=old.doctor_id,
        doctor_name=doctor.name,
        old_start_time=old.start_time,
        old_end_time=old.end_time,
        new_slot_id=new_slot_id,
        new_start_time=slot.start_time,
        new_end_time=slot.end_time,
        timezone=user_timezone,
        reason=reason,
        status=ProposalStatus.PENDING_APPROVAL,
        expires_at=now + timedelta(minutes=ttl_minutes),
        created_at=now,
    )
    ProposalLifecycle(proposal_repository).create(
        uuid.UUID(proposal.reschedule_request_id),
        patient_id,
        "RESCHEDULING",
        proposal.proposal_version,
        proposal.model_dump(mode="json"),
        proposal.expires_at,
    )
    return proposal


def get_pending_rescheduling_proposal(
    request_id: str, patient_id: uuid.UUID, proposal_repository: ProposalRepository
) -> ReschedulingProposal | None:
    record = ProposalLifecycle(proposal_repository).get_owned(
        uuid.UUID(request_id), patient_id, "RESCHEDULING"
    )
    if not record:
        return None
    payload = dict(record["payload"])
    payload["status"] = _status(record.get("status"))
    return ReschedulingProposal.model_validate(payload)


def execute_atomic_rescheduling(
    reschedule_request_id: str,
    proposal_version: int,
    patient_id: uuid.UUID,
    *,
    proposal_repository: ProposalRepository,
    cancellation_window_minutes: int = 120,
) -> ReschedulingResult:
    proposal = get_pending_rescheduling_proposal(
        reschedule_request_id, patient_id, proposal_repository
    )
    if proposal is None:
        raise ValueError("Rescheduling proposal was not found for this patient.")
    response = ProposalLifecycle(proposal_repository).execute(
        uuid.UUID(reschedule_request_id),
        patient_id,
        proposal_version,
        cancellation_window_minutes,
    )
    status = _status(response.get("status"))
    appointment = response.get("appointment") or {}
    return ReschedulingResult(
        reschedule_request_id=reschedule_request_id,
        appointment_id=uuid.UUID(appointment["id"])
        if appointment.get("id")
        else proposal.appointment_id,
        status=status,
        doctor_name=proposal.doctor_name,
        patient_name=proposal.patient_name,
        new_start_time=proposal.new_start_time,
        new_end_time=proposal.new_end_time,
        timezone=proposal.timezone,
        message=response.get("error") or _message(status, "Appointment rescheduled."),
    )


def _status(value: str | None) -> ProposalStatus:
    if value == "EXECUTED":
        return ProposalStatus.BOOKED
    try:
        return ProposalStatus(value)
    except ValueError:
        return ProposalStatus.FAILED


def _message(status: ProposalStatus, success: str) -> str:
    return (
        success if status == ProposalStatus.BOOKED else "Appointment operation failed."
    )
