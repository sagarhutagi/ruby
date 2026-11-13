import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.memory.service import memory_service
from app.models.entities import Memory, MemoryAuditEvent


@pytest.mark.asyncio
async def test_memory_crud_lifecycle(client: AsyncClient, session: AsyncSession):
    """Verify memory creation, listing, updating, pinning, and hard deletion."""
    # 1. Create a memory
    create_res = await client.post(
        "/api/v1/memories",
        json={
            "content": "Prefers mathematical derivations in rigorous LaTeX notation.",
            "memory_type": "profile",
            "importance_score": 0.9,
            "confidence": 1.0,
            "is_pinned": True,
        },
    )
    assert create_res.status_code == 201
    mem = create_res.json()
    mem_id = mem["id"]
    assert mem["memory_type"] == "profile"
    assert mem["is_pinned"] is True
    assert mem["importance_score"] == 0.9

    # 2. List memories with filter
    list_res = await client.get("/api/v1/memories?memory_type=profile")
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(m["id"] == mem_id for m in items)

    # 3. Update memory
    patch_res = await client.patch(
        f"/api/v1/memories/{mem_id}",
        json={"importance_score": 0.95, "content": "Always format all math in KaTeX LaTeX."},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["importance_score"] == 0.95
    assert updated["content"] == "Always format all math in KaTeX LaTeX."

    # 4. Toggle Pin
    pin_res = await client.post(f"/api/v1/memories/{mem_id}/pin")
    assert pin_res.status_code == 200
    assert pin_res.json()["is_pinned"] is False

    # 5. Verify audit trail has 'created', 'updated', and 'unpinned'
    audit_res = await client.get(f"/api/v1/memories/audit/trail?memory_id={mem_id}")
    assert audit_res.status_code == 200
    audits = audit_res.json()
    actions = [a["action"] for a in audits]
    assert "created" in actions
    assert "updated" in actions
    assert "unpinned" in actions

    # 6. Delete memory (verifying hard purge)
    del_res = await client.delete(f"/api/v1/memories/{mem_id}")
    assert del_res.status_code == 204

    # Verify memory is no longer in list
    check_res = await client.get("/api/v1/memories")
    assert not any(m["id"] == mem_id for m in check_res.json())


@pytest.mark.asyncio
async def test_semantic_memory_search(client: AsyncClient, session: AsyncSession):
    """Verify vector similarity search across memories."""
    # Create two semantic memories
    res1 = await client.post(
        "/api/v1/memories",
        json={
            "content": "Dijkstra's shortest path algorithm operates on non-negative weighted graphs.",
            "memory_type": "semantic",
            "importance_score": 0.8,
        },
    )
    mem1_id = res1.json()["id"]

    res2 = await client.post(
        "/api/v1/memories",
        json={
            "content": "Baking sourdough bread requires flour, water, salt, and wild yeast starter.",
            "memory_type": "semantic",
            "importance_score": 0.3,
        },
    )
    mem2_id = res2.json()["id"]

    try:
        # Search for algorithm
        search_res = await client.post(
            "/api/v1/memories/search",
            json={"query": "shortest path graph algorithm", "top_k": 2},
        )
        assert search_res.status_code == 200
        results = search_res.json()
        assert len(results) >= 1
        top_match = results[0]
        assert top_match["memory"]["id"] == mem1_id
        assert top_match["similarity"] > 0.0
    finally:
        await client.delete(f"/api/v1/memories/{mem1_id}")
        await client.delete(f"/api/v1/memories/{mem2_id}")


@pytest.mark.asyncio
async def test_candidate_memory_extraction_and_contradiction(client: AsyncClient, session: AsyncSession):
    """Verify automated extraction of profile and episodic memories, duplicate detection, and contradiction flags."""
    # Create existing baseline profile memory
    base_res = await client.post(
        "/api/v1/memories",
        json={
            "content": "I prefer detailed derivations for every mathematical step.",
            "memory_type": "profile",
            "importance_score": 0.8,
        },
    )
    base_id = base_res.json()["id"]

    try:
        extract_text = (
            "I prefer brief summaries rather than long derivations.\n"
            "I struggled with the Bankers algorithm deadlock condition in the exam."
        )

        extract_res = await client.post(
            "/api/v1/memories/extract-candidates",
            json={"text": extract_text},
        )
        assert extract_res.status_code == 200
        candidates = extract_res.json()
        assert len(candidates) == 2

        # Candidate 1: contradiction with "detailed" vs "brief"
        c1 = next(c for c in candidates if "brief" in c["content"])
        assert c1["memory_type"] == "profile"
        assert c1["is_contradiction"] is True

        # Candidate 2: episodic difficulty
        c2 = next(c for c in candidates if "Bankers" in c["content"])
        assert c2["memory_type"] == "episodic"
        assert c2["importance_score"] >= 0.7
    finally:
        await client.delete(f"/api/v1/memories/{base_id}")


@pytest.mark.asyncio
async def test_memory_export_and_import(client: AsyncClient, session: AsyncSession):
    """Verify export and import of academic memories."""
    # Create memory to export
    res = await client.post(
        "/api/v1/memories",
        json={
            "content": "Procedural rule: Always check for edge cases with empty arrays.",
            "memory_type": "procedural",
            "importance_score": 0.85,
        },
    )
    created_id = res.json()["id"]

    try:
        # Export
        export_res = await client.get("/api/v1/memories/export")
        assert export_res.status_code == 200
        exported = export_res.json()
        assert any(item["content"] == "Procedural rule: Always check for edge cases with empty arrays." for item in exported)

        # Import new item
        import_payload = [
            {
                "content": "Semantic fact: QuickSort average time complexity is O(n log n).",
                "memory_type": "semantic",
                "importance_score": 0.75,
            }
        ]
        import_res = await client.post("/api/v1/memories/import", json=import_payload)
        assert import_res.status_code == 200
        assert import_res.json()["imported_count"] == 1

        # Verify imported item exists
        list_res = await client.get("/api/v1/memories?q=QuickSort")
        assert list_res.status_code == 200
        mems = list_res.json()
        assert len(mems) >= 1
        assert "QuickSort" in mems[0]["content"]

        # Cleanup imported item
        await client.delete(f"/api/v1/memories/{mems[0]['id']}")
    finally:
        await client.delete(f"/api/v1/memories/{created_id}")
