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


def test_think_tag_parser_unit():
    """Verify ThinkTagParser correctly isolates <think> blocks across stream chunks."""
    from app.services.chat.engine import ThinkTagParser

    parser = ThinkTagParser()
    chunks = [
        "Intro ",
        "<th",
        "ink>\nStep 1: Check definitions.\nStep 2: Compare.\n</th",
        "ink>\nFinal Answer: TCP is connection-oriented.",
    ]
    streamed = []
    for c in chunks:
        streamed.extend(parser.feed(c))
    streamed.extend(parser.flush())

    thought_chunks = [text for t, text in streamed if t == "think"]
    content_chunks = [text for t, text in streamed if t == "content"]

    assert "".join(thought_chunks).strip() == "Step 1: Check definitions.\nStep 2: Compare."
    assert "".join(content_chunks).strip() == "Intro \nFinal Answer: TCP is connection-oriented."
    assert parser.thought_text.strip() == "Step 1: Check definitions.\nStep 2: Compare."
    assert parser.response_text.strip() == "Intro \nFinal Answer: TCP is connection-oriented."


@pytest.mark.asyncio
async def test_chat_web_search_mode_and_step_tracing():
    """
    Test dedicated web-search mode (mode='web-search'):
    - Bypasses local document RAG retrieval.
    - Forces SearXNG web search.
    - Emits step events (intent, web_search, context, generation, validation).
    - Emits think_token when LLM outputs <think> tags.
    - Diagnostics and done event contain steps and thinking_content.
    """
    from app.services.chat.engine import chat_engine

    async with async_session_factory() as session:
        conv = Conversation(title="Web Search Mode Test")
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        mock_web_res = WebSearchResponse(
            query="Python 3.14 features",
            results=[
                WebSearchResultItem(
                    title="What's New in Python 3.14",
                    url="https://docs.python.org/3.14/whatsnew/",
                    snippet="Python 3.14 introduces free-threaded CPython optimizations.",
                    engine="duckduckgo",
                    source_type="web",
                )
            ],
            total_results=1,
            is_available=True,
        )

        async def mock_thinking_stream(*args, **kwargs):
            yield ChatResponseChunk(content_delta="<think>\nAnalyzing latest PEPs for 3.14...\n</think>\n", is_done=False)
            yield ChatResponseChunk(content_delta="Python 3.14 features major interpreter improvements.", is_done=True)

        mock_adapter = AsyncMock()
        mock_adapter.provider_type = "mock"
        mock_adapter.name = "mock"
        mock_adapter.default_model = "mock-reasoning-model"
        mock_adapter.stream_chat = mock_thinking_stream

        with patch("app.services.search.searxng.searxng_client.search", return_value=mock_web_res), \
             patch("app.services.ai.manager.provider_manager.get_active_adapter", return_value=mock_adapter):

            events = []
            async for evt in chat_engine.stream_chat(
                session=session,
                conversation_id=conv.id,
                user_content="What are the key Python 3.14 features?",
                mode="web-search",
                web_search=False,  # Should still search web because mode is web-search!
            ):
                events.append(evt)

            event_types = [e.get("type") for e in events]
            assert "step" in event_types
            assert "web_search_start" in event_types
            assert "web_sources" in event_types
            assert "think_token" in event_types
            assert "token" in event_types
            assert "done" in event_types
            # Local document sources should NOT be retrieved
            assert "sources" not in event_types

            # Verify steps emitted
            step_events = [e["step"] for e in events if e.get("type") == "step"]
            step_ids = {s["id"] for s in step_events}
            assert "intent" in step_ids
            assert "web_search" in step_ids
            assert "context" in step_ids
            assert "generation" in step_ids

            # Verify done event contents
            done_evt = next(e for e in events if e.get("type") == "done")
            assert "steps" in done_evt
            assert len(done_evt["steps"]) >= 4
            assert "Analyzing latest PEPs" in done_evt["thinking_content"]
            assert "Python 3.14 features" in done_evt["full_content"]

            # Verify SQLite persistence of diagnostics
            msg_stmt = (
                select(Message)
                .where(Message.conversation_id == conv.id, Message.role == "assistant")
                .order_by(Message.created_at.desc())
            )
            saved_msg = (await session.execute(msg_stmt)).scalars().first()
            assert saved_msg is not None
            assert saved_msg.mode == "web-search"
            assert "steps" in saved_msg.diagnostics
            assert saved_msg.diagnostics["thinking_content"] != ""

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


def test_think_tag_parser_unit():
    """Verify ThinkTagParser correctly isolates <think> blocks across stream chunks."""
    from app.services.chat.engine import ThinkTagParser

    parser = ThinkTagParser()
    chunks = [
        "Intro ",
        "<th",
        "ink>\nStep 1: Check definitions.\nStep 2: Compare.\n</th",
        "ink>\nFinal Answer: TCP is connection-oriented.",
    ]
    streamed = []
    for c in chunks:
        streamed.extend(parser.feed(c))
    streamed.extend(parser.flush())

    thought_chunks = [text for t, text in streamed if t == "think"]
    content_chunks = [text for t, text in streamed if t == "content"]

    assert "".join(thought_chunks).strip() == "Step 1: Check definitions.\nStep 2: Compare."
    assert "".join(content_chunks).strip() == "Intro \nFinal Answer: TCP is connection-oriented."
    assert parser.thought_text.strip() == "Step 1: Check definitions.\nStep 2: Compare."
    assert parser.response_text.strip() == "Intro \nFinal Answer: TCP is connection-oriented."


@pytest.mark.asyncio
async def test_chat_web_search_mode_and_step_tracing():
    """
    Test dedicated web-search mode (mode='web-search'):
    - Bypasses local document RAG retrieval.
    - Forces SearXNG web search.
    - Emits step events (intent, web_search, context, generation, validation).
    - Emits think_token when LLM outputs <think> tags.
    - Diagnostics and done event contain steps and thinking_content.
    """
    from app.services.chat.engine import chat_engine

    async with async_session_factory() as session:
        conv = Conversation(title="Web Search Mode Test")
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        mock_web_res = WebSearchResponse(
            query="Python 3.14 features",
            results=[
                WebSearchResultItem(
                    title="What's New in Python 3.14",
                    url="https://docs.python.org/3.14/whatsnew/",
                    snippet="Python 3.14 introduces free-threaded CPython optimizations.",
                    engine="duckduckgo",
                    source_type="web",
                )
            ],
            total_results=1,
            is_available=True,
        )

        async def mock_thinking_stream(*args, **kwargs):
            yield ChatResponseChunk(content_delta="<think>\nAnalyzing latest PEPs for 3.14...\n</think>\n", is_done=False)
            yield ChatResponseChunk(content_delta="Python 3.14 features major interpreter improvements.", is_done=True)

        mock_adapter = AsyncMock()
        mock_adapter.provider_type = "mock"
        mock_adapter.name = "mock"
        mock_adapter.default_model = "mock-reasoning-model"
        mock_adapter.stream_chat = mock_thinking_stream

        with patch("app.services.search.searxng.searxng_client.search", return_value=mock_web_res), \
             patch("app.services.ai.manager.provider_manager.get_active_adapter", return_value=mock_adapter):

            events = []
            async for evt in chat_engine.stream_chat(
                session=session,
                conversation_id=conv.id,
                user_content="What are the key Python 3.14 features?",
                mode="web-search",
                web_search=False,  # Should still search web because mode is web-search!
            ):
                events.append(evt)

            event_types = [e.get("type") for e in events]
            assert "step" in event_types
            assert "web_search_start" in event_types
            assert "web_sources" in event_types
            assert "think_token" in event_types
            assert "token" in event_types
            assert "done" in event_types
            # Local document sources should NOT be retrieved
            assert "sources" not in event_types

            # Verify steps emitted
            step_events = [e["step"] for e in events if e.get("type") == "step"]
            step_ids = {s["id"] for s in step_events}
            assert "intent" in step_ids
            assert "web_search" in step_ids
            assert "context" in step_ids
            assert "generation" in step_ids

            # Verify done event contents
            done_evt = next(e for e in events if e.get("type") == "done")
            assert "steps" in done_evt
            assert len(done_evt["steps"]) >= 4
            assert "Analyzing latest PEPs" in done_evt["thinking_content"]
            assert "Python 3.14 features" in done_evt["full_content"]

            # Verify SQLite persistence of diagnostics
            msg_stmt = (
                select(Message)
                .where(Message.conversation_id == conv.id, Message.role == "assistant")
                .order_by(Message.created_at.desc())
            )
            saved_msg = (await session.execute(msg_stmt)).scalars().first()
            assert saved_msg is not None
            assert saved_msg.mode == "web-search"
            assert "steps" in saved_msg.diagnostics
            assert saved_msg.diagnostics["thinking_content"] != ""

        # Clean up test conversation & messages
        await session.delete(conv)
        await session.commit()


@pytest.mark.asyncio
async def test_chat_long_term_memory_formation_and_recall():
    """
    Regression test for Long-Term Memory:
    1. Teaching Ruby a profile memory via chat ('Please remember that my name is Mars...')
       must trigger candidate extraction, save to SQLite/Chroma, and emit memory_saved event.
    2. Subsequent turns must automatically recall active/pinned memories into the prompt context.
    """
    from app.services.memory.service import memory_service
    from app.models.entities import Memory

    async with async_session_factory() as session:
        conv = Conversation(title="Memory Regression Test")
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        created_mem_id = None
        try:
            # Turn 1: Explicit Remember instruction
            async def mock_turn1_stream(*args, **kwargs):
                yield ChatResponseChunk(content_delta="Understood! I have saved this to memory.", is_done=True)

            mock_adapter = AsyncMock()
            mock_adapter.provider_type = "mock"
            mock_adapter.name = "mock"
            mock_adapter.default_model = "mock-model"
            mock_adapter.stream_chat = mock_turn1_stream

            with patch("app.services.ai.manager.provider_manager.get_active_adapter", return_value=mock_adapter):
                events = []
                async for evt in chat_engine.stream_chat(
                    session=session,
                    conversation_id=conv.id,
                    user_content="Please remember that my name is Mars and my favorite programming language is Rust.",
                    mode="general",
                ):
                    events.append(evt)

                # Verify memory_saved event
                save_evt = next((e for e in events if e.get("type") == "memory_saved"), None)
                assert save_evt is not None
                created_mem_id = save_evt["memory"]["id"]
                assert "Mars" in save_evt["memory"]["content"]

                # Verify memory step
                step_evts = [e["step"] for e in events if e.get("type") == "step"]
                mem_step = [s for s in step_evts if s["id"] == "memory"][-1]
                assert mem_step is not None
                assert mem_step["status"] == "completed"

            # Verify memory was persisted to DB
            mem_db = await session.scalar(select(Memory).where(Memory.id == created_mem_id))
            assert mem_db is not None
            assert mem_db.memory_type == "profile"

            # Turn 2: Verify recall in subsequent prompt
            captured_messages = []

            async def mock_turn2_stream(messages, *args, **kwargs):
                captured_messages.extend(messages)
                yield ChatResponseChunk(content_delta="Your name is Mars and you love Rust.", is_done=True)

            mock_adapter.stream_chat = mock_turn2_stream

            with patch("app.services.ai.manager.provider_manager.get_active_adapter", return_value=mock_adapter):
                turn2_events = []
                async for evt in chat_engine.stream_chat(
                    session=session,
                    conversation_id=conv.id,
                    user_content="What is my name?",
                    mode="general",
                ):
                    turn2_events.append(evt)

                # Verify memories event emitted
                memories_evt = next((e for e in turn2_events if e.get("type") == "memories"), None)
                assert memories_evt is not None
                assert any("Mars" in m["content"] for m in memories_evt["memories"])

                # Verify prompt received by LLM contains the recalled memory block
                user_prompt = captured_messages[-1].content
                assert "=== RECALLED MEMORIES (Long-term User Memory) ===" in user_prompt
                assert "Mars" in user_prompt

        finally:
            # Clean up test memory and conversation
            if created_mem_id:
                await memory_service.delete_memory(session=session, memory_id=created_mem_id)
            await session.delete(conv)
            await session.commit()
