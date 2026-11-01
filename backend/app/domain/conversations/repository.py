"""Conversation persistence contracts."""

import uuid
from datetime import datetime
from typing import Protocol

from app.domain.models import (
    ConversationMessageModel,
    ConversationModel,
    ConversationStatus,
)


class ConversationRepository(Protocol):
    def create(self, conversation: ConversationModel) -> ConversationModel: ...
    def get_by_id(self, conversation_id: uuid.UUID) -> ConversationModel | None: ...
    def list_for_patient(
        self, patient_id: uuid.UUID, limit: int = 50
    ) -> list[ConversationModel]: ...
    def update_summary(
        self, conversation_id: uuid.UUID, summary: str
    ) -> ConversationModel | None: ...
    def update_status(
        self, conversation_id: uuid.UUID, status: ConversationStatus
    ) -> ConversationModel | None: ...
    def touch(self, conversation_id: uuid.UUID, last_message_at: datetime) -> None: ...
    def delete_conversation(self, conversation_id: uuid.UUID) -> bool: ...


class ConversationMessageRepository(Protocol):
    def create(self, message: ConversationMessageModel) -> ConversationMessageModel: ...
    def list_by_conversation(
        self, conversation_id: uuid.UUID, limit: int = 100
    ) -> list[ConversationMessageModel]: ...
    def delete_by_conversation(self, conversation_id: uuid.UUID) -> int: ...
