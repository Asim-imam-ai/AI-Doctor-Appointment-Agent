"""FastAPI routes for Conversation & Memory operations."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.memory.conversation_service import ConversationService
from app.memory.memory_service import MemoryService
from app.repositories import (
    get_conversation_message_repository,
    get_conversation_repository,
    get_memory_repository,
)
from app.schemas.memory import (
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
    ListConversationsResponse,
    ListMemoriesResponse,
    MemoryItemRequest,
    MemoryItemResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_services():
    c_repo = get_conversation_repository()
    cm_repo = get_conversation_message_repository()
    m_repo = get_memory_repository()

    conv_service = ConversationService(c_repo, cm_repo)
    mem_service = MemoryService(m_repo)
    return conv_service, mem_service


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session for a patient",
)
async def create_conversation_endpoint(
    request: CreateConversationRequest,
    x_patient_id: Optional[str] = Header(None, alias="X-Patient-ID"),
):
    """Creates a conversation session. Validates patient ownership via X-Patient-ID header if present."""
    conv_service, _ = _get_services()
    patient_id = request.patient_id

    if x_patient_id:
        try:
            header_patient_id = uuid.UUID(x_patient_id)
            if header_patient_id != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized: Patient ID mismatch.",
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Patient-ID header format.",
            ) from e

    conv = conv_service.create_conversation(
        patient_id, title=request.title or "New Conversation"
    )
    return conv


@router.get(
    "/conversations",
    response_model=ListConversationsResponse,
    status_code=status.HTTP_200_OK,
    summary="List active conversations for a patient",
)
async def list_conversations_endpoint(
    patient_id: uuid.UUID = Query(...),
    x_patient_id: Optional[str] = Header(None, alias="X-Patient-ID"),
):
    """Lists conversations for an authenticated patient."""
    conv_service, _ = _get_services()

    if x_patient_id:
        try:
            if uuid.UUID(x_patient_id) != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized cross-patient access attempt.",
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Patient-ID header.",
            ) from e

    conversations = conv_service.list_conversations(patient_id)
    return ListConversationsResponse(conversations=conversations)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation detail and messages",
)
async def get_conversation_endpoint(
    conversation_id: uuid.UUID,
    patient_id: uuid.UUID = Query(...),
    x_patient_id: Optional[str] = Header(None, alias="X-Patient-ID"),
):
    """Retrieves conversation detail and message history enforcing patient ownership."""
    conv_service, _ = _get_services()

    if x_patient_id:
        try:
            if uuid.UUID(x_patient_id) != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized cross-patient access attempt.",
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Patient-ID header.",
            ) from e

    try:
        conv = conv_service.get_conversation(patient_id, conversation_id)
        messages = conv_service.get_messages(patient_id, conversation_id)
        return ConversationDetailResponse(
            id=conv.id,
            patient_id=conv.patient_id,
            title=conv.title,
            status=conv.status,
            summary=conv.summary,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
            messages=messages,
        )
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Archive/Delete a conversation",
)
async def delete_conversation_endpoint(
    conversation_id: uuid.UUID,
    patient_id: uuid.UUID = Query(...),
    x_patient_id: Optional[str] = Header(None, alias="X-Patient-ID"),
):
    """Deletes a conversation enforcing patient ownership."""
    conv_service, _ = _get_services()

    if x_patient_id:
        try:
            if uuid.UUID(x_patient_id) != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized cross-patient access attempt.",
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Patient-ID header.",
            ) from e

    try:
        success = conv_service.delete_conversation(patient_id, conversation_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or already deleted.",
            )
        return {"status": "success", "message": "Conversation deleted successfully."}
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get(
    "/memory",
    response_model=ListMemoriesResponse,
    status_code=status.HTTP_200_OK,
    summary="List patient memory preferences",
)
async def list_memories_endpoint(
    patient_id: uuid.UUID = Query(...),
    x_patient_id: Optional[str] = Header(None, alias="X-Patient-ID"),
):
    """Lists active user memory preferences for an authorized patient."""
    _, mem_service = _get_services()

    if x_patient_id:
        try:
            if uuid.UUID(x_patient_id) != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized cross-patient memory access attempt.",
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Patient-ID header.",
            ) from e

    memories = mem_service.get_user_memories(patient_id, active_only=True)
    return ListMemoriesResponse(memories=memories)


@router.post(
    "/memory",
    response_model=MemoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save or update a patient memory preference",
)
async def create_memory_endpoint(
    request: MemoryItemRequest,
    x_patient_id: Optional[str] = Header(None, alias="X-Patient-ID"),
):
    """Saves a structured memory item for a patient enforcing allowlists and policy validation."""
    _, mem_service = _get_services()

    if x_patient_id:
        try:
            if uuid.UUID(x_patient_id) != request.patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized cross-patient memory write attempt.",
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Patient-ID header.",
            ) from e

    try:
        saved = mem_service.save_preference(
            patient_id=request.patient_id,
            key=request.key,
            value=request.value,
            source=request.source,
            expires_at=request.expires_at,
        )
        return saved
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.delete(
    "/memory/{memory_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a memory preference item",
)
async def delete_memory_endpoint(
    memory_id: uuid.UUID,
    patient_id: uuid.UUID = Query(...),
    x_patient_id: Optional[str] = Header(None, alias="X-Patient-ID"),
):
    """Deactivates/Deletes a memory preference enforcing ownership."""
    _, mem_service = _get_services()

    if x_patient_id:
        try:
            if uuid.UUID(x_patient_id) != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized cross-patient memory deletion attempt.",
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Patient-ID header.",
            ) from e

    try:
        success = mem_service.delete_memory(patient_id, memory_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory item not found or already deleted.",
            )
        return {"status": "success", "message": "Memory item deleted successfully."}
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
