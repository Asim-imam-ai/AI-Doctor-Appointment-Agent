"""Supabase Conversation repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.conversations.repository import ConversationRepository
from app.domain.models import ConversationModel, ConversationStatus
from app.infrastructure.repositories.supabase.base import SupabaseRepository


class SupabaseConversationRepository(SupabaseRepository, ConversationRepository):
    def create(self, conversation: ConversationModel) -> ConversationModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = conversation.model_dump(mode="json")
        res = self.client.table("conversations").insert(data).execute()
        return ConversationModel.model_validate(res.data[0])

    def get_by_id(self, conversation_id: uuid.UUID) -> Optional[ConversationModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("conversations")
            .select("*")
            .eq("id", str(conversation_id))
            .execute()
        )
        if not res.data:
            return None
        return ConversationModel.model_validate(res.data[0])

    def list_for_patient(
        self, patient_id: uuid.UUID, limit: int = 50
    ) -> List[ConversationModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("conversations")
            .select("*")
            .eq("patient_id", str(patient_id))
            .neq("status", "DELETED")
            .order("last_message_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [ConversationModel.model_validate(item) for item in res.data]

    def update_summary(
        self, conversation_id: uuid.UUID, summary: str
    ) -> Optional[ConversationModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("conversations")
            .update(
                {
                    "summary": summary,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", str(conversation_id))
            .execute()
        )
        if not res.data:
            return None
        return ConversationModel.model_validate(res.data[0])

    def update_status(
        self, conversation_id: uuid.UUID, status: ConversationStatus
    ) -> Optional[ConversationModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("conversations")
            .update(
                {
                    "status": status.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", str(conversation_id))
            .execute()
        )
        if not res.data:
            return None
        return ConversationModel.model_validate(res.data[0])

    def delete_conversation(self, conversation_id: uuid.UUID) -> bool:
        res = self.update_status(conversation_id, ConversationStatus.DELETED)
        return res is not None

    def touch(self, conversation_id: uuid.UUID, last_message_at: datetime) -> None:
        self.client.table("conversations").update(
            {
                "last_message_at": last_message_at.isoformat(),
                "updated_at": last_message_at.isoformat(),
            }
        ).eq("id", str(conversation_id)).execute()
