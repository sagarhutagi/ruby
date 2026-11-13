import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import async_session_factory
from app.models.entities import Conversation, Message
from app.services.chat.engine import chat_engine
from app.services.search.searxng import WebSearchResponse, WebSearchResultItem
from app.services.ai.base import ChatResponseChunk


@pytest.mark.asyncio
async def test_chat_empty_model_response_fallback():
    """
    Regression test for Issue A:
    When an AI provider yields an empty stream (0 tokens or whitespace only),
    the chat engine must NOT save an empty assistant message or return empty text.
    It must supply a helpful fallback message explaining the state.
    """
    async with async_session_factory() as session:
        # Create temporary test conversation
        conv = Conversation(title="Empty Response Test")
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        # Mock adapter stream_chat to yield empty chunks
        async def mock_empty_stream(*args, **kwargs):
            yield ChatResponseChunk(content_delta="", is_done=True)

        mock_adapter = AsyncMock()
        mock_adapter.provider_type = "mock"
        mock_adapter.name = "mock"
        mock_adapter.default_model = "mock-empty-model"
        mock_adapter.stream_chat = mock_empty_stream

        with patch("app.services.ai.manager.provider_manager.get_active_adapter", return_value=mock_adapter):
            events = []
            async for evt in chat_engine.stream_chat(
                session=session,
                conversation_id=conv.id,
                user_content="Test prompt that yields empty response",
                mode="resource-grounded",
            ):
                events.append(evt)

            done_evt = next((e for e in events if e.get("type") == "done"), None)
            assert done_evt is not None
            # Content must NOT be empty
            assert len(done_evt["full_content"].strip()) > 0
            assert "empty response" in done_evt["full_content"].lower() or "retry" in done_evt["full_content"].lower()

            # Verify saved assistant message in SQLite is not empty
            msg_stmt = (
                select(Message)
                .where(Message.conversation_id == conv.id, Message.role == "assistant")
                .order_by(Message.created_at.desc())
            )
            saved_msg = (await session.execute(msg_stmt)).scalars().first()
            assert saved_msg is not None
            assert len(saved_msg.content.strip()) > 0

        # Clean up test conversation & messages
        await session.delete(conv)
        await session.commit()


@pytest.mark.asyncio
async def test_chat_web_search_streaming_integration():
    """
    Test SearXNG web search triggered in chat_engine.stream_chat.
    Verifies that web_search_start and web_sources events are emitted,
    and web context is assembled into the prompt.
    """
    async with async_session_factory() as session:
        conv = Conversation(title="Web Search Stream Test")
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        mock_web_res = WebSearchResponse(
            query="Latest Kubernetes releases",
            results=[
                WebSearchResultItem(
                    title="Kubernetes 1.32 Release Notes",
                    url="https://kubernetes.io/blog/2025/k8s-1-32/",
                    snippet="Kubernetes v1.32 delivers major improvements in cluster security.",
                    engine="google",
                    source_type="web",
                )
            ],
            total_results=1,
            is_available=True,
        )

        async def mock_llm_stream(messages, *args, **kwargs):
            # Verify the web context was passed to the LLM messages
            user_msg = next((m for m in messages if m.role == "user"), None)
            assert user_msg is not None
            assert "LIVE WEB SEARCH RESULTS" in user_msg.content or "Kubernetes" in user_msg.content
            yield ChatResponseChunk(content_delta="According to the live web search, Kubernetes v1.32 was released.", is_done=True)

        mock_adapter = AsyncMock()
        mock_adapter.provider_type = "mock"
        mock_adapter.name = "mock"
        mock_adapter.default_model = "mock-web-model"
        mock_adapter.stream_chat = mock_llm_stream

        with patch("app.services.search.searxng.searxng_client.search", return_value=mock_web_res), \
             patch("app.services.ai.manager.provider_manager.get_active_adapter", return_value=mock_adapter):

            events = []
            async for evt in chat_engine.stream_chat(
                session=session,
                conversation_id=conv.id,
                user_content="What are the latest Kubernetes releases?",
                mode="general",
                web_search=True,
            ):
                events.append(evt)

            event_types = [e.get("type") for e in events]
            assert "web_search_start" in event_types
            assert "web_sources" in event_types
            assert "token" in event_types
            assert "done" in event_types

            done_evt = next(e for e in events if e.get("type") == "done")
            assert len(done_evt["web_sources"]) == 1
            assert done_evt["web_sources"][0]["url"] == "https://kubernetes.io/blog/2025/k8s-1-32/"

        # Clean up test conversation & messages
        await session.delete(conv)
        await session.commit()
