"""Authenticated chat endpoint backed by persistent conversation history."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.agentic.orchestrator import build_orchestrator_graph
from app.api.dependencies.auth import AuthenticatedPatient, get_current_patient
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.infrastructure.db.services import get_conversation_service

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    try:
        conversation_id = uuid.UUID(request.session_id)
        conversations = get_conversation_service()
        conversations.get_conversation(patient.id, conversation_id)
        conversations.append_message(
            patient.id, conversation_id, "USER", request.message
        )
        result = build_orchestrator_graph().invoke(
            {
                "user_message": request.message,
                "patient_id": str(patient.id),
            }
        )
        response = result.get("response", "I could not complete that request.")
        conversations.append_message(patient.id, conversation_id, "ASSISTANT", response)
        return ChatResponse(
            session_id=str(conversation_id),
            message=response,
            requires_hitl=bool(result.get("result")),
            action_type=result.get("intent"),
        )
    except (ValueError, KeyError, PermissionError) as exc:
        raise HTTPException(status_code=404, detail="Conversation not found.") from exc
