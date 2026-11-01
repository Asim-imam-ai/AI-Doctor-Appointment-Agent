"""EmbeddingsService: Central abstraction for generating text vector embeddings."""

import logging
import math
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


# Fallback deterministic pseudo-embeddings generator for offline test & CI environments
def _generate_pseudo_embedding(text: str, dim: int = 1536) -> List[float]:
    """Generates a deterministic 1536-dimensional unit vector derived from text content."""
    vec = [0.0] * dim
    for i, char in enumerate(text):
        idx = (ord(char) * (i + 1)) % dim
        vec[idx] += 1.0

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


class EmbeddingsService:
    """Service governing vector embedding creation using OpenAI API or deterministic test double."""

    def __init__(self, client: object = None, model: str = "text-embedding-3-small"):
        self.client = client
        self.model = model

    def embed_text(self, text: str) -> List[float]:
        """Generates embedding vector for a single text chunk."""
        if not text or not text.strip():
            return [0.0] * 1536

        if self.client is None and not settings.OPENAI_API_KEY:
            # Deterministic fallback when OpenAI API key is unconfigured
            return _generate_pseudo_embedding(text)

        try:
            if self.client is None:
                from openai import OpenAI

                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

            response = self.client.embeddings.create(
                input=text.replace("\n", " "),
                model=self.model,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(
                f"OpenAI embedding generation failed, using fallback pseudo-embedding: {e}"
            )
            return _generate_pseudo_embedding(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a batch of text chunks."""
        return [self.embed_text(t) for t in texts]
