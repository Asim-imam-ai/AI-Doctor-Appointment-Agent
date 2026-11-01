"""Deterministic Read-Only Proposal Tool and Atomic Booking Execution for Phase 5."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from app.models import AvailabilityStatus
from app.schemas.booking_agent import BookingProposal, BookingResult, ProposalStatus
from app.services import (
    AppointmentService,
    AvailabilityService,
    DoctorService,
    PatientService,
)

# Global in-memory storage for pending booking proposals (durable per request_id)
_PENDING_PROPOSALS: Dict[str, BookingProposal] = {}


def create_booking_proposal(
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
    slot_id: uuid.UUID,
    user_timezone: str = "UTC",
    reason: Optional[str] = None,
    ttl_minutes: int = 15,
    patient_service: Optional[PatientService] = None,
    doctor_service: Optional[DoctorService] = None,
    availability_service: Optional[AvailabilityService] = None,
) -> BookingProposal:
    p_service = patient_service or PatientService()
    d_service = doctor_service or DoctorService()
    a_service = availability_service or AvailabilityService()

    patient = p_service.get_patient(patient_id)
    if not patient:
        raise ValueError(f"Patient with ID '{patient_id}' not found.")

    doctor = d_service.get_doctor(doctor_id)
    if not doctor or not doctor.is_active:
        raise ValueError(f"Doctor with ID '{doctor_id}' is not active or found.")

    slots = a_service.get_available_slots(doctor_id)
    target_slot = next((s for s in slots if s.id == slot_id), None)
    if not target_slot or target_slot.status != AvailabilityStatus.AVAILABLE:
        raise ValueError(f"Slot '{slot_id}' is not available for booking.")

    now_utc = datetime.now(timezone.utc)
    request_id = str(uuid.uuid4())

    proposal = BookingProposal(
        booking_request_id=request_id,
        proposal_version=1,
        patient_id=patient_id,
        patient_name=patient.name,
        doctor_id=doctor_id,
        doctor_name=doctor.name,
        slot_id=slot_id,
        start_time=target_slot.start_time,
        end_time=target_slot.end_time,
        timezone=user_timezone,
        clinic_name=doctor.clinic_name,
        reason=reason,
        status=ProposalStatus.PENDING_APPROVAL,
        expires_at=now_utc + timedelta(minutes=ttl_minutes),
        created_at=now_utc,
    )

    _PENDING_PROPOSALS[request_id] = proposal
    return proposal


def get_pending_proposal(booking_request_id: str) -> Optional[BookingProposal]:
    return _PENDING_PROPOSALS.get(booking_request_id)


def execute_atomic_booking(
    booking_request_id: str,
    proposal_version: int,
    patient_id: uuid.UUID,
    appointment_service: Optional[AppointmentService] = None,
) -> BookingResult:
    proposal = _PENDING_PROPOSALS.get(booking_request_id)
    if not proposal:
        return BookingResult(
            booking_request_id=booking_request_id,
            status=ProposalStatus.FAILED,
            doctor_name="Unknown",
            patient_name="Unknown",
            message="Booking proposal not found.",
        )

    # 1. Authorization check
    if proposal.patient_id != patient_id:
        return BookingResult(
            booking_request_id=booking_request_id,
            status=ProposalStatus.FAILED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message="Unauthorized: patient identity mismatch.",
        )

    # 2. Version check
    if proposal.proposal_version != proposal_version:
        return BookingResult(
            booking_request_id=booking_request_id,
            status=ProposalStatus.FAILED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message="Outdated proposal version.",
        )

    # 3. Expiration check
    now_utc = datetime.now(timezone.utc)
    if proposal.expires_at < now_utc:
        proposal.status = ProposalStatus.EXPIRED
        return BookingResult(
            booking_request_id=booking_request_id,
            status=ProposalStatus.EXPIRED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message="Booking proposal has expired. Please request fresh availability.",
        )

    # 4. Idempotency check (if already booked)
    if proposal.status == ProposalStatus.BOOKED:
        return BookingResult(
            booking_request_id=booking_request_id,
            status=ProposalStatus.BOOKED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            start_time=proposal.start_time,
            end_time=proposal.end_time,
            timezone=proposal.timezone,
            message="Appointment is already booked.",
        )

    appt_service = appointment_service or AppointmentService()

    # 5. Slot revalidation & Atomic creation
    try:
        appt = appt_service.atomic_create_appointment_and_update_slot(
            patient_id=proposal.patient_id,
            doctor_id=proposal.doctor_id,
            slot_id=proposal.slot_id,
            start_time=proposal.start_time,
            end_time=proposal.end_time,
            reason=proposal.reason,
        )
        proposal.status = ProposalStatus.BOOKED
        return BookingResult(
            booking_request_id=booking_request_id,
            appointment_id=appt.id,
            status=ProposalStatus.BOOKED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            start_time=proposal.start_time,
            end_time=proposal.end_time,
            timezone=proposal.timezone,
            message=(
                f"Appointment with {proposal.doctor_name} "
                "successfully booked and confirmed."
            ),
        )
    except ValueError as e:
        err_msg = str(e)
        if "no longer available" in err_msg or "conflict" in err_msg:
            proposal.status = ProposalStatus.SLOT_UNAVAILABLE
            return BookingResult(
                booking_request_id=booking_request_id,
                status=ProposalStatus.SLOT_UNAVAILABLE,
                doctor_name=proposal.doctor_name,
                patient_name=proposal.patient_name,
                message=f"Booking failed: {err_msg}",
            )
        proposal.status = ProposalStatus.FAILED
        return BookingResult(
            booking_request_id=booking_request_id,
            status=ProposalStatus.FAILED,
            doctor_name=proposal.doctor_name,
            patient_name=proposal.patient_name,
            message=f"Booking failed: {err_msg}",
        )
