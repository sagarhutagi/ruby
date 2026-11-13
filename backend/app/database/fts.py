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
    session: AsyncSession, query_str: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """Query FTS5 using BM25 ranking."""
    # Sanitize query string for FTS5 syntax
    sanitized = "".join(c for c in query_str if c.isalnum() or c.isspace()).strip()
    if not sanitized:
        return []

    # Use MATCH with bm25 ranking
    sql = text(
        """
        SELECT chunk_id, document_id, bm25(chunk_fts) as rank, snippet(chunk_fts, 2, '<b>', '</b>', '...', 32) as match_snippet
        FROM chunk_fts
        WHERE chunk_fts MATCH :query
        ORDER BY rank
        LIMIT :limit;
        """
    )
    result = await session.execute(sql, {"query": sanitized, "limit": limit})
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
