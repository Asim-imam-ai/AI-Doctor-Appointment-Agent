"""IngestionPipeline: Validates, normalizes, chunks, embeds, and stores approved knowledge documents."""

import hashlib
import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from app.models import (
    KnowledgeCategory,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentStatus,
)
from app.rag.embeddings_service import EmbeddingsService
from app.repositories import (
    get_knowledge_chunk_repository,
    get_knowledge_document_repository,
)
from app.repositories.base import (
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)

logger = logging.getLogger(__name__)

ALLOWED_FILE_EXTENSIONS = {".md", ".txt"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB limit
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50


class IngestionPipeline:
    """Pipeline for ingesting approved application knowledge files into vector storage."""

    def __init__(
        self,
        doc_repo: Optional[KnowledgeDocumentRepository] = None,
        chunk_repo: Optional[KnowledgeChunkRepository] = None,
        embeddings_service: Optional[EmbeddingsService] = None,
    ):
        self.doc_repo = doc_repo or get_knowledge_document_repository()
        self.chunk_repo = chunk_repo or get_knowledge_chunk_repository()
        self.embeddings_service = embeddings_service or EmbeddingsService()

    def validate_file(self, file_path: Path) -> Tuple[str, str]:
        """Validates file existence, format extension, size, and encoding."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.suffix.lower() not in ALLOWED_FILE_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension '{file_path.suffix}'. Allowed: {ALLOWED_FILE_EXTENSIONS}"
            )

        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File size {file_path.stat().st_size} bytes exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES} bytes."
            )

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise ValueError(f"Failed to read file with UTF-8 encoding: {e}") from e

        if not content.strip():
            raise ValueError("Document content cannot be empty.")

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return content, content_hash

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> List[str]:
        """Splits document text into overlapping semantic chunks deterministically."""
        cleaned = re.sub(r"\r\n", "\n", text).strip()
        paragraphs = cleaned.split("\n\n")

        chunks = []
        current_chunk = ""

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue

            if len(current_chunk) + len(p) + 2 <= chunk_size:
                current_chunk = (
                    f"{current_chunk}\n\n{p}".strip() if current_chunk else p
                )
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(p) > chunk_size:
                    # Split long paragraph by words
                    words = p.split(" ")
                    sub_chunk = ""
                    for w in words:
                        if len(sub_chunk) + len(w) + 1 <= chunk_size:
                            sub_chunk = f"{sub_chunk} {w}".strip()
                        else:
                            chunks.append(sub_chunk)
                            sub_chunk = w
                    if sub_chunk:
                        current_chunk = sub_chunk
                else:
                    current_chunk = p

        if current_chunk:
            chunks.append(current_chunk)

        # Apply overlap if chunks exist
        if overlap > 0 and len(chunks) > 1:
            overlapped_chunks = [chunks[0]]
            for i in range(1, len(chunks)):
                prev_tail = (
                    chunks[i - 1][-overlap:]
                    if len(chunks[i - 1]) >= overlap
                    else chunks[i - 1]
                )
                overlapped_chunks.append(f"{prev_tail}\n{chunks[i]}")
            return overlapped_chunks

        return chunks

    def ingest_file(
        self,
        file_path: Path,
        title: str,
        category: KnowledgeCategory,
        version: str = "1.0",
        metadata: Optional[dict] = None,
    ) -> KnowledgeDocumentModel:
        """Ingests an approved document file, creating document and chunk embeddings."""
        content, content_hash = self.validate_file(file_path)

        # Deactivate existing active document with same content hash or title/version
        existing_docs = self.doc_repo.list_documents(category=category)
        for doc in existing_docs:
            if doc.content_hash == content_hash or doc.title.lower() == title.lower():
                logger.info(f"Deactivating obsolete version of document {doc.id}")
                self.doc_repo.update_status(doc.id, KnowledgeDocumentStatus.INACTIVE)

        doc_model = KnowledgeDocumentModel(
            title=title,
            category=category,
            version=version,
            status=KnowledgeDocumentStatus.ACTIVE,
            source=file_path.name,
            content_hash=content_hash,
            metadata=metadata or {},
        )

        saved_doc = self.doc_repo.create(doc_model)

        # Split content into chunks
        text_chunks = self.chunk_text(content)
        chunk_models = []

        for idx, raw_chunk in enumerate(text_chunks):
            embedding = self.embeddings_service.embed_text(raw_chunk)
            c_model = KnowledgeChunkModel(
                document_id=saved_doc.id,
                chunk_index=idx,
                content=raw_chunk,
                embedding=embedding,
                metadata={
                    "title": title,
                    "category": category.value,
                    "version": version,
                    "source": file_path.name,
                },
            )
            chunk_models.append(c_model)

        self.chunk_repo.save_chunks(chunk_models)
        logger.info(
            f"Successfully ingested file '{file_path.name}' into document {saved_doc.id} with {len(chunk_models)} chunks."
        )
        return saved_doc
