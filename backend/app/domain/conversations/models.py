"""Conversation domain models and lifecycle states."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConversationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class ConversationModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    patient_id: uuid.UUID
    title: str = Field(default="New Conversation", max_length=255)
    status: ConversationStatus = ConversationStatus.ACTIVE
    summary: Optional[str] = None
    last_message_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ConversationMessageModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: uuid.UUID
    role: str = Field(..., max_length=50)
    content: str = Field(..., max_length=4000)
    metadata: Optional[dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
