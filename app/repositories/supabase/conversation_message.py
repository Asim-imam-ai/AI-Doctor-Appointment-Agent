"""Supabase ConversationMessage repository implementation."""

import uuid
from typing import List

from app.models import ConversationMessageModel
from app.repositories.base import ConversationMessageRepository


class SupabaseConversationMessageRepository(ConversationMessageRepository):
    def create(self, message: ConversationMessageModel) -> ConversationMessageModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = message.model_dump(mode="json")
        res = self.client.table("conversation_messages").insert(data).execute()
        return ConversationMessageModel.model_validate(res.data[0])

    def list_by_conversation(
        self, conversation_id: uuid.UUID, limit: int = 100
    ) -> List[ConversationMessageModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("conversation_messages")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return [ConversationMessageModel.model_validate(item) for item in res.data]

    def delete_by_conversation(self, conversation_id: uuid.UUID) -> int:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("conversation_messages")
            .delete()
            .eq("conversation_id", str(conversation_id))
            .execute()
        )
        return len(res.data) if res.data else 0
