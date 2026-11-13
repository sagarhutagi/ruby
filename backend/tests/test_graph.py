import os
import shutil
import tempfile
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import Subject, Document, DocumentChunk, KnowledgeNode, KnowledgeEdge
from app.services.graph.service import knowledge_graph_service
from app.services.obsidian.exporter import obsidian_exporter


@pytest.mark.asyncio
async def test_node_and_edge_crud(session: AsyncSession):
    """Test creating, querying, updating, and deleting nodes and edges."""
    # 1. Create Nodes
    node1 = await knowledge_graph_service.create_node(
        session=session,
        label="Virtual Memory",
        node_type="concept",
        description="Memory management technique providing abstraction of secondary storage.",
    )
    assert node1.id is not None
    assert node1.label == "Virtual Memory"

    node2 = await knowledge_graph_service.create_node(
        session=session,
        label="Paging",
        node_type="concept",
        description="Memory allocation scheme allowing non-contiguous physical address space.",
    )

    # Duplicate creation returns existing node
    node1_dup = await knowledge_graph_service.create_node(session=session, label="Virtual Memory")
    assert node1_dup.id == node1.id

    # 2. Create Edge
    edge = await knowledge_graph_service.create_edge(
        session=session,
        source_id=node2.id,
        target_id=node1.id,
        relationship_type="PREREQUISITE_OF",
    )
    assert edge is not None
    assert edge.source_id == node2.id
    assert edge.target_id == node1.id

    # 3. Query Graph
    graph = await knowledge_graph_service.get_graph(session=session)
    assert len(graph["nodes"]) >= 2
    assert len(graph["edges"]) >= 1

    # 4. Update Node
    updated = await knowledge_graph_service.update_node(
        session=session,
        node_id=node1.id,
        description="Updated virtual memory description.",
        is_verified=True,
    )
    assert updated.description == "Updated virtual memory description."
    assert updated.is_verified is True

    # 5. Delete Edge
    del_edge_ok = await knowledge_graph_service.delete_edge(session=session, edge_id=edge.id)
    assert del_edge_ok is True

    # 6. Delete Node
    del_node_ok = await knowledge_graph_service.delete_node(session=session, node_id=node1.id)
    assert del_node_ok is True
    await knowledge_graph_service.delete_node(session=session, node_id=node2.id)


@pytest.mark.asyncio
async def test_prerequisite_chain(session: AsyncSession):
    """Test prerequisite dependency resolution."""
    # Build chain: Paging (A) -> Page Tables (B) -> Virtual Memory (C)
    node_a = await knowledge_graph_service.create_node(session=session, label="Paging Concept")
    node_b = await knowledge_graph_service.create_node(session=session, label="Page Tables")
    node_c = await knowledge_graph_service.create_node(session=session, label="Demand Paging")

    # A is prerequisite of B, B is prerequisite of C
    await knowledge_graph_service.create_edge(
        session=session, source_id=node_a.id, target_id=node_b.id, relationship_type="PREREQUISITE_OF"
    )
    await knowledge_graph_service.create_edge(
        session=session, source_id=node_b.id, target_id=node_c.id, relationship_type="PREREQUISITE_OF"
    )

    # Get prerequisites for Demand Paging (C)
    res = await knowledge_graph_service.get_prerequisite_chain(session=session, target_node_id=node_c.id)
    assert res["prerequisites_count"] == 2
    labels = [n["label"] for n in res["study_order"]]
    # A should come before B
    assert labels == ["Paging Concept", "Page Tables"]

    # Cleanup
    await knowledge_graph_service.delete_node(session=session, node_id=node_a.id)
    await knowledge_graph_service.delete_node(session=session, node_id=node_b.id)
    await knowledge_graph_service.delete_node(session=session, node_id=node_c.id)


@pytest.mark.asyncio
async def test_concept_extraction_from_document(session: AsyncSession):
    """Test automatic academic concept and relation extraction from parsed document chunks."""
    # Seed or fetch subject
    subject = await session.scalar(select(Subject).where(Subject.name == "Database Systems"))
    if not subject:
        subject = Subject(name="Database Systems", description="CS301 Relational DBs")
        session.add(subject)
        await session.commit()
        await session.refresh(subject)

    doc = Document(
        title="Transaction Processing Principles",
        filename="transactions.md",
        file_path="/data/documents/transactions.md",
        file_type="markdown",
        file_size_bytes=1024,
        file_hash="hash_txn_123",
        status="indexed",
        subject_id=subject.id,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    chunk1 = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content="# ACID Properties\n\n**Atomicity** ensures all operations complete or none do. "
        "Two-Phase Locking is an algorithm for serializable concurrency control.",
        token_count=35,
        section_heading="# ACID Properties",
    )
    chunk2 = DocumentChunk(
        document_id=doc.id,
        chunk_index=1,
        content="## Serializability\n\n$$Conflict = T1 \\cap T2$$\n"
        "Serializability refers to the execution schedule yielding identical results to sequential execution.",
        token_count=30,
        section_heading="## Serializability",
    )
    session.add_all([chunk1, chunk2])
    await session.commit()

    # Run extraction
    result = await knowledge_graph_service.extract_concepts_from_document(
        session=session, document_id=doc.id
    )

    assert result["document_id"] == doc.id
    assert result["nodes_created"] >= 3
    assert result["edges_created"] >= 2

    # Verify extracted nodes are marked unverified
    graph = await knowledge_graph_service.get_graph(session=session, subject_id=subject.id)
    assert any(n["is_verified"] is False for n in graph["nodes"])


@pytest.mark.asyncio
async def test_obsidian_notes_and_export(session: AsyncSession):
    """Test Obsidian Markdown generation, [[wikilinks]], conflict preview, and vault export."""
    # Create test nodes and link
    n1 = await knowledge_graph_service.create_node(
        session=session,
        label="Dijkstra Algorithm",
        node_type="concept",
        description="Greedy algorithm for single-source shortest path on weighted graphs.",
    )
    n2 = await knowledge_graph_service.create_node(
        session=session,
        label="Shortest Path Problem",
        node_type="topic",
        description="Finding a path between two vertices such that total weight is minimized.",
    )
    await knowledge_graph_service.create_edge(
        session=session,
        source_id=n1.id,
        target_id=n2.id,
        relationship_type="RELATED_TO",
    )

    # Generate notes in memory
    notes = await obsidian_exporter.generate_vault_notes(session=session)
    assert len(notes) >= 3  # n1, n2, + _RUBY_INDEX.md

    # Check note content
    dijkstra_note = next(n for n in notes if n["label"] == "Dijkstra Algorithm")
    assert "---" in dijkstra_note["content"]
    assert 'title: "Dijkstra Algorithm"' in dijkstra_note["content"]
    assert "[[Shortest Path Problem]]" in dijkstra_note["content"]

    # Test conflict preview & export in temporary directory
    temp_vault = tempfile.mkdtemp()
    try:
        preview1 = await obsidian_exporter.preview_export(session=session, vault_path=temp_vault)
        assert preview1["total_notes"] >= 3
        assert len(preview1["files_to_create"]) >= 3
        assert preview1["has_conflicts"] is False

        # First export
        res1 = await obsidian_exporter.export_to_vault(
            session=session, vault_path=temp_vault, allow_overwrite=False
        )
        assert res1["written_count"] >= 3
        assert res1["skipped_count"] == 0

        # Second preview: should detect existing files (conflicts)
        preview2 = await obsidian_exporter.preview_export(session=session, vault_path=temp_vault)
        assert preview2["has_conflicts"] is True
        assert len(preview2["files_to_overwrite"]) >= 3

        # Second export with allow_overwrite=False: should skip
        res2 = await obsidian_exporter.export_to_vault(
            session=session, vault_path=temp_vault, allow_overwrite=False
        )
        assert res2["skipped_count"] >= 3

        # Second export with allow_overwrite=True: should rewrite
        res3 = await obsidian_exporter.export_to_vault(
            session=session, vault_path=temp_vault, allow_overwrite=True
        )
        assert res3["written_count"] >= 3

        # Test ZIP stream generation
        zip_buf = await obsidian_exporter.create_vault_zip(session=session)
        assert zip_buf.getbuffer().nbytes > 0
    finally:
        shutil.rmtree(temp_vault, ignore_errors=True)
        await knowledge_graph_service.delete_node(session=session, node_id=n1.id)
        await knowledge_graph_service.delete_node(session=session, node_id=n2.id)


@pytest.mark.asyncio
async def test_graph_api_endpoints(client: AsyncClient, session: AsyncSession):
    """Test HTTP API endpoints for Knowledge Graph and Obsidian export."""
    # 1. Create Node
    node_res = await client.post(
        "/api/v1/graph/nodes",
        json={
            "label": "Fourier Transform",
            "node_type": "formula",
            "description": "Decomposes functions into frequency components.",
            "position_x": 120.0,
            "position_y": 80.0,
        },
    )
    assert node_res.status_code == 201
    node_id = node_res.json()["id"]

    # 2. Update Node
    patch_res = await client.patch(
        f"/api/v1/graph/nodes/{node_id}",
        json={"is_verified": False, "description": "Updated Fourier description."},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_verified"] is False

    # 3. Get Graph
    get_res = await client.get("/api/v1/graph")
    assert get_res.status_code == 200
    graph_data = get_res.json()
    assert any(n["id"] == node_id for n in graph_data["nodes"])

    # 4. Preview Obsidian Export
    prev_res = await client.post(
        "/api/v1/graph/obsidian/preview",
        json={"vault_path": "./data/test_obsidian_vault"},
    )
    assert prev_res.status_code == 200
    assert "total_notes" in prev_res.json()

    # 5. Export ZIP download
    zip_res = await client.get("/api/v1/graph/obsidian/export-zip")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"

    # Cleanup
    del_res = await client.delete(f"/api/v1/graph/nodes/{node_id}")
    assert del_res.status_code == 204
