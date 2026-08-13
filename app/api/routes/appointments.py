"""FastAPI routes for Appointment Booking and HITL approval workflow."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.agents import build_appointment_booking_graph
from app.schemas.booking_agent import (
    ApproveBookingApiResponse,
    BookingApprovalDecision,
    BookingApprovalRequest,
    PrepareBookingApiRequest,
    PrepareBookingApiResponse,
)
from app.tools.booking_proposal import (
    get_pending_proposal,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/prepare",
    response_model=PrepareBookingApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Prepare a booking proposal (Requires HITL approval before final mutation)",
)
async def prepare_booking_endpoint(request: PrepareBookingApiRequest):
    """Invokes booking graph to prepare a structured BookingProposal.

    The operation pauses before final appointment creation, requiring explicit
    HITL approval via `/approve`.
    """
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
    """Processes explicit Human-In-The-Loop approval or rejection decision.

    If APPROVED: revalidates slot availability and performs atomic appointment creation.
    If REJECTED: marks proposal rejected without mutating appointment records.
    """
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

    # Resume graph execution with APPROVED status
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
