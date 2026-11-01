"""FastAPI routes for Doctor Discovery operations."""

import logging
import uuid

from fastapi import APIRouter, HTTPException, status

from app.agentic.workflows.doctor_discovery.graph import build_doctor_discovery_graph
from app.api.schemas.doctor_discovery import (
    DoctorSearchApiRequest,
    DoctorSearchApiResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/search",
    response_model=DoctorSearchApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Search for doctors using natural language or filter criteria",
)
async def search_doctors_endpoint(request: DoctorSearchApiRequest):
    """Exposes Doctor Discovery LangGraph agent workflow via FastAPI.

    Validates request payload, invokes doctor discovery graph, and returns
    structured doctor search results.
    """
    request_id = str(uuid.uuid4())

    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request message cannot be empty.",
        )

    try:
        graph = build_doctor_discovery_graph()
        initial_state = {
            "user_message": request.message,
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "metadata": {"request_id": request_id},
        }

        final_state = graph.invoke(initial_state)

        doctors = []
        if final_state.get("tool_results"):
            doctors = final_state["tool_results"].doctors

        response_msg = final_state.get("response") or "Doctor search completed."
        err = final_state.get("error")

        return DoctorSearchApiResponse(
            request_id=request_id,
            status="error" if err else "success",
            message=response_msg,
            doctors=doctors,
            error=err,
        )

    except Exception as e:
        logger.error(f"Error in doctor discovery endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing doctor search request.",
        ) from e
