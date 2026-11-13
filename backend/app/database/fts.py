from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def init_fts(session: AsyncSession) -> None:
    """Initialize SQLite FTS5 virtual table for document chunks."""
    await session.execute(
        text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
                chunk_id UNINDEXED,
                document_id UNINDEXED,
                content,
                tokenize = 'porter unicode61'
            );
            """
        )
    )
    await session.commit()


async def index_chunk_fts(
    session: AsyncSession, chunk_id: str, document_id: str, content: str
) -> None:
    """Index or re-index a single chunk in SQLite FTS5."""
    # Delete existing chunk if present to prevent duplicates
    await session.execute(
        text("DELETE FROM chunk_fts WHERE chunk_id = :chunk_id;"),
        {"chunk_id": chunk_id},
    )
    await session.execute(
        text(
            """
            INSERT INTO chunk_fts(chunk_id, document_id, content)
            VALUES(:chunk_id, :document_id, :content);
            """
        ),
        {"chunk_id": chunk_id, "document_id": document_id, "content": content},
    )
    await session.commit()


async def search_fts(
    session: AsyncSession,
    query_str: str,
    limit: int = 10,
    document_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Query FTS5 using BM25 ranking, optionally filtering by document_ids."""
    # Sanitize query string for FTS5 syntax
    sanitized = "".join(c for c in query_str if c.isalnum() or c.isspace()).strip()
    if not sanitized:
        return []

    # Format multi-word query into OR or AND match for robust retrieval
    # In FTS5, terms separated by spaces match exact conjunction. Let's keep spaces or OR logic.
    query_terms = [t for t in sanitized.split() if len(t) > 1]
    if not query_terms:
        match_expr = sanitized
    else:
        # Match any of the key terms (OR) with higher weight for all terms
        match_expr = " OR ".join(query_terms)

    params: Dict[str, Any] = {"query": match_expr, "limit": limit}

    if document_ids:
        # Generate parameterised IN clause
        placeholders = [f":doc_{i}" for i in range(len(document_ids))]
        for i, doc_id in enumerate(document_ids):
            params[f"doc_{i}"] = doc_id
        doc_filter = f"AND document_id IN ({', '.join(placeholders)})"
    else:
        doc_filter = ""

    sql = text(
        f"""
        SELECT chunk_id, document_id, bm25(chunk_fts) as rank, snippet(chunk_fts, 2, '<b>', '</b>', '...', 32) as match_snippet
        FROM chunk_fts
        WHERE chunk_fts MATCH :query
        {doc_filter}
        ORDER BY rank
        LIMIT :limit;
        """
    )
    result = await session.execute(sql, params)
    rows = result.fetchall()
    return [
        {
            "chunk_id": row.chunk_id,
            "document_id": row.document_id,
            "rank": float(row.rank),
            "snippet": row.match_snippet,
        }
        for row in rows
    ]



async def delete_document_fts(session: AsyncSession, document_id: str) -> None:
    """Remove all chunks of a document from FTS5."""
    await session.execute(
        text("DELETE FROM chunk_fts WHERE document_id = :document_id;"),
        {"document_id": document_id},
    )
    await session.commit()
