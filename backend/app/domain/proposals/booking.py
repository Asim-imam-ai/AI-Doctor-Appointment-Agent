"""Booking proposal creation and approval execution over durable persistence."""

import uuid
from datetime import datetime, timedelta, timezone

from app.domain.proposals.lifecycle import ProposalLifecycle
from app.domain.proposals.models import BookingProposal, BookingResult, ProposalStatus
from app.domain.proposals.repository import ProposalRepository


def create_booking_proposal(
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
    slot_id: uuid.UUID,
    *,
    patient_service,
    doctor_service,
    availability_service,
    proposal_repository: ProposalRepository,
    user_timezone: str = "UTC",
    reason: str | None = None,
    ttl_minutes: int = 15,
) -> BookingProposal:
    patient = patient_service.get_patient(patient_id)
    doctor = doctor_service.get_doctor(doctor_id)
    if patient is None:
        raise ValueError("Patient profile was not found.")
    if doctor is None or not doctor.is_active:
        raise ValueError("Doctor is not active or was not found.")
    slot = next(
        (
            candidate
            for candidate in availability_service.get_available_slots(doctor_id)
            if candidate.id == slot_id
        ),
        None,
    )
    if slot is None:
        raise ValueError("Selected slot is not available.")

    now = datetime.now(timezone.utc)
    proposal = BookingProposal(
        booking_request_id=str(uuid.uuid4()),
        patient_id=patient_id,
        patient_name=patient.name,
        doctor_id=doctor_id,
        doctor_name=doctor.name,
        slot_id=slot_id,
        start_time=slot.start_time,
        end_time=slot.end_time,
        timezone=user_timezone,
        clinic_name=doctor.clinic_name,
        reason=reason,
        expires_at=now + timedelta(minutes=ttl_minutes),
        created_at=now,
    )
    ProposalLifecycle(proposal_repository).create(
        proposal_id=uuid.UUID(proposal.booking_request_id),
        patient_id=patient_id,
        action="BOOKING",
        version=proposal.proposal_version,
        payload=proposal.model_dump(mode="json"),
        expires_at=proposal.expires_at,
    )
    return proposal


def get_pending_proposal(
    booking_request_id: str,
    patient_id: uuid.UUID,
    proposal_repository: ProposalRepository,
) -> BookingProposal | None:
    record = ProposalLifecycle(proposal_repository).get_owned(
        uuid.UUID(booking_request_id), patient_id, "BOOKING"
    )
    if record is None:
        return None
    payload = dict(record["payload"])
    payload["status"] = _status_from_record(record.get("status"))
    return BookingProposal.model_validate(payload)


def execute_atomic_booking(
    booking_request_id: str,
    proposal_version: int,
    patient_id: uuid.UUID,
    *,
    proposal_repository: ProposalRepository,
    cancellation_window_minutes: int = 120,
) -> BookingResult:
    proposal = get_pending_proposal(booking_request_id, patient_id, proposal_repository)
    if proposal is None:
        return BookingResult(
            booking_request_id=booking_request_id,
            status=ProposalStatus.FAILED,
            doctor_name="",
            patient_name="",
            message="Booking proposal was not found for this patient.",
        )
    if proposal.proposal_version != proposal_version:
        return _booking_result(
            proposal, ProposalStatus.FAILED, "Proposal version is outdated."
        )
    response = ProposalLifecycle(proposal_repository).execute(
        uuid.UUID(booking_request_id),
        patient_id,
        proposal_version,
        cancellation_window_minutes,
    )
    status = _status_from_record(response.get("status"))
    appointment = response.get("appointment") or {}
    return _booking_result(
        proposal,
        status,
        response.get("error") or _execution_message(status, "Appointment booked."),
        uuid.UUID(appointment["id"]) if appointment.get("id") else None,
    )


def _booking_result(
    proposal: BookingProposal,
    status: ProposalStatus,
    message: str,
    appointment_id: uuid.UUID | None = None,
) -> BookingResult:
    return BookingResult(
        booking_request_id=proposal.booking_request_id,
        appointment_id=appointment_id,
        status=status,
        doctor_name=proposal.doctor_name,
        patient_name=proposal.patient_name,
        start_time=proposal.start_time,
        end_time=proposal.end_time,
        timezone=proposal.timezone,
        message=message,
    )


def _status_from_record(value: str | None) -> ProposalStatus:
    mapping = {
        "PENDING_APPROVAL": ProposalStatus.PENDING_APPROVAL,
        "APPROVED": ProposalStatus.APPROVED,
        "REJECTED": ProposalStatus.REJECTED,
        "EXPIRED": ProposalStatus.EXPIRED,
        "EXECUTED": ProposalStatus.BOOKED,
        "FAILED": ProposalStatus.FAILED,
    }
    return mapping.get(str(value), ProposalStatus.FAILED)


def _execution_message(status: ProposalStatus, success: str) -> str:
    if status == ProposalStatus.BOOKED:
        return success
    if status == ProposalStatus.EXPIRED:
        return "Proposal has expired. Prepare a new request."
    return "Appointment operation could not be completed."
