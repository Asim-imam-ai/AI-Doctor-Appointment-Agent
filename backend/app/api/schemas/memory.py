"""Pydantic schemas for Conversation & Memory API requests and responses."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import ConversationStatus, MemorySource, MemoryType


class CreateConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field("New Conversation", max_length=255)


class ConversationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    title: str
    status: ConversationStatus
    summary: Optional[str] = None
    last_message_at: datetime
    created_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: List[ConversationMessageResponse] = []


class MemoryItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=500)
    source: MemorySource = MemorySource.EXPLICIT_USER
    expires_at: Optional[datetime] = None


class MemoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    memory_type: MemoryType
    key: str
    value: str
    source: MemorySource
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime


class ListConversationsResponse(BaseModel):
    status: str = "success"
    conversations: List[ConversationResponse] = []


class ListMemoriesResponse(BaseModel):
    status: str = "success"
    memories: List[MemoryItemResponse] = []
