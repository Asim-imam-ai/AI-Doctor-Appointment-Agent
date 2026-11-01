"""RAG, ingestion, and embedding tests with external providers mocked."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domain.models import (
    KnowledgeCategory,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
)
from app.knowledge.embeddings import EmbeddingsService
from app.knowledge.ingestion import IngestionPipeline
from app.knowledge.retriever import RAGService


class FakeEmbeddings:
    def embed_text(self, text: str, input_type: str = "query") -> list[float]:
        return [0.1] * 1024

    def embed_batch(
        self, texts: list[str], input_type: str = "document"
    ) -> list[list[float]]:
        return [[0.1] * 1024 for _ in texts]


def test_embeddings_use_configured_voyage_client_without_pseudo_fallback():
    response = SimpleNamespace(embeddings=[[0.25] * 1024])
    client = Mock()
    client.embed.return_value = response
    service = EmbeddingsService(client=client, model="voyage-4-large")

    vector = service.embed_text("clinic cancellation policy")
    assert vector == [0.25] * 1024
    client.embed.assert_called_once_with(
        texts=["clinic cancellation policy"],
        model="voyage-4-large",
        input_type="document",
        output_dimension=1024,
    )
    with pytest.raises(ValueError, match="must not be empty"):
        service.embed_text(" ")


def test_embedding_provider_errors_propagate():
    client = Mock()
    client.embed.side_effect = RuntimeError("provider unavailable")
    with pytest.raises(RuntimeError, match="provider unavailable"):
        EmbeddingsService(client=client).embed_text("policy")


def test_ingestion_validates_and_persists_embedded_chunks(tmp_path: Path):
    source = tmp_path / "policy.md"
    source.write_text(
        "# Cancellation\n\nCancel at least one day in advance.", encoding="utf-8"
    )
    documents, chunks = Mock(), Mock()
    documents.list_documents.return_value = []
    saved_doc = KnowledgeDocumentModel(
        title="Cancellation",
        category=KnowledgeCategory.CANCELLATION_POLICY,
        source=source.name,
        content_hash="a" * 64,
    )
    documents.create.side_effect = lambda doc: doc.model_copy(
        update={"id": saved_doc.id}
    )
    pipeline = IngestionPipeline(documents, chunks, FakeEmbeddings())

    created = pipeline.ingest_file(
        source, title="Cancellation", category=KnowledgeCategory.CANCELLATION_POLICY
    )
    assert created.title == "Cancellation"
    docs = chunks.save_chunks.call_args.args[0]
    assert len(docs) == 1
    assert docs[0].embedding == [0.1] * 1024
    assert "one day" in docs[0].content


def test_retriever_uses_vector_repository_and_grounded_llm():
    chunk = KnowledgeChunkModel(
        document_id=__import__("uuid").uuid4(),
        chunk_index=0,
        content="Cancel an appointment at least 24 hours in advance.",
        metadata={
            "title": "Cancellation Policy",
            "source": "policy.md",
            "version": "1",
        },
    )
    repository, llm = Mock(), Mock()
    repository.search_similar_chunks.return_value = [chunk]
    llm.invoke.return_value = SimpleNamespace(
        content="The policy requires 24 hours' notice."
    )
    service = RAGService(repository, Mock(), FakeEmbeddings(), llm=llm)

    answer = service.answer_query("How much notice is needed?")
    assert answer.grounded is True
    assert answer.retrieval_count == 1
    assert answer.sources[0].title == "Cancellation Policy"
    repository.search_similar_chunks.assert_called_once()
    llm.invoke.assert_called_once()


def test_rag_returns_explicit_unavailable_answer_for_no_retrieval():
    repository = Mock()
    repository.search_similar_chunks.return_value = []
    service = RAGService(repository, Mock(), FakeEmbeddings(), llm=Mock())
    answer = service.answer_query("unknown")
    assert answer.grounded is False
    assert answer.retrieval_count == 0
    assert "enough information" in answer.answer
