"""Contracts for non-aggregate persistence used by memory and knowledge services."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.models import (
    KnowledgeCategory,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentStatus,
    MemoryItemModel,
)


class MemoryRepository(Protocol):
    def create_or_update(self, item: MemoryItemModel) -> MemoryItemModel: ...
    def get_by_id(self, memory_id: uuid.UUID) -> MemoryItemModel | None: ...
    def get_by_key(self, patient_id: uuid.UUID, key: str) -> MemoryItemModel | None: ...
    def list_for_patient(
        self, patient_id: uuid.UUID, active_only: bool = True
    ) -> list[MemoryItemModel]: ...
    def delete_memory(self, memory_id: uuid.UUID) -> bool: ...
    def delete_by_key(self, patient_id: uuid.UUID, key: str) -> bool: ...


class KnowledgeDocumentRepository(Protocol):
    def create(self, doc: KnowledgeDocumentModel) -> KnowledgeDocumentModel: ...
    def get_by_id(self, doc_id: uuid.UUID) -> KnowledgeDocumentModel | None: ...
    def get_by_hash(self, content_hash: str) -> KnowledgeDocumentModel | None: ...
    def list_documents(
        self,
        category: KnowledgeCategory | None = None,
        status: KnowledgeDocumentStatus | None = None,
    ) -> list[KnowledgeDocumentModel]: ...
    def update_status(
        self, doc_id: uuid.UUID, status: KnowledgeDocumentStatus
    ) -> KnowledgeDocumentModel | None: ...


class KnowledgeChunkRepository(Protocol):
    def save_chunks(
        self, chunks: list[KnowledgeChunkModel]
    ) -> list[KnowledgeChunkModel]: ...
    def search_similar_chunks(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        category: KnowledgeCategory | None = None,
        min_similarity: float = 0.0,
    ) -> list[KnowledgeChunkModel]: ...
    def delete_chunks_by_document(self, document_id: uuid.UUID) -> bool: ...
