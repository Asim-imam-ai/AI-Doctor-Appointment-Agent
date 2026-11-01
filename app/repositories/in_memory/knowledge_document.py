"""In-memory KnowledgeDocument repository implementation."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models import (
    KnowledgeCategory,
    KnowledgeDocumentModel,
    KnowledgeDocumentStatus,
)
from app.repositories.base import KnowledgeDocumentRepository


class InMemoryKnowledgeDocumentRepository(KnowledgeDocumentRepository):
    def __init__(self) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, KnowledgeDocumentModel] = {}

    def create(self, doc: KnowledgeDocumentModel) -> KnowledgeDocumentModel:
        self._storage[doc.id] = doc
        return doc

    def get_by_id(self, doc_id: uuid.UUID) -> Optional[KnowledgeDocumentModel]:
        return self._storage.get(doc_id)

    def get_by_hash(self, content_hash: str) -> Optional[KnowledgeDocumentModel]:
        for d in self._storage.values():
            if d.content_hash == content_hash:
                return d
        return None

    def list_documents(
        self,
        category: Optional[KnowledgeCategory] = None,
        status: Optional[KnowledgeDocumentStatus] = None,
    ) -> List[KnowledgeDocumentModel]:
        res = list(self._storage.values())
        if category:
            res = [d for d in res if d.category == category]
        if status:
            res = [d for d in res if d.status == status]
        return res

    def update_status(
        self, doc_id: uuid.UUID, status: KnowledgeDocumentStatus
    ) -> Optional[KnowledgeDocumentModel]:
        doc = self._storage.get(doc_id)
        if not doc:
            return None
        updated = doc.model_copy(
            update={"status": status, "updated_at": datetime.now(timezone.utc)}
        )
        self._storage[doc_id] = updated
        return updated
