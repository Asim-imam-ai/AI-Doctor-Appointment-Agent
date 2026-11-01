"""FastAPI routes for Appointment Booking, Cancellation, Rescheduling, and HITL approval workflow."""

import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.agentic.workflows.booking.graph import build_appointment_booking_graph
from app.agentic.workflows.cancellation.graph import (
    build_appointment_cancellation_graph,
)
from app.agentic.workflows.rescheduling.graph import (
    build_appointment_rescheduling_graph,
)
from app.api.dependencies.auth import AuthenticatedPatient, get_current_patient
from app.api.schemas.appointment import AppointmentResponse
from app.api.schemas.booking_agent import (
    ApproveBookingApiResponse,
    BookingApprovalDecision,
    BookingApprovalRequest,
    PrepareBookingApiRequest,
    PrepareBookingApiResponse,
)
from app.api.schemas.management_agent import (
    ApproveCancellationApiResponse,
    ApproveReschedulingApiResponse,
    CancellationApprovalDecision,
    CancellationApprovalRequest,
    PrepareCancellationApiRequest,
    PrepareCancellationApiResponse,
    PrepareReschedulingApiRequest,
    PrepareReschedulingApiResponse,
    ReschedulingApprovalDecision,
    ReschedulingApprovalRequest,
)
from app.domain.proposals.booking import get_pending_proposal
from app.domain.proposals.management import (
    get_pending_cancellation_proposal,
    get_pending_rescheduling_proposal,
)
from app.infrastructure.db.repositories import get_proposal_repository
from app.infrastructure.db.services import get_appointment_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=List[AppointmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List appointments for patient",
)
async def list_patient_appointments_endpoint(
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    """Retrieves all appointments for the authenticated patient."""
    try:
        return get_appointment_service().list_patient_appointments(patient.id)
    except Exception as e:
        logger.exception("Error listing appointments")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list appointments.",
        ) from e


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get appointment details by ID",
)
async def get_appointment_endpoint(
    appointment_id: uuid.UUID,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    """Retrieves appointment details by ID."""
    appt = get_appointment_service().get_appointment(appointment_id)
    if not appt or appt.patient_id != patient.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment '{appointment_id}' not found.",
        )
    return appt


@router.post(
    "/prepare",
    response_model=PrepareBookingApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Prepare a booking proposal (Requires HITL approval before final mutation)",
)
async def prepare_booking_endpoint(
    request: PrepareBookingApiRequest,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    """Invokes booking graph to prepare a structured BookingProposal."""
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request message cannot be empty.",
        )

    try:
        graph = build_appointment_booking_graph()
        initial_state = {
            "user_message": request.message,
            "patient_id": patient.id,
            "doctor_id": request.doctor_id,
            "slot_id": request.slot_id,
            "user_timezone": request.user_timezone,
            "reason": request.reason,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "proposal_version": 1,
            "metadata": {},
        }

        final_state = graph.invoke(initial_state)

        proposal = final_state.get("booking_proposal")
        err = final_state.get("error")
        msg = (
            "Unable to prepare booking proposal."
            if err
            else final_state.get("response") or "Proposal prepared successfully."
        )

        return PrepareBookingApiResponse(
            request_id=proposal.booking_request_id if proposal else "N/A",
            status="error" if err else "success",
            message=msg,
            proposal=proposal,
            requires_approval=True,
            error="Proposal preparation failed." if err else None,
        )
    except Exception as e:
        logger.exception("Error preparing booking proposal")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to prepare booking proposal.",
        ) from e


@router.post(
    "/{booking_request_id}/approve",
    response_model=ApproveBookingApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve or reject a pending booking proposal (HITL Boundary)",
)
async def approve_booking_endpoint(
    booking_request_id: str,
    request: BookingApprovalRequest,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    """Processes explicit Human-In-The-Loop approval or rejection decision."""
    if booking_request_id != request.booking_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path booking_request_id does not match payload body.",
        )

    proposal = get_pending_proposal(
        booking_request_id, patient.id, get_proposal_repository()
    )
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking proposal '{booking_request_id}' not found or expired.",
        )

    if request.decision == BookingApprovalDecision.REJECT:
        get_proposal_repository().reject(
            uuid.UUID(booking_request_id), patient.id, request.proposal_version
        )
        return ApproveBookingApiResponse(
            request_id=booking_request_id,
            status="success",
            message="Booking proposal rejected by user. No appointment was created.",
        )

    try:
        graph = build_appointment_booking_graph()
        resume_state = {
            "booking_proposal": proposal,
            "approval_status": "APPROVED",
            "proposal_version": request.proposal_version,
            "patient_id": patient.id,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "metadata": {},
        }

        final_state = graph.invoke(resume_state)

        result = final_state.get("booking_result")
        err = final_state.get("error")
        msg = (
            "Booking operation failed."
            if err
            else final_state.get("response") or "Booking process completed."
        )

        return ApproveBookingApiResponse(
            request_id=booking_request_id,
            status="error"
            if err or (result and result.status.value != "BOOKED")
            else "success",
            message=msg,
            booking_result=result,
            error="Booking operation failed." if err else None,
        )
    except Exception as e:
        logger.exception("Error in booking approval execution")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to execute booking approval.",
        ) from e


@router.post(
    "/cancel/prepare",
    response_model=PrepareCancellationApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Prepare a cancellation proposal (Requires HITL approval)",
)
async def prepare_cancellation_endpoint(
    request: PrepareCancellationApiRequest,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    """Invokes cancellation graph to prepare a structured CancellationProposal."""
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request message cannot be empty.",
        )

    try:
        graph = build_appointment_cancellation_graph()
        initial_state = {
            "user_message": request.message,
            "patient_id": patient.id,
            "appointment_id": request.appointment_id,
            "user_timezone": request.user_timezone,
            "reason": request.reason,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "proposal_version": 1,
            "metadata": {},
        }

        final_state = graph.invoke(initial_state)

        proposal = final_state.get("cancellation_proposal")
        err = final_state.get("error")
        msg = (
            "Unable to prepare cancellation proposal."
            if err
            else final_state.get("response")
            or "Cancellation proposal prepared successfully."
        )

        return PrepareCancellationApiResponse(
            request_id=proposal.cancellation_request_id if proposal else "N/A",
            status="error" if err else "success",
            message=msg,
            proposal=proposal,
            requires_approval=True,
            error="Proposal preparation failed." if err else None,
        )
    except Exception as e:
        logger.exception("Error preparing cancellation proposal")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to prepare cancellation proposal.",
        ) from e


@router.post(
    "/cancel/{cancellation_request_id}/approve",
    response_model=ApproveCancellationApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve or reject a pending cancellation proposal (HITL Boundary)",
)
async def approve_cancellation_endpoint(
    cancellation_request_id: str,
    request: CancellationApprovalRequest,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    """Processes explicit HITL approval/rejection for cancellation."""
    if cancellation_request_id != request.cancellation_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path cancellation_request_id does not match payload body.",
        )

    proposal = get_pending_cancellation_proposal(
        cancellation_request_id, patient.id, get_proposal_repository()
    )
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cancellation proposal '{cancellation_request_id}' not found or expired.",
        )

    if request.decision == CancellationApprovalDecision.REJECT:
        get_proposal_repository().reject(
            uuid.UUID(cancellation_request_id), patient.id, request.proposal_version
        )
        return ApproveCancellationApiResponse(
            request_id=cancellation_request_id,
            status="success",
            message="Cancellation proposal rejected by user. Appointment remains active.",
        )

    try:
        graph = build_appointment_cancellation_graph()
        resume_state = {
            "cancellation_proposal": proposal,
            "approval_status": "APPROVED",
            "proposal_version": request.proposal_version,
            "patient_id": patient.id,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "metadata": {},
        }

        final_state = graph.invoke(resume_state)

        result = final_state.get("cancellation_result")
        err = final_state.get("error")
        msg = (
            "Cancellation operation failed."
            if err
            else final_state.get("response") or "Cancellation process completed."
        )

        return ApproveCancellationApiResponse(
            request_id=cancellation_request_id,
            status="error"
            if err or (result and result.status.value != "BOOKED")
            else "success",
            message=msg,
            cancellation_result=result,
            error="Cancellation operation failed." if err else None,
        )
    except Exception as e:
        logger.exception("Error in cancellation approval execution")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to execute cancellation approval.",
        ) from e


@router.post(
    "/reschedule/prepare",
    response_model=PrepareReschedulingApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Prepare a rescheduling proposal (Requires HITL approval)",
)
async def prepare_rescheduling_endpoint(
    request: PrepareReschedulingApiRequest,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    """Invokes rescheduling graph to prepare a structured ReschedulingProposal."""
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request message cannot be empty.",
        )

    try:
        graph = build_appointment_rescheduling_graph()
        initial_state = {
            "user_message": request.message,
            "patient_id": patient.id,
            "appointment_id": request.appointment_id,
            "new_slot_id": request.new_slot_id,
            "user_timezone": request.user_timezone,
            "reason": request.reason,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "proposal_version": 1,
            "metadata": {},
        }

        final_state = graph.invoke(initial_state)

        proposal = final_state.get("rescheduling_proposal")
        err = final_state.get("error")
        msg = (
            "Unable to prepare rescheduling proposal."
            if err
            else final_state.get("response")
            or "Rescheduling proposal prepared successfully."
        )

        return PrepareReschedulingApiResponse(
            request_id=proposal.reschedule_request_id if proposal else "N/A",
            status="error" if err else "success",
            message=msg,
            proposal=proposal,
            requires_approval=True,
            error="Proposal preparation failed." if err else None,
        )
    except Exception as e:
        logger.exception("Error preparing rescheduling proposal")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to prepare rescheduling proposal.",
        ) from e


@router.post(
    "/reschedule/{reschedule_request_id}/approve",
    response_model=ApproveReschedulingApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve or reject a pending rescheduling proposal (HITL Boundary)",
)
async def approve_rescheduling_endpoint(
    reschedule_request_id: str,
    request: ReschedulingApprovalRequest,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    """Processes explicit HITL approval/rejection for rescheduling."""
    if reschedule_request_id != request.reschedule_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path reschedule_request_id does not match payload body.",
        )

    proposal = get_pending_rescheduling_proposal(
        reschedule_request_id, patient.id, get_proposal_repository()
    )
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rescheduling proposal '{reschedule_request_id}' not found or expired.",
        )

    if request.decision == ReschedulingApprovalDecision.REJECT:
        get_proposal_repository().reject(
            uuid.UUID(reschedule_request_id), patient.id, request.proposal_version
        )
        return ApproveReschedulingApiResponse(
            request_id=reschedule_request_id,
            status="success",
            message="Rescheduling proposal rejected by user. Original appointment remains active.",
        )

    try:
        graph = build_appointment_rescheduling_graph()
        resume_state = {
            "rescheduling_proposal": proposal,
            "approval_status": "APPROVED",
            "proposal_version": request.proposal_version,
            "patient_id": patient.id,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "metadata": {},
        }

        final_state = graph.invoke(resume_state)

        result = final_state.get("rescheduling_result")
        err = final_state.get("error")
        msg = (
            "Rescheduling operation failed."
            if err
            else final_state.get("response") or "Rescheduling process completed."
        )

        return ApproveReschedulingApiResponse(
            request_id=reschedule_request_id,
            status="error"
            if err or (result and result.status.value != "BOOKED")
            else "success",
            message=msg,
            rescheduling_result=result,
            error="Rescheduling operation failed." if err else None,
        )
    except Exception as e:
        logger.exception("Error in rescheduling approval execution")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to execute rescheduling approval.",
        ) from e
