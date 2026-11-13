import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_subject_and_collection_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Verify seeded subjects
        list_res = await client.get("/api/v1/subjects")
        assert list_res.status_code == 200
        subjects = list_res.json()
        assert len(subjects) >= 5
        names = [s["name"] for s in subjects]
        assert "Computer Networks" in names

        # 2. Create custom subject
        create_res = await client.post(
            "/api/v1/subjects",
            json={
                "name": "Artificial Intelligence",
                "description": "Machine Learning, Search Algorithms, Heuristics",
                "color": "#10b981",
                "icon": "brain",
            },
        )
        assert create_res.status_code == 201
        subj_data = create_res.json()
        subj_id = subj_data["id"]
        assert subj_data["name"] == "Artificial Intelligence"

        # 3. Create nested collection
        col_res = await client.post(
            "/api/v1/collections",
            json={
                "subject_id": subj_id,
                "name": "Search Algorithms",
                "description": "BFS, DFS, A*, Minimax",
            },
        )
        assert col_res.status_code == 201
        col_data = col_res.json()
        col_id = col_data["id"]
        assert col_data["subject_id"] == subj_id

        # 4. List collections filtered by subject
        col_list = await client.get(f"/api/v1/collections?subject_id={subj_id}")
        assert col_list.status_code == 200
        assert len(col_list.json()) == 1

        # 5. Clean up collection and subject
        del_col = await client.delete(f"/api/v1/collections/{col_id}")
        assert del_col.status_code == 204

        del_subj = await client.delete(f"/api/v1/subjects/{subj_id}")
        assert del_subj.status_code == 204
