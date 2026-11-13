import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Conversation, Message, Document, DocumentChunk
from app.services.ai.base import (
    BaseAIProvider,
    ChatMessage,
    ChatResponse,
    ChatResponseChunk,
    ModelInfo,
    ProviderCapability,
)
from app.services.retrieval.hybrid import RetrievedChunk


class MockAIAdapter(BaseAIProvider):
    def __init__(self):
        super().__init__(
            name="Mock Provider",
            provider_type="mock",
            default_model="mock-academic-model",
            base_url="http://mock",
            api_key=None,
        )

    async def list_models(self):
        return [
            ModelInfo(
                id="mock-academic-model",
                name="Mock Model",
                provider_type="mock",
                capabilities=[ProviderCapability.CHAT, ProviderCapability.STREAM],
                is_local=True,
            )
        ]

    async def test_connection(self):
        return {"success": True, "latency_ms": 5.0, "message": "Mock connected"}

    async def chat(self, messages, model=None, temperature=None, max_tokens=None):
        return ChatResponse(
            content="Based on [Doc: OS Principles, Page: 42], Peterson's algorithm solves mutual exclusion.",
            model="mock-academic-model",
            tokens_used=18,
        )

    async def stream_chat(self, messages, model=None, temperature=None, max_tokens=None):
        tokens = [
            "Based ", "on ", "[Doc: OS Principles, Page: 42], ",
            "Peterson's ", "algorithm ", "solves ", "mutual exclusion."
        ]
        for t in tokens:
            yield ChatResponseChunk(content_delta=t)



@pytest.mark.asyncio
async def test_conversation_crud_endpoints(client: AsyncClient):
    """Verify conversation creation, listing, updating, and deletion."""
    # 1. Create conversation
    create_res = await client.post(
        "/api/v1/conversations",
        json={"title": "Operating Systems Study", "system_prompt": "Focus on CPU scheduling"},
    )
    assert create_res.status_code == 201
    conv = create_res.json()
    conv_id = conv["id"]
    assert conv["title"] == "Operating Systems Study"

    # 2. List conversations
    list_res = await client.get("/api/v1/conversations")
    assert list_res.status_code == 200
    conv_list = list_res.json()
    assert any(c["id"] == conv_id for c in conv_list)

    # 3. Update conversation
    patch_res = await client.patch(
        f"/api/v1/conversations/{conv_id}",
        json={"title": "OS Process Sync & Deadlocks"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "OS Process Sync & Deadlocks"

    # 4. Export conversation
    export_res = await client.get(f"/api/v1/conversations/{conv_id}/export")
    assert export_res.status_code == 200
    assert "OS Process Sync & Deadlocks" in export_res.text

    # 5. Delete conversation
    del_res = await client.delete(f"/api/v1/conversations/{conv_id}")
    assert del_res.status_code == 204

    # Verify 404 after deletion
    get_res = await client.get(f"/api/v1/conversations/{conv_id}")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_chat_resource_grounded_mode(client: AsyncClient, session: AsyncSession, monkeypatch):
    """Verify resource-grounded answer generation with citations."""
    mock_adapter = MockAIAdapter()

    # Mock provider manager to return our mock adapter
    from app.services.ai.manager import provider_manager
    monkeypatch.setattr(provider_manager, "get_active_adapter", AsyncMock(return_value=mock_adapter))

    # Mock hybrid retriever to return known chunk
    from app.services.retrieval.hybrid import hybrid_retriever, HybridRetrievalResult
    mock_chunk = RetrievedChunk(
        chunk_id="chunk-os-1",
        document_id="doc-os",
        document_title="OS Principles",
        content="Peterson's algorithm is a concurrent programming algorithm for mutual exclusion.",
        page_number=42,
        section_heading="Critical Section",
        dense_score=0.95,
        sparse_score=0.88,
        rrf_score=0.016,
        matched_by="both",
    )
    mock_search_res = HybridRetrievalResult(
        query="Peterson algorithm",
        total_found=1,
        dense_count=1,
        sparse_count=1,
        dense_latency_ms=2.0,
        sparse_latency_ms=1.5,
        total_latency_ms=3.5,
        chunks=[mock_chunk],
    )
    monkeypatch.setattr(hybrid_retriever, "search", AsyncMock(return_value=mock_search_res))

    # Create conversation
    conv_res = await client.post("/api/v1/conversations", json={"title": "Sync Test"})
    conv_id = conv_res.json()["id"]

    # Send message in resource-grounded mode
    msg_res = await client.post(
        "/api/v1/chat/message",
        json={
            "conversation_id": conv_id,
            "content": "Explain Peterson's algorithm and cite the page.",
            "mode": "resource-grounded",
        },
    )
    assert msg_res.status_code == 200
    data = msg_res.json()
    assert data["role"] == "assistant"
    assert "Peterson's algorithm" in data["content"]
    assert data["citations"] is not None
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["document_title"] == "OS Principles"
    assert data["citations"][0]["page_number"] == 42
    assert data["citations"][0]["is_verified"] is True
    assert data["diagnostics"]["grounding"]["is_grounded"] is True


@pytest.mark.asyncio
async def test_chat_general_mode_indication(client: AsyncClient, session: AsyncSession, monkeypatch):
    """Verify general knowledge mode appends clear ungrounded indication tag."""
    mock_adapter = MockAIAdapter()
    from app.services.ai.manager import provider_manager
    monkeypatch.setattr(provider_manager, "get_active_adapter", AsyncMock(return_value=mock_adapter))

    conv_res = await client.post("/api/v1/conversations", json={"title": "General Test"})
    conv_id = conv_res.json()["id"]

    msg_res = await client.post(
        "/api/v1/chat/message",
        json={
            "conversation_id": conv_id,
            "content": "What is the capital of France?",
            "mode": "general",
        },
    )
    assert msg_res.status_code == 200
    data = msg_res.json()
    assert "General Knowledge" in data["content"]
    assert data["mode"] == "general"


@pytest.mark.asyncio
async def test_chat_streaming_sse(client: AsyncClient, session: AsyncSession, monkeypatch):
    """Verify SSE streaming endpoint emits token and done events."""
    mock_adapter = MockAIAdapter()
    from app.services.ai.manager import provider_manager
    monkeypatch.setattr(provider_manager, "get_active_adapter", AsyncMock(return_value=mock_adapter))

    conv_res = await client.post("/api/v1/conversations", json={"title": "Stream Test"})
    conv_id = conv_res.json()["id"]

    stream_res = await client.post(
        "/api/v1/chat/stream",
        json={
            "conversation_id": conv_id,
            "content": "Tell me about mutual exclusion.",
            "mode": "general",
        },
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers.get("content-type", "")
    body_text = stream_res.text
    assert "event: token" in body_text
    assert "event: done" in body_text
