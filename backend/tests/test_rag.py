import pytest
import math
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.documents.base import ParsedDocument, ParsedChunk
from app.services.retrieval.chunker import StructureAwareChunker
from app.services.retrieval.embeddings import LocalDenseEmbeddingProvider, embedding_manager
from app.services.retrieval.chroma_store import ChromaStore, chroma_store
from app.services.retrieval.hybrid import HybridRetriever, RetrievedChunk
from app.services.retrieval.provenance import ContextAssembler, CitationValidator
from app.models.entities import Document, DocumentChunk, Subject
from app.database.fts import index_chunk_fts, search_fts
from app.workers.ingestion import process_ingestion_job
from app.models.entities import IngestionJob


def test_structure_aware_chunker_preserves_code_and_tables():
    """Verify that structure-aware chunking preserves fenced code and markdown tables without split."""
    content = (
        "# Operating Systems: Process Synchronization\n\n"
        "Here is the Peterson's algorithm implementation:\n\n"
        "```python\n"
        "flag = [False, False]\n"
        "turn = 0\n"
        "def process_0():\n"
        "    flag[0] = True\n"
        "    turn = 1\n"
        "    while flag[1] and turn == 1:\n"
        "        pass\n"
        "    # critical section\n"
        "    flag[0] = False\n"
        "```\n\n"
        "Here is the complexity comparison:\n\n"
        "| Algorithm | Mutex | Progress | Bounded Waiting |\n"
        "|---|---|---|---|\n"
        "| Peterson | Yes | Yes | Yes |\n"
        "| Dekker | Yes | Yes | Yes |\n\n"
        "Conclusion: Both algorithms satisfy all three critical section requirements."
    )

    parsed_doc = ParsedDocument(
        title="OS Synchronization",
        file_type="markdown",
        chunks=[
            ParsedChunk(
                content=content,
                page_number=1,
                section_heading="Process Synchronization",
            )
        ],
        total_pages=1,
    )

    chunker = StructureAwareChunker(max_chunk_chars=400, overlap_chars=50)
    chunks = chunker.chunk_parsed_document(parsed_doc)

    assert len(chunks) >= 2
    # Verify code block was not split across chunks
    code_chunks = [c for c in chunks if "```python" in c.content]
    assert len(code_chunks) == 1
    assert "def process_0():" in code_chunks[0].content
    assert "flag[0] = False" in code_chunks[0].content

    # Verify table is kept intact
    table_chunks = [c for c in chunks if "| Algorithm |" in c.content]
    assert len(table_chunks) == 1
    assert "| Peterson | Yes |" in table_chunks[0].content

    # Provenance preserved
    for c in chunks:
        assert c.page_number == 1
        assert c.section_heading is not None


def test_local_dense_embedding_provider_properties():
    """Verify deterministic 384-dim normalized vector embeddings."""
    provider = LocalDenseEmbeddingProvider(dimension=384)
    assert provider.dimension == 384
    assert provider.provider_name == "local"

    text_a = "Operating systems manage hardware and process scheduling."
    text_b = "Operating systems schedule processes and control memory."
    text_c = "Delicious apple pie baked with cinnamon and sugar."

    vec_a = provider._compute_vector(text_a)
    vec_b = provider._compute_vector(text_b)
    vec_c = provider._compute_vector(text_c)

    # Dimensionality
    assert len(vec_a) == 384
    assert len(vec_b) == 384
    assert len(vec_c) == 384

    # Unit normalisation: norm should be ~1.0
    norm_a = math.sqrt(sum(x * x for x in vec_a))
    assert pytest.approx(norm_a, abs=1e-5) == 1.0

    # Determinism: same text yields exact same vector
    vec_a_again = provider._compute_vector(text_a)
    assert vec_a == vec_a_again

    # Cosine similarity calculation
    def cos_sim(u, v):
        return sum(x * y for x, y in zip(u, v))

    sim_ab = cos_sim(vec_a, vec_b)
    sim_ac = cos_sim(vec_a, vec_c)

    # OS vs OS should be more similar than OS vs Apple Pie
    assert sim_ab > sim_ac


def test_chroma_store_crud(tmp_path: Path):
    """Verify ChromaDB upsert, similarity query, and deletion."""
    test_store = ChromaStore(persist_dir=str(tmp_path / "chroma_test"))
    test_store.rebuild_collection()

    provider = LocalDenseEmbeddingProvider(dimension=384)
    texts = [
        "Dijkstra shortest path algorithm runs in O(V^2) or O((V+E) log V).",
        "Bellman-Ford algorithm handles graphs with negative edge weights.",
        "Convolutional neural networks are effective for image classification.",
    ]
    ids = ["c1", "c2", "c3"]
    vectors = [provider._compute_vector(t) for t in texts]
    metas = [
        {"document_id": "doc_algo", "section_heading": "Dijkstra", "page_number": 10},
        {"document_id": "doc_algo", "section_heading": "Bellman-Ford", "page_number": 12},
        {"document_id": "doc_ml", "section_heading": "CNN", "page_number": 1},
    ]

    test_store.add_chunks(chunk_ids=ids, documents=texts, embeddings=vectors, metadatas=metas)
    assert test_store.count() == 3

    # Query for Dijkstra
    q_vec = provider._compute_vector("Dijkstra shortest path complexity")
    res = test_store.query_similar(query_embedding=q_vec, top_k=2)

    assert len(res) == 2
    assert res[0]["chunk_id"] == "c1"
    assert res[0]["similarity"] > 0.0

    # Filter by document_id
    ml_res = test_store.query_similar(
        query_embedding=q_vec,
        top_k=5,
        where_filter={"document_id": "doc_ml"},
    )
    assert len(ml_res) == 1
    assert ml_res[0]["chunk_id"] == "c3"

    # Delete by document
    test_store.delete_by_document("doc_algo")
    assert test_store.count() == 1

    # Cleanup
    test_store.delete_by_ids(["c3"])
    assert test_store.count() == 0


@pytest.mark.asyncio
async def test_hybrid_search_rrf_scoring(session: AsyncSession, tmp_path: Path):
    """Verify hybrid reciprocal rank fusion combining dense ChromaDB and sparse FTS5."""
    test_store = ChromaStore(persist_dir=str(tmp_path / "hybrid_test"))
    test_store.rebuild_collection()

    # Create dummy document and chunks in SQLite
    doc = Document(
        title="Algorithms and Data Structures",
        filename="dsa.pdf",
        file_path="/tmp/fake_dsa.pdf",
        file_hash="fakehashdsa123",
        file_type="pdf",
        file_size_bytes=1024,
        status="indexed",
    )
    session.add(doc)
    await session.flush()

    chunk1 = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content="Binary search trees provide logarithmic search time in average cases.",
        token_count=12,
        page_number=5,
        section_heading="BST Operations",
    )
    chunk2 = DocumentChunk(
        document_id=doc.id,
        chunk_index=1,
        content="Red-black trees are self-balancing binary search trees ensuring O(log n) worst case.",
        token_count=15,
        page_number=8,
        section_heading="Balanced Trees",
    )
    session.add_all([chunk1, chunk2])
    await session.flush()

    # Index in FTS5
    await index_chunk_fts(session, chunk1.id, doc.id, chunk1.content)
    await index_chunk_fts(session, chunk2.id, doc.id, chunk2.content)

    # Index in ChromaDB
    provider = LocalDenseEmbeddingProvider(dimension=384)
    v1 = provider._compute_vector(chunk1.content)
    v2 = provider._compute_vector(chunk2.content)

    test_store.add_chunks(
        chunk_ids=[chunk1.id, chunk2.id],
        documents=[chunk1.content, chunk2.content],
        embeddings=[v1, v2],
        metadatas=[
            {"document_id": doc.id, "document_title": doc.title, "page_number": 5},
            {"document_id": doc.id, "document_title": doc.title, "page_number": 8},
        ],
    )

    # Execute hybrid search with mock store swapped into global retriever
    import app.services.retrieval.hybrid as hybrid_module
    old_store = hybrid_module.chroma_store
    hybrid_module.chroma_store = test_store

    try:
        retriever = HybridRetriever(k_constant=60)
        results = await retriever.search(
            session=session,
            query="self-balancing red-black tree",
            top_k=5,
            dense_weight=0.5,
            sparse_weight=0.5,
            provider=provider,
        )

        assert results.total_found >= 1
        top_chunk = results.chunks[0]
        assert top_chunk.chunk_id == chunk2.id
        assert top_chunk.document_title == "Algorithms and Data Structures"
        assert top_chunk.page_number == 8
        assert top_chunk.rrf_score > 0.0
        assert top_chunk.matched_by in ("both", "sparse", "dense")
    finally:
        hybrid_module.chroma_store = old_store


def test_context_assembler_and_citation_validator():
    """Verify prompt context assembly and LLM response grounding validation."""
    chunks = [
        RetrievedChunk(
            chunk_id="chk-101",
            document_id="doc-1",
            document_title="Operating Systems Principles",
            content="Deadlock requires four necessary conditions: mutual exclusion, hold and wait, no preemption, and circular wait.",
            page_number=42,
            section_heading="Coffman Conditions",
            dense_score=0.92,
            sparse_score=0.85,
            rrf_score=0.016,
            matched_by="both",
        ),
        RetrievedChunk(
            chunk_id="chk-102",
            document_id="doc-1",
            document_title="Operating Systems Principles",
            content="Banker's algorithm is a deadlock avoidance algorithm created by Edsger Dijkstra.",
            page_number=48,
            section_heading="Deadlock Avoidance",
            dense_score=0.88,
            sparse_score=0.79,
            rrf_score=0.015,
            matched_by="both",
        ),
    ]

    context = ContextAssembler.assemble_context(chunks)
    assert "=== ACADEMIC RESOURCE CONTEXT ===" in context
    assert "Operating Systems Principles" in context
    assert "Page: 42" in context
    assert "Coffman Conditions" in context

    validator = CitationValidator()

    # Grounded response with exact citations and quotes
    good_response = (
        "According to [Doc: Operating Systems Principles, Page: 42], deadlock requires four conditions:\n"
        "mutual exclusion, hold and wait, no preemption, and circular wait.\n"
        "To avoid deadlock, the system can use the \"Banker's algorithm is a deadlock avoidance algorithm\" as noted on [SOURCE #2]."
    )
    report_good = validator.validate_response(good_response, chunks)
    assert report_good.is_grounded is True
    assert report_good.verified_count >= 2
    assert report_good.hallucination_warning is False
    assert len(report_good.quotes) >= 1
    assert report_good.quotes[0].is_present_in_context is True

    # Hallucinated response citing non-existent documents and pages
    bad_response = (
        "In [Doc: Quantum Neural Networks, Page: 999], it is proven that deadlock occurs due to quantum entanglement."
    )
    report_bad = validator.validate_response(bad_response, chunks)
    assert report_bad.is_grounded is False
    assert report_bad.hallucination_warning is True
    assert report_bad.unverified_count >= 1

    # Missing evidence declaration
    absent_response = "I did not find sufficient evidence in the uploaded documents to answer your question."
    report_absent = validator.validate_response(absent_response, chunks)
    assert report_absent.missing_evidence_declared is True
    assert report_absent.is_grounded is True


@pytest.mark.asyncio
async def test_retrieval_api_endpoints(client, session: AsyncSession):
    """Verify HTTP retrieval endpoints /search, /inspect, /stats, and /validate-citation."""
    # Test /api/v1/retrieval/stats
    resp = await client.get("/api/v1/retrieval/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "chroma" in data
    assert "embedding_provider" in data
    assert "dimension" in data

    # Test /api/v1/retrieval/search on empty / seeded database
    search_payload = {
        "query": "operating systems process memory",
        "top_k": 5,
        "dense_weight": 0.5,
        "sparse_weight": 0.5,
    }
    resp = await client.post("/api/v1/retrieval/search", json=search_payload)
    assert resp.status_code == 200
    res_data = resp.json()
    assert "query" in res_data
    assert "chunks" in res_data
    assert "total_latency_ms" in res_data

    # Test /api/v1/retrieval/inspect
    resp = await client.post("/api/v1/retrieval/inspect", json=search_payload)
    assert resp.status_code == 200
    inspect_data = resp.json()
    assert "sample_context" in inspect_data
    assert "fused_chunks" in inspect_data

    # Test /api/v1/retrieval/validate-citation
    val_payload = {
        "response_text": "I did not find sufficient evidence in the uploaded documents.",
        "retrieved_chunks": [],
    }
    resp = await client.post("/api/v1/retrieval/validate-citation", json=val_payload)
    assert resp.status_code == 200
    val_data = resp.json()
    assert val_data["is_grounded"] is True
    assert val_data["missing_evidence_declared"] is True
