"""FastAPI routes for Knowledge Base & RAG operations."""

import logging
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.models import KnowledgeCategory, KnowledgeDocumentStatus
from app.rag.ingestion_pipeline import IngestionPipeline
from app.rag.rag_service import RAGService
from app.repositories import (
    get_knowledge_chunk_repository,
    get_knowledge_document_repository,
)
from app.schemas.knowledge import (
    IngestDocumentRequest,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSourceSchema,
    ListKnowledgeDocumentsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_rag_service() -> RAGService:
    d_repo = get_knowledge_document_repository()
    c_repo = get_knowledge_chunk_repository()
    return RAGService(chunk_repo=c_repo, doc_repo=d_repo)


def _get_ingestion_pipeline() -> IngestionPipeline:
    d_repo = get_knowledge_document_repository()
    c_repo = get_knowledge_chunk_repository()
    return IngestionPipeline(doc_repo=d_repo, chunk_repo=c_repo)


def _verify_admin_role(x_user_role: Optional[str]) -> None:
    """Enforces authorization check for knowledge ingestion endpoints."""
    if not x_user_role or x_user_role.lower() not in ("admin", "superuser", "system"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Admin access required for knowledge base ingestion/management.",
        )


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search knowledge base and retrieve grounded policy answers",
)
async def search_knowledge_endpoint(request: KnowledgeSearchRequest):
    """Executes grounded RAG search query against approved knowledge base."""
    rag_service = _get_rag_service()

    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty.",
        )

    res = rag_service.answer_query(
        query=request.query,
        category=request.category,
        top_k=request.top_k,
    )

    sources = [
        KnowledgeSourceSchema(
            document_id=s.document_id,
            title=s.title,
            section=s.section,
            source=s.source,
            version=s.version,
        )
        for s in res.sources
    ]

    return KnowledgeSearchResponse(
        answer=res.answer,
        grounded=res.grounded,
        category=res.category,
        retrieval_count=res.retrieval_count,
        sources=sources,
    )


@router.post(
    "/ingest",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest an approved knowledge document (Admin Only)",
)
async def ingest_document_endpoint(
    request: IngestDocumentRequest,
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """Admin-only endpoint for ingesting approved knowledge documents into vector storage."""
    _verify_admin_role(x_user_role)

    pipeline = _get_ingestion_pipeline()

    # Write content to temporary file for pipeline processing
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(request.content)
        tmp_path = Path(tmp.name)

    try:
        doc = pipeline.ingest_file(
            file_path=tmp_path,
            title=request.title,
            category=request.category,
            version=request.version,
        )
        return doc
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@router.get(
    "/documents",
    response_model=ListKnowledgeDocumentsResponse,
    status_code=status.HTTP_200_OK,
    summary="List knowledge documents",
)
async def list_documents_endpoint(
    category: Optional[KnowledgeCategory] = Query(None),
    status_filter: Optional[KnowledgeDocumentStatus] = Query(None, alias="status"),
):
    """Lists registered knowledge documents."""
    doc_repo = get_knowledge_document_repository()
    docs = doc_repo.list_documents(category=category, status=status_filter)
    return ListKnowledgeDocumentsResponse(documents=docs)
