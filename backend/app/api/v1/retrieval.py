import time
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services.retrieval.hybrid import hybrid_retriever, HybridRetrievalResult, RetrievedChunk
from app.services.retrieval.provenance import citation_validator, CitationValidationReport, context_assembler
from app.services.retrieval.chroma_store import chroma_store
from app.services.retrieval.embeddings import embedding_manager

logger = logging.getLogger("ruby.api.retrieval")

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Academic search query")
    top_k: int = Field(default=5, ge=1, le=50)
    document_ids: Optional[List[str]] = Field(default=None, description="Scope search to specific document IDs")
    subject_id: Optional[str] = Field(default=None, description="Scope search to a specific academic subject")
    dense_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    sparse_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class CitationValidationRequest(BaseModel):
    response_text: str
    retrieved_chunks: List[RetrievedChunk]


class RetrievalInspectResponse(BaseModel):
    query: str
    expanded_query: Optional[str] = None
    total_found: int
    dense_count: int
    sparse_count: int
    dense_latency_ms: float
    sparse_latency_ms: float
    total_latency_ms: float
    fused_chunks: List[RetrievedChunk]
    sample_context: str


@router.post("/search", response_model=HybridRetrievalResult, summary="Execute Hybrid Search")
async def execute_search(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute hybrid retrieval combining dense vector similarity (ChromaDB)
    and sparse keyword matching (SQLite FTS5 BM25) with Reciprocal Rank Fusion (RRF).
    """
    return await hybrid_retriever.search(
        session=db,
        query=req.query,
        top_k=req.top_k,
        document_ids=req.document_ids,
        subject_id=req.subject_id,
        dense_weight=req.dense_weight,
        sparse_weight=req.sparse_weight,
    )


@router.post("/inspect", response_model=RetrievalInspectResponse, summary="Inspect Hybrid RAG Diagnostics")
async def inspect_search(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Deep diagnostics endpoint showing dense, sparse, and fused RRF rankings,
    telemetry latencies, and the assembled LLM prompt context block.
    """
    res = await hybrid_retriever.search(
        session=db,
        query=req.query,
        top_k=req.top_k,
        document_ids=req.document_ids,
        subject_id=req.subject_id,
        dense_weight=req.dense_weight,
        sparse_weight=req.sparse_weight,
    )

    assembled_context = context_assembler.assemble_context(res.chunks)

    return RetrievalInspectResponse(
        query=res.query,
        expanded_query=res.expanded_query,
        total_found=res.total_found,
        dense_count=res.dense_count,
        sparse_count=res.sparse_count,
        dense_latency_ms=res.dense_latency_ms,
        sparse_latency_ms=res.sparse_latency_ms,
        total_latency_ms=res.total_latency_ms,
        fused_chunks=res.chunks,
        sample_context=assembled_context,
    )


@router.post("/validate-citation", response_model=CitationValidationReport, summary="Validate Response Citation Grounding")
async def validate_citation(req: CitationValidationRequest):
    """
    Inspect LLM response text, verify citation markers against retrieved chunks,
    and verify quote fidelity to detect hallucinations and unsupported claims.
    """
    return citation_validator.validate_response(
        response_text=req.response_text,
        retrieved_chunks=req.retrieved_chunks,
    )


@router.get("/stats", summary="Get Vector and Retrieval Stats")
async def get_retrieval_stats():
    """Returns vector store metrics, active embedding model, and dimensions."""
    provider = embedding_manager.get_provider()
    chroma_info = chroma_store.get_stats()
    return {
        "chroma": chroma_info,
        "embedding_provider": provider.provider_name,
        "embedding_model": provider.model_name,
        "dimension": provider.dimension,
    }
