import time
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import Document, DocumentChunk
from app.database.fts import search_fts
from app.services.retrieval.chroma_store import chroma_store
from app.services.retrieval.embeddings import embedding_manager, BaseEmbeddingProvider

logger = logging.getLogger("ruby.retrieval.hybrid")

ACADEMIC_ACRONYMS: Dict[str, str] = {
    "os": "operating systems process memory scheduling",
    "dsa": "data structures algorithms time complexity",
    "cn": "computer networks tcp ip packets protocol",
    "dlcd": "digital logic computer design boolean circuits flip-flops",
    "dbms": "database management system sql relational normalization",
    "oop": "object oriented programming inheritance polymorphism",
    "ai": "artificial intelligence machine learning neural networks",
}


class RetrievedChunk(BaseModel):
    """Ranked retrieved chunk with complete provenance and hybrid score attribution."""
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    token_count: int = 0
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    sheet_name: Optional[str] = None
    cell_range: Optional[str] = None
    section_heading: Optional[str] = None
    dense_rank: Optional[int] = None
    sparse_rank: Optional[int] = None
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rrf_score: float = 0.0
    matched_by: str = "unknown"  # "both", "dense", "sparse"
    snippet: Optional[str] = None


class HybridRetrievalResult(BaseModel):
    """Complete retrieval response including diagnostics and timing telemetry."""
    query: str
    expanded_query: Optional[str] = None
    total_found: int
    dense_count: int
    sparse_count: int
    dense_latency_ms: float
    sparse_latency_ms: float
    total_latency_ms: float
    chunks: List[RetrievedChunk] = Field(default_factory=list)


class HybridRetriever:
    """
    Academic Hybrid Retriever combining Dense Vector Search (ChromaDB)
    and Sparse BM25 Keyword Search (SQLite FTS5) via Reciprocal Rank Fusion (RRF).
    """

    def __init__(self, k_constant: int = 60):
        self.k_constant = k_constant

    def expand_query(self, query: str) -> str:
        """Appends contextual academic terms if query matches known academic acronyms."""
        tokens = query.lower().split()
        expanded_parts = [query]
        for t in tokens:
            cleaned = "".join(c for c in t if c.isalnum())
            if cleaned in ACADEMIC_ACRONYMS:
                expanded_parts.append(ACADEMIC_ACRONYMS[cleaned])
        return " ".join(expanded_parts)

    async def search(
        self,
        session: AsyncSession,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
        subject_id: Optional[str] = None,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        provider: Optional[BaseEmbeddingProvider] = None,
    ) -> HybridRetrievalResult:
        start_time = time.perf_counter()
        query = query.strip()
        if not query:
            return HybridRetrievalResult(
                query=query,
                total_found=0,
                dense_count=0,
                sparse_count=0,
                dense_latency_ms=0.0,
                sparse_latency_ms=0.0,
                total_latency_ms=0.0,
                chunks=[],
            )

        # Subject filtering: resolve documents under this subject if specified
        target_doc_ids = set(document_ids) if document_ids else None
        if subject_id:
            sub_stmt = select(Document.id).where(Document.subject_id == subject_id)
            sub_docs = set((await session.execute(sub_stmt)).scalars().all())
            if target_doc_ids is not None:
                target_doc_ids = target_doc_ids.intersection(sub_docs)
            else:
                target_doc_ids = sub_docs

        effective_doc_ids = list(target_doc_ids) if target_doc_ids is not None else None

        # 1. Sparse BM25 Search via SQLite FTS5
        sparse_start = time.perf_counter()
        fts_limit = max(top_k * 3, 20)
        sparse_raw = await search_fts(
            session=session,
            query_str=query,
            limit=fts_limit,
            document_ids=effective_doc_ids,
        )
        sparse_latency_ms = (time.perf_counter() - sparse_start) * 1000.0

        # 2. Dense Vector Search via ChromaDB
        dense_start = time.perf_counter()
        active_provider = provider or embedding_manager.get_provider()
        query_vector = await active_provider.embed_query(query)

        where_filter: Optional[Dict[str, Any]] = None
        if effective_doc_ids is not None:
            if len(effective_doc_ids) == 1:
                where_filter = {"document_id": effective_doc_ids[0]}
            elif len(effective_doc_ids) > 1:
                where_filter = {"document_id": {"$in": effective_doc_ids}}
            else:
                # Filter matched 0 documents
                where_filter = {"document_id": "__NO_MATCH__"}

        dense_raw = chroma_store.query_similar(
            query_embedding=query_vector,
            top_k=max(top_k * 3, 20),
            where_filter=where_filter,
        )
        dense_latency_ms = (time.perf_counter() - dense_start) * 1000.0

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF score = sum(weight / (k + rank))
        scores: Dict[str, Dict[str, Any]] = {}

        # Add Dense Rankings (1-indexed)
        for rank_idx, item in enumerate(dense_raw, start=1):
            c_id = item["chunk_id"]
            rrf_contrib = dense_weight / (self.k_constant + rank_idx)
            scores[c_id] = {
                "chunk_id": c_id,
                "document_id": item["metadata"].get("document_id", ""),
                "dense_rank": rank_idx,
                "sparse_rank": None,
                "dense_score": float(item["similarity"]),
                "sparse_score": 0.0,
                "rrf_score": rrf_contrib,
                "matched_by": "dense",
                "snippet": None,
            }

        # Add Sparse Rankings (1-indexed)
        for rank_idx, item in enumerate(sparse_raw, start=1):
            c_id = item["chunk_id"]
            rrf_contrib = sparse_weight / (self.k_constant + rank_idx)
            # In SQLite FTS5 bm25, lower rank is better (often negative). Convert to positive relative score.
            bm25_raw = float(item["rank"])
            normalised_bm25 = 1.0 / (1.0 + abs(bm25_raw))

            if c_id in scores:
                scores[c_id]["sparse_rank"] = rank_idx
                scores[c_id]["sparse_score"] = normalised_bm25
                scores[c_id]["rrf_score"] += rrf_contrib
                scores[c_id]["matched_by"] = "both"
                if item["snippet"]:
                    scores[c_id]["snippet"] = item["snippet"]
            else:
                scores[c_id] = {
                    "chunk_id": c_id,
                    "document_id": item["document_id"],
                    "dense_rank": None,
                    "sparse_rank": rank_idx,
                    "dense_score": 0.0,
                    "sparse_score": normalised_bm25,
                    "rrf_score": rrf_contrib,
                    "matched_by": "sparse",
                    "snippet": item["snippet"],
                }

        # 4. Sort all items by RRF score descending
        fused = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
        top_fused = fused[:top_k]

        if not top_fused:
            total_latency_ms = (time.perf_counter() - start_time) * 1000.0
            return HybridRetrievalResult(
                query=query,
                expanded_query=self.expand_query(query) if query != self.expand_query(query) else None,
                total_found=0,
                dense_count=len(dense_raw),
                sparse_count=len(sparse_raw),
                dense_latency_ms=round(dense_latency_ms, 2),
                sparse_latency_ms=round(sparse_latency_ms, 2),
                total_latency_ms=round(total_latency_ms, 2),
                chunks=[],
            )

        # 5. Hydrate canonical chunk data & document titles from SQLite
        top_chunk_ids = [item["chunk_id"] for item in top_fused]
        stmt = (
            select(DocumentChunk, Document.title)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(DocumentChunk.id.in_(top_chunk_ids))
        )
        rows = (await session.execute(stmt)).all()
        hydrated_map = {c.id: (c, doc_title) for c, doc_title in rows}

        results: List[RetrievedChunk] = []
        for item in top_fused:
            c_id = item["chunk_id"]
            if c_id in hydrated_map:
                chunk_model, doc_title = hydrated_map[c_id]
                results.append(
                    RetrievedChunk(
                        chunk_id=c_id,
                        document_id=chunk_model.document_id,
                        document_title=doc_title,
                        content=chunk_model.content,
                        token_count=chunk_model.token_count,
                        page_number=chunk_model.page_number,
                        slide_number=chunk_model.slide_number,
                        sheet_name=chunk_model.sheet_name,
                        cell_range=chunk_model.cell_range,
                        section_heading=chunk_model.section_heading,
                        dense_rank=item["dense_rank"],
                        sparse_rank=item["sparse_rank"],
                        dense_score=round(item["dense_score"], 4),
                        sparse_score=round(item["sparse_score"], 4),
                        rrf_score=round(item["rrf_score"], 5),
                        matched_by=item["matched_by"],
                        snippet=item["snippet"],
                    )
                )

        total_latency_ms = (time.perf_counter() - start_time) * 1000.0
        return HybridRetrievalResult(
            query=query,
            expanded_query=self.expand_query(query) if query != self.expand_query(query) else None,
            total_found=len(results),
            dense_count=len(dense_raw),
            sparse_count=len(sparse_raw),
            dense_latency_ms=round(dense_latency_ms, 2),
            sparse_latency_ms=round(sparse_latency_ms, 2),
            total_latency_ms=round(total_latency_ms, 2),
            chunks=results,
        )


hybrid_retriever = HybridRetriever()
