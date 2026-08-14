"""Pydantic schemas for Knowledge & RAG API operations."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import KnowledgeCategory, KnowledgeDocumentStatus


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    category: Optional[KnowledgeCategory] = None
    top_k: int = Field(default=4, ge=1, le=20)


class KnowledgeSourceSchema(BaseModel):
    document_id: str
    title: str
    section: Optional[str] = None
    source: str
    version: str


class KnowledgeSearchResponse(BaseModel):
    status: str = "success"
    answer: str
    grounded: bool
    category: Optional[str] = None
    retrieval_count: int
    sources: List[KnowledgeSourceSchema] = []


class IngestDocumentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    category: KnowledgeCategory
    version: str = Field(default="1.0", max_length=50)
    content: str = Field(..., min_length=1, max_length=100000)
    file_name: str = Field(default="policy.md", max_length=255)


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    category: KnowledgeCategory
    version: str
    status: KnowledgeDocumentStatus
    source: str
    content_hash: str
    created_at: datetime


class ListKnowledgeDocumentsResponse(BaseModel):
    status: str = "success"
    documents: List[KnowledgeDocumentResponse] = []
