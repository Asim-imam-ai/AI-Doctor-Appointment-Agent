"""Supabase KnowledgeChunk repository implementation."""

import logging
import uuid
from typing import List, Optional

from app.models import KnowledgeCategory, KnowledgeChunkModel
from app.repositories.base import KnowledgeChunkRepository

logger = logging.getLogger(__name__)


class SupabaseKnowledgeChunkRepository(KnowledgeChunkRepository):
    def __init__(self, client: Optional[object] = None) -> None:
        super().__init__(client)

    def save_chunks(
        self, chunks: List[KnowledgeChunkModel]
    ) -> List[KnowledgeChunkModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        data = [c.model_dump(mode="json") for c in chunks]
        res = self.client.table("knowledge_chunks").insert(data).execute()
        return [KnowledgeChunkModel.model_validate(row) for row in (res.data or [])]

    def search_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 4,
        category: Optional[KnowledgeCategory] = None,
        min_similarity: float = 0.0,
    ) -> List[KnowledgeChunkModel]:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        # Attempt RPC vector-match first; fall back to plain table scan on error.
        rpc_params = {
            "query_embedding": query_embedding,
            "match_count": top_k,
            "filter_category": category.value if category else None,
        }
        try:
            res = self.client.rpc("match_knowledge_chunks", rpc_params).execute()
            if res.data:
                return [KnowledgeChunkModel.model_validate(row) for row in res.data]
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "match_knowledge_chunks RPC unavailable (%s); falling back to table scan.",
                exc,
            )
        # Fallback: return first top_k chunks without similarity ordering.
        res = self.client.table("knowledge_chunks").select("*").limit(top_k).execute()
        return [KnowledgeChunkModel.model_validate(row) for row in (res.data or [])]

    def delete_chunks_by_document(self, document_id: uuid.UUID) -> bool:
        if not self.client:
            raise RuntimeError("Supabase client is not initialized.")
        res = (
            self.client.table("knowledge_chunks")
            .delete()
            .eq("document_id", str(document_id))
            .execute()
        )
        return bool(res.data)
