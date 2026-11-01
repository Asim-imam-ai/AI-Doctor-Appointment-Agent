"""Supabase KnowledgeDocument repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.domain.models import (
    KnowledgeCategory,
    KnowledgeDocumentModel,
    KnowledgeDocumentStatus,
)
from app.domain.repository import KnowledgeDocumentRepository
from app.infrastructure.repositories.supabase.base import SupabaseRepository


class SupabaseKnowledgeDocumentRepository(
    SupabaseRepository, KnowledgeDocumentRepository
):
    def __init__(self, client: Optional[object] = None) -> None:
        super().__init__(client)

    def create(self, doc: KnowledgeDocumentModel) -> KnowledgeDocumentModel:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = doc.model_dump(mode="json")
        res = self.client.table("knowledge_documents").insert(data).execute()
        if res.data:
            return KnowledgeDocumentModel.model_validate(res.data[0])
        return doc

    def get_by_id(self, doc_id: uuid.UUID) -> Optional[KnowledgeDocumentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("knowledge_documents")
            .select("*")
            .eq("id", str(doc_id))
            .execute()
        )
        if res.data:
            return KnowledgeDocumentModel.model_validate(res.data[0])
        return None

    def get_by_hash(self, content_hash: str) -> Optional[KnowledgeDocumentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("knowledge_documents")
            .select("*")
            .eq("content_hash", content_hash)
            .execute()
        )
        if res.data:
            return KnowledgeDocumentModel.model_validate(res.data[0])
        return None

    def list_documents(
        self,
        category: Optional[KnowledgeCategory] = None,
        status: Optional[KnowledgeDocumentStatus] = None,
    ) -> List[KnowledgeDocumentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        query = self.client.table("knowledge_documents").select("*")
        if category:
            query = query.eq("category", category.value)
        if status:
            query = query.eq("status", status.value)
        res = query.execute()
        return [KnowledgeDocumentModel.model_validate(row) for row in (res.data or [])]

    def update_status(
        self, doc_id: uuid.UUID, status: KnowledgeDocumentStatus
    ) -> Optional[KnowledgeDocumentModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("knowledge_documents")
            .update(
                {
                    "status": status.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", str(doc_id))
            .execute()
        )
        if res.data:
            return KnowledgeDocumentModel.model_validate(res.data[0])
        return None
