"""EmbeddingsService: Central abstraction for Voyage AI text embeddings."""

import logging
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Create Voyage retrieval embeddings for documents and search queries."""

    def __init__(self, client: object = None, model: str | None = None):
        self.client = client
        self.model = model or settings.VOYAGE_EMBEDDING_MODEL
        self.dimensions = settings.VOYAGE_EMBEDDING_DIMENSIONS
        if self.dimensions not in {256, 512, 1024, 2048}:
            raise ValueError(
                "VOYAGE_EMBEDDING_DIMENSIONS must be one of 256, 512, 1024, or 2048."
            )

    def _get_client(self) -> object:
        if self.client is None:
            if not settings.VOYAGE_API_KEY:
                raise RuntimeError(
                    "VOYAGE_API_KEY is required for knowledge embeddings."
                )
            import voyageai

            self.client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        return self.client

    def embed_text(self, text: str, input_type: str = "document") -> List[float]:
        """Generate one Voyage embedding for a document chunk or query."""
        return self.embed_batch([text], input_type=input_type)[0]

    def embed_batch(
        self, texts: List[str], input_type: str = "document"
    ) -> List[List[float]]:
        """Generate embeddings in a single Voyage request for a list of texts."""
        if not texts:
            return []
        if len(texts) > 1000:
            raise ValueError("Voyage embedding batches may contain at most 1000 texts.")
        if any(not text or not text.strip() for text in texts):
            raise ValueError("Embedding input must not be empty.")
        if input_type not in {"document", "query"}:
            raise ValueError("Embedding input_type must be 'document' or 'query'.")

        try:
            response = self._get_client().embed(
                texts=[text.replace("\n", " ") for text in texts],
                model=self.model,
                input_type=input_type,
                output_dimension=self.dimensions,
            )
            vectors = response.embeddings
            if len(vectors) != len(texts) or any(
                len(vector) != self.dimensions for vector in vectors
            ):
                raise ValueError(
                    "Voyage returned an embedding with an unexpected count or dimension."
                )
            return vectors
        except Exception:
            logger.exception("Voyage embedding generation failed")
            raise
