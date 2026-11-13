import pytest
import json
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport, Response
from app.main import app
from app.database.session import async_session_factory
from app.services.ai.adapters.ollama import OllamaAdapter
from app.services.ai.adapters.openai_provider import OpenAIAdapter
from app.services.ai.adapters.gemini import GeminiAdapter
from app.services.ai.adapters.claude import ClaudeAdapter
from app.services.ai.base import ChatMessage


@pytest.mark.asyncio
async def test_provider_crud_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a provider with secret API key
        raw_key = "sk-test-secret-1234567890abcdef"
        create_payload = {
            "name": "Test OpenAI Provider",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o-mini",
            "api_key": raw_key,
            "is_enabled": True,
            "is_default": False,
            "temperature": 0.5,
        }
        res = await client.post("/api/v1/providers", json=create_payload)
        assert res.status_code == 201
        created = res.json()
        prov_id = created["id"]
        assert created["name"] == "Test OpenAI Provider"
        assert created["has_api_key"] is True
        # CRITICAL SECURITY CHECK: Secret is never exposed in response
        assert raw_key not in res.text
        assert "abcdef" not in res.text
        assert created["masked_key"].startswith("sk-")

        # 2. List providers - verify secret is not present in listing
        list_res = await client.get("/api/v1/providers")
        assert list_res.status_code == 200
        providers = list_res.json()
        assert any(p["id"] == prov_id for p in providers)
        assert raw_key not in list_res.text

        # 3. Update provider
        update_res = await client.put(f"/api/v1/providers/{prov_id}", json={"temperature": 0.2})
        assert update_res.status_code == 200
        assert update_res.json()["temperature"] == 0.2

        # 4. Delete provider
        del_res = await client.delete(f"/api/v1/providers/{prov_id}")
        assert del_res.status_code == 204

        # 5. Confirm deletion
        get_res = await client.get(f"/api/v1/providers/{prov_id}")
        assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_ollama_adapter_mocked():
    adapter = OllamaAdapter(
        name="Mock Ollama",
        provider_type="ollama",
        base_url="http://127.0.0.1:11434",
        default_model="llama3.2:latest",
    )

    mock_tags_response = Response(
        status_code=200,
        content=json.dumps({"models": [{"name": "llama3.2:latest", "details": {"parameter_size": "3B"}}]}),
        request=AsyncMock(),
    )

    with patch("httpx.AsyncClient.get", return_value=mock_tags_response):
        test_res = await adapter.test_connection()
        assert test_res["success"] is True
        assert test_res["model_count"] == 1

        models = await adapter.list_models()
        assert len(models) == 1
        assert models[0].id == "llama3.2:latest"
        assert models[0].is_local is True


@pytest.mark.asyncio
async def test_openai_adapter_mocked():
    adapter = OpenAIAdapter(
        name="Mock OpenAI",
        provider_type="openai",
        api_key="sk-mock-key",
        default_model="gpt-4o-mini",
    )

    mock_chat_response = Response(
        status_code=200,
        content=json.dumps({
            "choices": [{"message": {"content": "Hello from mock OpenAI!"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 15},
        }),
        request=AsyncMock(),
    )

    with patch("httpx.AsyncClient.post", return_value=mock_chat_response):
        chat_res = await adapter.chat([ChatMessage(role="user", content="Hi")])
        assert chat_res.content == "Hello from mock OpenAI!"
        assert chat_res.tokens_used == 15
        assert chat_res.finish_reason == "stop"


@pytest.mark.asyncio
async def test_gemini_adapter_mocked():
    adapter = GeminiAdapter(
        name="Mock Gemini",
        provider_type="gemini",
        api_key="mock-gemini-key",
        default_model="gemini-1.5-flash",
    )

    mock_gemini_response = Response(
        status_code=200,
        content=json.dumps({
            "candidates": [{"content": {"parts": [{"text": "Hello from mock Gemini!"}]}, "finishReason": "STOP"}],
            "usageMetadata": {"totalTokenCount": 20},
        }),
        request=AsyncMock(),
    )

    with patch("httpx.AsyncClient.post", return_value=mock_gemini_response):
        chat_res = await adapter.chat([ChatMessage(role="user", content="Hi")])
        assert chat_res.content == "Hello from mock Gemini!"
        assert chat_res.tokens_used == 20


@pytest.mark.asyncio
async def test_claude_adapter_mocked():
    adapter = ClaudeAdapter(
        name="Mock Claude",
        provider_type="anthropic",
        api_key="sk-ant-mock",
        default_model="claude-3-5-sonnet-20241022",
    )

    mock_claude_response = Response(
        status_code=200,
        content=json.dumps({
            "content": [{"type": "text", "text": "Hello from mock Claude!"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }),
        request=AsyncMock(),
    )

    with patch("httpx.AsyncClient.post", return_value=mock_claude_response):
        chat_res = await adapter.chat([ChatMessage(role="user", content="Hi")])
        assert chat_res.content == "Hello from mock Claude!"
        assert chat_res.tokens_used == 15
