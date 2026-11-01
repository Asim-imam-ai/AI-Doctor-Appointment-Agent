"""In-memory Conversation repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models import ConversationModel, ConversationStatus
from app.repositories.base import ConversationRepository


class InMemoryConversationRepository(ConversationRepository):
    def __init__(self) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, ConversationModel] = {}

    def create(self, conversation: ConversationModel) -> ConversationModel:
        self._storage[conversation.id] = conversation
        return conversation

    def get_by_id(self, conversation_id: uuid.UUID) -> Optional[ConversationModel]:
        return self._storage.get(conversation_id)

    def list_for_patient(
        self, patient_id: uuid.UUID, limit: int = 50
    ) -> List[ConversationModel]:
        convs = [
            c
            for c in self._storage.values()
            if c.patient_id == patient_id and c.status != ConversationStatus.DELETED
        ]
        convs.sort(key=lambda x: x.last_message_at, reverse=True)
        return convs[:limit]

    def update_summary(
        self, conversation_id: uuid.UUID, summary: str
    ) -> Optional[ConversationModel]:
        c = self._storage.get(conversation_id)
        if not c:
            return None
        updated = c.model_copy(
            update={"summary": summary, "updated_at": datetime.now(timezone.utc)}
        )
        self._storage[conversation_id] = updated
        return updated

    def update_status(
        self, conversation_id: uuid.UUID, status: ConversationStatus
    ) -> Optional[ConversationModel]:
        c = self._storage.get(conversation_id)
        if not c:
            return None
        updated = c.model_copy(
            update={"status": status, "updated_at": datetime.now(timezone.utc)}
        )
        self._storage[conversation_id] = updated
        return updated

    def delete_conversation(self, conversation_id: uuid.UUID) -> bool:
        c = self._storage.get(conversation_id)
        if not c:
            return False
        self.update_status(conversation_id, ConversationStatus.DELETED)
        return True
