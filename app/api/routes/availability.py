"""FastAPI routes for Doctor Availability operations."""

import logging
import uuid

from fastapi import APIRouter, HTTPException, status

from app.agents import build_doctor_availability_graph
from app.schemas.availability_agent import (
    AvailabilitySearchApiRequest,
    AvailabilitySearchApiResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/search",
    response_model=AvailabilitySearchApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Search for available doctor appointment slots",
)
async def search_availability_endpoint(request: AvailabilitySearchApiRequest):
    """Exposes Doctor Availability LangGraph agent workflow via FastAPI.

    Validates request payload, invokes doctor availability graph, and returns
    structured available slot details.
    """
    request_id = str(uuid.uuid4())

    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request message cannot be empty.",
        )

    try:
        graph = build_doctor_availability_graph()
        initial_state = {
            "user_message": request.message,
            "user_timezone": request.user_timezone,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "metadata": {"request_id": request_id},
        }

        final_state = graph.invoke(initial_state)

        slots = []
        if final_state.get("tool_results"):
            slots = final_state["tool_results"].slots

        response_msg = final_state.get("response") or "Availability search completed."
        err = final_state.get("error")

        return AvailabilitySearchApiResponse(
            request_id=request_id,
            status="error" if err else "success",
            message=response_msg,
            slots=slots,
            error=err,
        )

    except Exception as e:
        logger.error(f"Error in availability search endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing availability search request.",
        ) from e
