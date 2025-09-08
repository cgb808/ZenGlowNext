"""Pydantic schemas for RAG API and DB rows."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="User natural language question")
    top_k: int = Field(5, ge=1, le=50, description="Number of context chunks")


class RetrievedChunk(BaseModel):
    text: str
    metadata: Optional[Dict[str, Any]] = None
    score: Optional[float] = None


class RAGQueryResponse(BaseModel):
    answer: str
    chunks: List[RetrievedChunk] = []
from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    include_sources: bool = False


class SourceChunk(BaseModel):
    id: Optional[str] = None
    text: Optional[str] = None
    score: Optional[float] = None


class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk] = []
