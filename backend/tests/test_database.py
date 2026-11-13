import pytest
from sqlalchemy import select
from app.database.session import async_session_factory
from app.models.entities import Subject, Document, DocumentChunk
from app.database.fts import search_fts, index_chunk_fts, delete_document_fts


@pytest.mark.asyncio
async def test_seeded_subjects():
    async with async_session_factory() as session:
        result = await session.execute(select(Subject))
        subjects = result.scalars().all()
        assert len(subjects) >= 5
        names = [s.name for s in subjects]
        assert "Mathematics" in names
        assert "Data Structures & Algorithms" in names
        assert "Operating Systems" in names


@pytest.mark.asyncio
async def test_fts5_indexing_and_search():
    async with async_session_factory() as session:
        # Index sample chunk
        chunk_id = "test-chunk-xylophonic-quasar"
        doc_id = "test-doc-xylophonic-quasar"
        content = "XylophonicQuasar algorithm finds the shortest path in a weighted graph."
        await index_chunk_fts(session, chunk_id, doc_id, content)

        # Search for keyword
        results = await search_fts(session, "XylophonicQuasar", limit=5)
        assert len(results) > 0
        assert results[0]["chunk_id"] == chunk_id
        assert results[0]["document_id"] == doc_id
        assert "XylophonicQuasar" in results[0]["snippet"]

        # Clean up
        await delete_document_fts(session, doc_id)
        results_after = await search_fts(session, "XylophonicQuasar", limit=5)
        assert len(results_after) == 0
