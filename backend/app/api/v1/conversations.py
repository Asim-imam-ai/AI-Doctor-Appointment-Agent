"""Authenticated conversation and preference endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.auth import AuthenticatedPatient, get_current_patient
from app.api.schemas.memory import (
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
    ListConversationsResponse,
    ListMemoriesResponse,
    MemoryItemRequest,
    MemoryItemResponse,
)
from app.infrastructure.db.services import get_conversation_service, get_memory_service

router = APIRouter()


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation_endpoint(
    request: CreateConversationRequest,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    return get_conversation_service().create_conversation(
        patient.id, title=request.title or "New Conversation"
    )


@router.get("", response_model=ListConversationsResponse)
async def list_conversations_endpoint(
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    return ListConversationsResponse(
        conversations=get_conversation_service().list_conversations(patient.id)
    )


@router.get("/memory", response_model=ListMemoriesResponse)
async def list_memories_endpoint(
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    return ListMemoriesResponse(
        memories=get_memory_service().get_user_memories(patient.id, active_only=True)
    )


@router.post("/memory", response_model=MemoryItemResponse, status_code=201)
async def create_memory_endpoint(
    request: MemoryItemRequest,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    try:
        return get_memory_service().save_preference(
            patient_id=patient.id,
            key=request.key,
            value=request.value,
            source=request.source,
            expires_at=request.expires_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/memory/{memory_id}")
async def delete_memory_endpoint(
    memory_id: uuid.UUID,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    if not get_memory_service().delete_memory(patient.id, memory_id):
        raise HTTPException(status_code=404, detail="Memory item not found.")
    return {"status": "success", "message": "Memory item deleted successfully."}


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_endpoint(
    conversation_id: uuid.UUID,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    service = get_conversation_service()
    try:
        conversation = service.get_conversation(patient.id, conversation_id)
        messages = service.get_messages(patient.id, conversation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found.") from exc
    return ConversationDetailResponse(
        id=conversation.id,
        patient_id=conversation.patient_id,
        title=conversation.title,
        status=conversation.status,
        summary=conversation.summary,
        last_message_at=conversation.last_message_at,
        created_at=conversation.created_at,
        messages=messages,
    )


@router.delete("/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: uuid.UUID,
    patient: AuthenticatedPatient = Depends(get_current_patient),
):
    try:
        deleted = get_conversation_service().delete_conversation(
            patient.id, conversation_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found.") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"status": "success", "message": "Conversation deleted successfully."}
