"""In-memory KnowledgeChunk repository implementation."""

import uuid
from typing import Dict, List, Optional

from app.models import KnowledgeCategory, KnowledgeChunkModel, KnowledgeDocumentStatus
from app.repositories.base import KnowledgeChunkRepository, KnowledgeDocumentRepository


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class InMemoryKnowledgeChunkRepository(KnowledgeChunkRepository):
    def __init__(self, doc_repo: Optional[KnowledgeDocumentRepository] = None) -> None:
        super().__init__()
        self._storage: Dict[uuid.UUID, KnowledgeChunkModel] = {}
        self.doc_repo = doc_repo

    def save_chunks(
        self, chunks: List[KnowledgeChunkModel]
    ) -> List[KnowledgeChunkModel]:
        for c in chunks:
            self._storage[c.id] = c
        return chunks

    def search_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 4,
        category: Optional[KnowledgeCategory] = None,
        min_similarity: float = 0.0,
    ) -> List[KnowledgeChunkModel]:
        candidates = []
        for chunk in self._storage.values():
            if self.doc_repo:
                doc = self.doc_repo.get_by_id(chunk.document_id)
                if not doc or doc.status != KnowledgeDocumentStatus.ACTIVE:
                    continue
                if category and doc.category != category:
                    continue
            sim = _cosine_similarity(query_embedding, chunk.embedding or [])
            if sim >= min_similarity:
                candidates.append((sim, chunk))
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in candidates[:top_k]]

    def delete_chunks_by_document(self, document_id: uuid.UUID) -> bool:
        to_delete = [
            cid for cid, c in self._storage.items() if c.document_id == document_id
        ]
        for cid in to_delete:
            del self._storage[cid]
        return len(to_delete) > 0
