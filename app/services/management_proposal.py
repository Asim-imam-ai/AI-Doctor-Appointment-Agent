"""Deterministic proposal tool and atomic execution for Cancellation and Rescheduling (Phase 6)."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from app.models import AvailabilityStatus
from app.schemas.booking_agent import ProposalStatus
from app.schemas.management_agent import (
    CancellationProposal,
    CancellationResult,
    ReschedulingProposal,
    ReschedulingResult,
)
from app.services import (
    AppointmentService,
    AvailabilityService,
    DoctorService,
    PatientService,
)

# Global in-memory storage for pending cancellation and rescheduling proposals
_PENDING_CANCELLATION_PROPOSALS: Dict[str, CancellationProposal] = {}
_PENDING_RESCHEDULING_PROPOSALS: Dict[str, ReschedulingProposal] = {}


def create_cancellation_proposal(
    appointment_id: uuid.UUID,
    patient_id: uuid.UUID,
    reason: Optional[str] = None,
    user_timezone: str = "UTC",
    ttl_minutes: int = 15,
    appointment_service: Optional[AppointmentService] = None,
    patient_service: Optional[PatientService] = None,
    doctor_service: Optional[DoctorService] = None,
) -> CancellationProposal:
    appt_service = appointment_service or AppointmentService()
    p_service = patient_service or PatientService()
    d_service = doctor_service or DoctorService()

    # Verify ownership & eligibility
    appt = appt_service.check_cancellation_eligibility(appointment_id, patient_id)

    patient = p_service.get_patient(patient_id)
    patient_name = patient.name if patient else "Unknown Patient"

    doctor = d_service.get_doctor(appt.doctor_id)
    doctor_name = doctor.name if doctor else "Unknown Doctor"

    now_utc = datetime.now(timezone.utc)
    request_id = str(uuid.uuid4())

    proposal = CancellationProposal(
        cancellation_request_id=request_id,
        proposal_version=1,
        appointment_id=appointment_id,
        patient_id=patient_id,
        patient_name=patient_name,
        doctor_id=appt.doctor_id,
        doctor_name=doctor_name,
        appointment_start=appt.start_time,
        appointment_end=appt.end_time,
        timezone=user_timezone,
        reason=reason,
        status=ProposalStatus.PENDING_APPROVAL,
        expires_at=now_utc + timedelta(minutes=ttl_minutes),
        created_at=now_utc,
    )

    _PENDING_CANCELLATION_PROPOSALS[request_id] = proposal
    return proposal


def get_pending_cancellation_proposal(
    request_id: str,
) -> Optional[CancellationProposal]:
    return _PENDING_CANCELLATION_PROPOSALS.get(request_id)


def execute_atomic_cancellation(
    cancellation_request_id: str,
    proposal_version: int,
    patient_id: uuid.UUID,
    appointment_service: Optional[AppointmentService] = None,
) -> CancellationResult:
    proposal = _PENDING_CANCELLATION_PROPOSALS.get(cancellation_request_id)
    if not proposal:
        return CancellationResult(
            cancellation_request_id=cancellation_request_id,
            status=ProposalStatus.FAILED,
            doctor_name="Unknown",
            patient_name="Unknown",
            message="Cancellation proposal not found.",
        )

    # Authorization check
    if proposal.patient_id != patient_id:
        return CancellationResult(
            cancellation_request_id=cancellation_request_id,
            status=ProposalStatus.FAILED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message="Unauthorized: patient identity mismatch.",
        )

    # Version check
    if proposal.proposal_version != proposal_version:
        return CancellationResult(
            cancellation_request_id=cancellation_request_id,
            status=ProposalStatus.FAILED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message="Outdated proposal version.",
        )

    # Expiration check
    now_utc = datetime.now(timezone.utc)
    if proposal.expires_at < now_utc:
        proposal.status = ProposalStatus.EXPIRED
        return CancellationResult(
            cancellation_request_id=cancellation_request_id,
            status=ProposalStatus.EXPIRED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message="Cancellation proposal has expired.",
        )

    # Idempotency check
    if proposal.status == ProposalStatus.BOOKED:  # reuse as executed state
        return CancellationResult(
            cancellation_request_id=cancellation_request_id,
            appointment_id=proposal.appointment_id,
            status=ProposalStatus.BOOKED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message="Appointment is already cancelled.",
        )

    appt_service = appointment_service or AppointmentService()

    try:
        appt = appt_service.cancel_appointment(proposal.appointment_id, patient_id)
        proposal.status = ProposalStatus.BOOKED  # successfully mutated
        return CancellationResult(
            cancellation_request_id=cancellation_request_id,
            appointment_id=appt.id,
            status=ProposalStatus.BOOKED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message=f"Appointment on {proposal.appointment_start.strftime('%Y-%m-%d %H:%M UTC')} successfully cancelled.",
        )
    except Exception as e:
        proposal.status = ProposalStatus.FAILED
        return CancellationResult(
            cancellation_request_id=cancellation_request_id,
            status=ProposalStatus.FAILED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message=f"Cancellation failed: {str(e)}",
        )


def create_rescheduling_proposal(
    appointment_id: uuid.UUID,
    patient_id: uuid.UUID,
    new_slot_id: uuid.UUID,
    reason: Optional[str] = None,
    user_timezone: str = "UTC",
    ttl_minutes: int = 15,
    appointment_service: Optional[AppointmentService] = None,
    patient_service: Optional[PatientService] = None,
    doctor_service: Optional[DoctorService] = None,
    availability_service: Optional[AvailabilityService] = None,
) -> ReschedulingProposal:
    appt_service = appointment_service or AppointmentService()
    p_service = patient_service or PatientService()
    d_service = doctor_service or DoctorService()
    avail_service = availability_service or AvailabilityService()

    # Revalidate old appointment eligibility
    old_appt = appt_service.check_reschedule_eligibility(appointment_id, patient_id)

    # Revalidate replacement slot
    slots = avail_service.get_available_slots(old_appt.doctor_id)
    new_slot = next((s for s in slots if s.id == new_slot_id), None)
    if not new_slot or new_slot.status != AvailabilityStatus.AVAILABLE:
        raise ValueError(f"Replacement slot '{new_slot_id}' is not available.")

    patient = p_service.get_patient(patient_id)
    patient_name = patient.name if patient else "Unknown Patient"

    doctor = d_service.get_doctor(old_appt.doctor_id)
    doctor_name = doctor.name if doctor else "Unknown Doctor"

    now_utc = datetime.now(timezone.utc)
    request_id = str(uuid.uuid4())

    proposal = ReschedulingProposal(
        reschedule_request_id=request_id,
        proposal_version=1,
        appointment_id=appointment_id,
        patient_id=patient_id,
        patient_name=patient_name,
        doctor_id=old_appt.doctor_id,
        doctor_name=doctor_name,
        old_start_time=old_appt.start_time,
        old_end_time=old_appt.end_time,
        new_slot_id=new_slot_id,
        new_start_time=new_slot.start_time,
        new_end_time=new_slot.end_time,
        timezone=user_timezone,
        reason=reason,
        status=ProposalStatus.PENDING_APPROVAL,
        expires_at=now_utc + timedelta(minutes=ttl_minutes),
        created_at=now_utc,
    )

    _PENDING_RESCHEDULING_PROPOSALS[request_id] = proposal
    return proposal


def get_pending_rescheduling_proposal(
    request_id: str,
) -> Optional[ReschedulingProposal]:
    return _PENDING_RESCHEDULING_PROPOSALS.get(request_id)


def execute_atomic_rescheduling(
    reschedule_request_id: str,
    proposal_version: int,
    patient_id: uuid.UUID,
    appointment_service: Optional[AppointmentService] = None,
) -> ReschedulingResult:
    proposal = _PENDING_RESCHEDULING_PROPOSALS.get(reschedule_request_id)
    if not proposal:
        return ReschedulingResult(
            reschedule_request_id=reschedule_request_id,
            status=ProposalStatus.FAILED,
            doctor_name="Unknown",
            patient_name="Unknown",
            message="Rescheduling proposal not found.",
        )

    # Authorization check
    if proposal.patient_id != patient_id:
        return ReschedulingResult(
            reschedule_request_id=reschedule_request_id,
            status=ProposalStatus.FAILED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message="Unauthorized: patient identity mismatch.",
        )

    # Version check
    if proposal.proposal_version != proposal_version:
        return ReschedulingResult(
            reschedule_request_id=reschedule_request_id,
            status=ProposalStatus.FAILED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message="Outdated proposal version.",
        )

    # Expiration check
    now_utc = datetime.now(timezone.utc)
    if proposal.expires_at < now_utc:
        proposal.status = ProposalStatus.EXPIRED
        return ReschedulingResult(
            reschedule_request_id=reschedule_request_id,
            status=ProposalStatus.EXPIRED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message="Rescheduling proposal has expired.",
        )

    # Idempotency check
    if proposal.status == ProposalStatus.BOOKED:
        return ReschedulingResult(
            reschedule_request_id=reschedule_request_id,
            appointment_id=proposal.appointment_id,
            status=ProposalStatus.BOOKED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            new_start_time=proposal.new_start_time,
            new_end_time=proposal.new_end_time,
            timezone=proposal.timezone,
            message="Appointment is already rescheduled.",
        )

    appt_service = appointment_service or AppointmentService()

    try:
        rescheduled_appt = appt_service.atomic_reschedule_appointment(
            appointment_id=proposal.appointment_id,
            patient_id=patient_id,
            new_slot_id=proposal.new_slot_id,
        )
        proposal.status = ProposalStatus.BOOKED
        return ReschedulingResult(
            reschedule_request_id=reschedule_request_id,
            appointment_id=rescheduled_appt.id,
            status=ProposalStatus.BOOKED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            new_start_time=proposal.new_start_time,
            new_end_time=proposal.new_end_time,
            timezone=proposal.timezone,
            message=f"Appointment successfully rescheduled to {proposal.new_start_time.strftime('%Y-%m-%d %H:%M UTC')}.",
        )
    except ValueError as e:
        err_msg = str(e)
        if "no longer available" in err_msg or "conflict" in err_msg:
            proposal.status = ProposalStatus.SLOT_UNAVAILABLE
            return ReschedulingResult(
                reschedule_request_id=reschedule_request_id,
                status=ProposalStatus.SLOT_UNAVAILABLE,
                doctor_name=proposal.doctor_name,
                patient_name=proposal.patient_name,
                message=f"Rescheduling failed: {err_msg}",
            )
        proposal.status = ProposalStatus.FAILED
        return ReschedulingResult(
            reschedule_request_id=reschedule_request_id,
            status=ProposalStatus.FAILED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message=f"Rescheduling failed: {err_msg}",
        )
