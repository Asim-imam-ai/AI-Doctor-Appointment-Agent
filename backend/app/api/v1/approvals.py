"""Generic authenticated approval lifecycle endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.auth import AuthenticatedPatient, get_current_patient
from app.api.schemas.approval import ApprovalDecision, ApprovalRequest, ApprovalResponse
from app.core.config import settings
from app.infrastructure.db.repositories import get_proposal_repository

router = APIRouter()


@router.get("/{proposal_id}")
async def get_proposal_endpoint(
    proposal_id: uuid.UUID,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    proposal = get_proposal_repository().get(proposal_id, patient.id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    return proposal


@router.post("/{proposal_id}/decision", response_model=ApprovalResponse)
async def decide_proposal_endpoint(
    proposal_id: uuid.UUID,
    request: ApprovalRequest,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    repository = get_proposal_repository()
    proposal = repository.get(proposal_id, patient.id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    try:
        if request.decision == ApprovalDecision.REJECT:
            result = repository.reject(proposal_id, patient.id, request.version)
            if result.get("status") != "REJECTED":
                raise ValueError("Proposal cannot be rejected.")
        else:
            result = repository.execute(
                proposal_id,
                patient.id,
                request.version,
                settings.CANCELLATION_WINDOW_MINUTES,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=409, detail="Proposal cannot be executed."
        ) from exc
    return ApprovalResponse(
        proposal_id=str(proposal_id),
        status=str(result.get("status", "FAILED")),
        result=result,
    )
