import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import (
    Document,
    DocumentChunk,
    Subject,
    Conversation,
    Message,
    FlashcardDeck,
    Flashcard,
    ReviewLog,
    QuizSession,
    QuizQuestion,
)
from app.services.analytics.service import analytics_service


@pytest.mark.asyncio
async def test_document_and_storage_analytics(session: AsyncSession):
    """Verify document storage, file type breakdown, and chunk counting."""
    doc = Document(
        title="Operating Systems Principles",
        filename="os_concepts.pdf",
        file_path="/data/documents/os_concepts.pdf",
        file_type="pdf",
        file_size_bytes=50000,
        file_hash="hash_doc_os_500",
        status="indexed",
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content="Kernel architecture and system call interfaces.",
        token_count=10,
    )
    session.add(chunk)
    await session.commit()

    analytics = await analytics_service.get_document_analytics(session)
    assert analytics["total_documents"] >= 1
    assert analytics["total_storage_bytes"] >= 50000
    assert analytics["total_chunks"] >= 1
    assert "pdf" in analytics["by_file_type"]


@pytest.mark.asyncio
async def test_study_and_retention_analytics(session: AsyncSession):
    """Verify FSRS flashcard retention metrics and quiz score accuracy."""
    deck = FlashcardDeck(name="Algorithm Analysis")
    session.add(deck)
    await session.commit()
    await session.refresh(deck)

    card = Flashcard(
        deck_id=deck.id,
        front="What is the worst-case time complexity of QuickSort?",
        back="O(n^2)",
        state=2,
        difficulty=6.2,
        stability=14.5,
    )
    session.add(card)
    await session.commit()
    await session.refresh(card)

    log = ReviewLog(
        card_id=card.id,
        rating=3,  # Good
        scheduled_days=14,
        elapsed_days=5,
    )
    session.add(log)

    # Add Quiz Session
    quiz = QuizSession(
        title="Complexity Quiz",
        total_questions=2,
        correct_count=2,
        score_percentage=100.0,
        status="completed",
    )
    session.add(quiz)
    await session.commit()

    study_stats = await analytics_service.get_study_analytics(session)
    assert study_stats["flashcards"]["total_cards"] >= 1
    assert study_stats["flashcards"]["total_reviews"] >= 1
    assert "Good" in study_stats["flashcards"]["ratings_distribution"]
    assert study_stats["quizzes"]["total_quizzes_taken"] >= 1
    assert study_stats["quizzes"]["average_score_percentage"] >= 0.0


@pytest.mark.asyncio
async def test_token_and_cost_analytics(session: AsyncSession):
    """Verify token usage, model separation, and cost calculations."""
    conv = Conversation(title="Algorithms Chat")
    session.add(conv)
    await session.commit()
    await session.refresh(conv)

    # Local Ollama message (cost = 0)
    m1 = Message(
        conversation_id=conv.id,
        role="assistant",
        content="Here is a binary search explanation.",
        provider_used="ollama",
        model_used="llama3.2:3b",
        tokens_used=1500,
        mode="resource-grounded",
    )
    # Cloud OpenAI message (cost > 0)
    m2 = Message(
        conversation_id=conv.id,
        role="assistant",
        content="Here is a recursive tree analysis.",
        provider_used="openai",
        model_used="gpt-4o",
        tokens_used=2000,
        mode="general",
    )
    session.add_all([m1, m2])
    await session.commit()

    tokens_stat = await analytics_service.get_token_and_cost_analytics(session)
    assert tokens_stat["total_tokens_consumed"] >= 3500
    assert "ollama" in tokens_stat["by_provider"]
    assert tokens_stat["by_provider"]["ollama"]["estimated_cost_usd"] == 0.0
    assert "openai" in tokens_stat["by_provider"]
    assert tokens_stat["by_provider"]["openai"]["estimated_cost_usd"] > 0.0


@pytest.mark.asyncio
async def test_sanitized_diagnostic_report(session: AsyncSession):
    """Verify diagnostic report contains hardware, storage, and zero unmasked secrets."""
    report = await analytics_service.generate_sanitized_diagnostic_report(session)

    assert "report_generated_at" in report
    assert "hardware" in report
    assert "storage_diagnostics" in report
    assert "configured_providers" in report
    assert report["environment"]["localhost_only"] is True

    # Verify no plaintext keys in report
    report_json = json.dumps(report)
    assert "sk-" not in report_json
    for p in report["configured_providers"]:
        assert p["api_key"] == "[REDACTED_SECRET]"


@pytest.mark.asyncio
async def test_analytics_api_endpoints(client: AsyncClient, session: AsyncSession):
    """Verify HTTP API endpoints for analytics overview and diagnostics export."""
    # Overview
    ov_res = await client.get("/api/v1/analytics/overview")
    assert ov_res.status_code == 200
    assert "documents" in ov_res.json()
    assert "study" in ov_res.json()
    assert "tokens" in ov_res.json()

    # Diagnostics report
    diag_res = await client.get("/api/v1/analytics/diagnostics")
    assert diag_res.status_code == 200
    assert "environment" in diag_res.json()

    # Diagnostics JSON Export
    export_res = await client.get("/api/v1/analytics/diagnostics/export")
    assert export_res.status_code == 200
    assert export_res.headers["content-type"] == "application/json"
    assert "ruby_sanitized_diagnostics.json" in export_res.headers["content-disposition"]
