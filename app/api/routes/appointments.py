"""FastAPI routes for Appointment Booking, Cancellation, Rescheduling, and HITL approval workflow."""

import logging
import uuid
from typing import List

from fastapi import APIRouter, HTTPException, status

from app.agents import (
    build_appointment_booking_graph,
    build_appointment_cancellation_graph,
    build_appointment_rescheduling_graph,
)
from app.schemas.appointment import AppointmentResponse
from app.schemas.booking_agent import (
    ApproveBookingApiResponse,
    BookingApprovalDecision,
    BookingApprovalRequest,
    PrepareBookingApiRequest,
    PrepareBookingApiResponse,
)
from app.schemas.management_agent import (
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
from app.services import AppointmentService
from app.tools.booking_proposal import get_pending_proposal
from app.tools.management_proposal import (
    get_pending_cancellation_proposal,
    get_pending_rescheduling_proposal,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=List[AppointmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List appointments for patient",
)
async def list_patient_appointments_endpoint(patient_id: uuid.UUID):
    """Retrieves all appointments for the authenticated patient."""
    try:
        service = AppointmentService()
        return service.list_patient_appointments(patient_id)
    except Exception as e:
        logger.error(f"Error listing appointments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list appointments: {str(e)}",
        ) from e


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get appointment details by ID",
)
async def get_appointment_endpoint(appointment_id: uuid.UUID):
    """Retrieves appointment details by ID."""
    service = AppointmentService()
    appt = service.get_appointment(appointment_id)
    if not appt:
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
async def prepare_booking_endpoint(request: PrepareBookingApiRequest):
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
            "patient_id": request.patient_id,
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
        msg = final_state.get("response") or "Proposal prepared successfully."

        return PrepareBookingApiResponse(
            request_id=proposal.booking_request_id if proposal else "N/A",
            status="error" if err else "success",
            message=msg,
            proposal=proposal,
            requires_approval=True,
            error=err,
        )
    except Exception as e:
        logger.error(f"Error preparing booking proposal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while preparing booking proposal: {str(e)}",
        ) from e


@router.post(
    "/{booking_request_id}/approve",
    response_model=ApproveBookingApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve or reject a pending booking proposal (HITL Boundary)",
)
async def approve_booking_endpoint(
    booking_request_id: str, request: BookingApprovalRequest
):
    """Processes explicit Human-In-The-Loop approval or rejection decision."""
    if booking_request_id != request.booking_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path booking_request_id does not match payload body.",
        )

    proposal = get_pending_proposal(booking_request_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking proposal '{booking_request_id}' not found or expired.",
        )

    if request.decision == BookingApprovalDecision.REJECT:
        proposal.status = proposal.status.REJECTED
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
            "patient_id": request.patient_id,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "metadata": {},
        }

        final_state = graph.invoke(resume_state)

        result = final_state.get("booking_result")
        err = final_state.get("error")
        msg = final_state.get("response") or "Booking process completed."

        return ApproveBookingApiResponse(
            request_id=booking_request_id,
            status="error"
            if err or (result and result.status.value != "BOOKED")
            else "success",
            message=msg,
            booking_result=result,
            error=err,
        )
    except Exception as e:
        logger.error(f"Error in approval execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during booking approval execution: {str(e)}",
        ) from e


@router.post(
    "/cancel/prepare",
    response_model=PrepareCancellationApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Prepare a cancellation proposal (Requires HITL approval)",
)
async def prepare_cancellation_endpoint(request: PrepareCancellationApiRequest):
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
            "patient_id": request.patient_id,
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
            final_state.get("response")
            or "Cancellation proposal prepared successfully."
        )

        return PrepareCancellationApiResponse(
            request_id=proposal.cancellation_request_id if proposal else "N/A",
            status="error" if err else "success",
            message=msg,
            proposal=proposal,
            requires_approval=True,
            error=err,
        )
    except Exception as e:
        logger.error(f"Error preparing cancellation proposal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while preparing cancellation proposal: {str(e)}",
        ) from e


@router.post(
    "/cancel/{cancellation_request_id}/approve",
    response_model=ApproveCancellationApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve or reject a pending cancellation proposal (HITL Boundary)",
)
async def approve_cancellation_endpoint(
    cancellation_request_id: str, request: CancellationApprovalRequest
):
    """Processes explicit HITL approval/rejection for cancellation."""
    if cancellation_request_id != request.cancellation_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path cancellation_request_id does not match payload body.",
        )

    proposal = get_pending_cancellation_proposal(cancellation_request_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cancellation proposal '{cancellation_request_id}' not found or expired.",
        )

    if request.decision == CancellationApprovalDecision.REJECT:
        proposal.status = proposal.status.REJECTED
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
            "patient_id": request.patient_id,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "metadata": {},
        }

        final_state = graph.invoke(resume_state)

        result = final_state.get("cancellation_result")
        err = final_state.get("error")
        msg = final_state.get("response") or "Cancellation process completed."

        return ApproveCancellationApiResponse(
            request_id=cancellation_request_id,
            status="error"
            if err or (result and result.status.value != "BOOKED")
            else "success",
            message=msg,
            cancellation_result=result,
            error=err,
        )
    except Exception as e:
        logger.error(f"Error in cancellation approval execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during cancellation approval execution: {str(e)}",
        ) from e


@router.post(
    "/reschedule/prepare",
    response_model=PrepareReschedulingApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Prepare a rescheduling proposal (Requires HITL approval)",
)
async def prepare_rescheduling_endpoint(request: PrepareReschedulingApiRequest):
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
            "patient_id": request.patient_id,
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
            final_state.get("response")
            or "Rescheduling proposal prepared successfully."
        )

        return PrepareReschedulingApiResponse(
            request_id=proposal.reschedule_request_id if proposal else "N/A",
            status="error" if err else "success",
            message=msg,
            proposal=proposal,
            requires_approval=True,
            error=err,
        )
    except Exception as e:
        logger.error(f"Error preparing rescheduling proposal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while preparing rescheduling proposal: {str(e)}",
        ) from e


@router.post(
    "/reschedule/{reschedule_request_id}/approve",
    response_model=ApproveReschedulingApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve or reject a pending rescheduling proposal (HITL Boundary)",
)
async def approve_rescheduling_endpoint(
    reschedule_request_id: str, request: ReschedulingApprovalRequest
):
    """Processes explicit HITL approval/rejection for rescheduling."""
    if reschedule_request_id != request.reschedule_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path reschedule_request_id does not match payload body.",
        )

    proposal = get_pending_rescheduling_proposal(reschedule_request_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rescheduling proposal '{reschedule_request_id}' not found or expired.",
        )

    if request.decision == ReschedulingApprovalDecision.REJECT:
        proposal.status = proposal.status.REJECTED
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
            "patient_id": request.patient_id,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "metadata": {},
        }

        final_state = graph.invoke(resume_state)

        result = final_state.get("rescheduling_result")
        err = final_state.get("error")
        msg = final_state.get("response") or "Rescheduling process completed."

        return ApproveReschedulingApiResponse(
            request_id=reschedule_request_id,
            status="error"
            if err or (result and result.status.value != "BOOKED")
            else "success",
            message=msg,
            rescheduling_result=result,
            error=err,
        )
    except Exception as e:
        logger.error(f"Error in rescheduling approval execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during rescheduling approval execution: {str(e)}",
        ) from e
