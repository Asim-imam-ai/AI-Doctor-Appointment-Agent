"""ConversationService: Business logic layer for persistent conversations, messaging, and summaries."""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.conversations.models import (
    ConversationMessageModel,
    ConversationModel,
    ConversationStatus,
)
from app.domain.conversations.repository import (
    ConversationMessageRepository,
    ConversationRepository,
)

logger = logging.getLogger(__name__)


class ConversationService:
    """Service governing conversation creation, message history persistence, summaries, and ownership."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: ConversationMessageRepository,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo

    def create_conversation(
        self, patient_id: uuid.UUID, title: str = "New Conversation"
    ) -> ConversationModel:
        """Creates a new conversation session for an authenticated patient."""
        conv = ConversationModel(
            patient_id=patient_id,
            title=title.strip()[:255],
            status=ConversationStatus.ACTIVE,
        )
        saved = self.conversation_repo.create(conv)
        logger.info(f"Created conversation {saved.id} for patient {patient_id}")
        return saved

    def get_conversation(
        self, patient_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> ConversationModel:
        """Retrieves a conversation verifying patient ownership."""
        conv = self.conversation_repo.get_by_id(conversation_id)
        if not conv or conv.status == ConversationStatus.DELETED:
            raise KeyError(f"Conversation with ID '{conversation_id}' not found.")
        if conv.patient_id != patient_id:
            logger.warning(
                f"Unauthorized conversation access: auth_patient={patient_id}, owner={conv.patient_id}"
            )
            raise PermissionError(
                "Unauthorized: You do not have permission to access this conversation."
            )
        return conv

    def list_conversations(
        self, patient_id: uuid.UUID, limit: int = 50
    ) -> List[ConversationModel]:
        """Lists active/archived conversations for an authenticated patient."""
        return self.conversation_repo.list_for_patient(patient_id, limit=limit)

    def append_message(
        self,
        patient_id: uuid.UUID,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> ConversationMessageModel:
        """Appends a message to an owned conversation and updates last_message_at."""
        conv = self.get_conversation(patient_id, conversation_id)

        msg = ConversationMessageModel(
            conversation_id=conv.id,
            role=role,
            content=content[:4000],
            metadata=metadata or {},
        )
        saved_msg = self.message_repo.create(msg)

        self.conversation_repo.touch(conv.id, datetime.now(timezone.utc))
        return saved_msg

    def get_messages(
        self, patient_id: uuid.UUID, conversation_id: uuid.UUID, limit: int = 100
    ) -> List[ConversationMessageModel]:
        """Retrieves messages for an owned conversation."""
        self.get_conversation(patient_id, conversation_id)
        return self.message_repo.list_by_conversation(conversation_id, limit=limit)

    def update_summary(
        self, patient_id: uuid.UUID, conversation_id: uuid.UUID, summary: str
    ) -> ConversationModel:
        """Updates the conversation summary enforcing ownership."""
        self.get_conversation(patient_id, conversation_id)
        updated = self.conversation_repo.update_summary(conversation_id, summary)
        if not updated:
            raise RuntimeError("Failed to update conversation summary.")
        return updated

    def archive_conversation(
        self, patient_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> ConversationModel:
        """Archives an active conversation."""
        self.get_conversation(patient_id, conversation_id)
        updated = self.conversation_repo.update_status(
            conversation_id, ConversationStatus.ARCHIVED
        )
        if not updated:
            raise RuntimeError("Failed to archive conversation.")
        return updated

    def delete_conversation(
        self, patient_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> bool:
        """Soft-deletes a conversation and associated message records."""
        self.get_conversation(patient_id, conversation_id)
        self.message_repo.delete_by_conversation(conversation_id)
        return self.conversation_repo.delete_conversation(conversation_id)
