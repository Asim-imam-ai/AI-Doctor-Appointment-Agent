"""EmbeddingsService: Central abstraction for generating text vector embeddings."""

import logging
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service governing vector embedding creation using OpenAI API or deterministic test double."""

    def __init__(self, client: object = None, model: str | None = None):
        self.client = client
        self.model = model or settings.OPENAI_EMBEDDING_MODEL

    def embed_text(self, text: str) -> List[float]:
        """Generates embedding vector for a single text chunk."""
        if not text or not text.strip():
            raise ValueError("Embedding input must not be empty.")

        if self.client is None and not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required for knowledge embeddings.")

        try:
            if self.client is None:
                from openai import OpenAI

                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

            response = self.client.embeddings.create(
                input=text.replace("\n", " "),
                model=self.model,
            )
            return response.data[0].embedding
        except Exception:
            logger.exception("OpenAI embedding generation failed")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a batch of text chunks."""
        return [self.embed_text(t) for t in texts]
