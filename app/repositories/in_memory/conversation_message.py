"""In-memory ConversationMessage repository implementation."""

import uuid
from typing import Dict, List

from app.models import ConversationMessageModel
from app.repositories.base import ConversationMessageRepository


class InMemoryConversationMessageRepository(ConversationMessageRepository):
    def __init__(self) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, ConversationMessageModel] = {}

    def create(self, message: ConversationMessageModel) -> ConversationMessageModel:
        self._storage[message.id] = message
        return message

    def list_by_conversation(
        self, conversation_id: uuid.UUID, limit: int = 100
    ) -> List[ConversationMessageModel]:
        msgs = [
            m for m in self._storage.values() if m.conversation_id == conversation_id
        ]
        msgs.sort(key=lambda x: x.created_at)
        return msgs[:limit]

    def delete_by_conversation(self, conversation_id: uuid.UUID) -> int:
        count = 0
        for m_id, m in list(self._storage.items()):
            if m.conversation_id == conversation_id:
                del self._storage[m_id]
                count += 1
        return count
