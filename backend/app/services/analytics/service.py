import os
import sys
import platform
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.models.entities import (
    Document,
    DocumentChunk,
    Subject,
    Conversation,
    Message,
    Memory,
    Flashcard,
    ReviewLog,
    QuizSession,
    QuizQuestion,
    StudySession,
    KnowledgeNode,
    KnowledgeEdge,
    ProviderConfig,
)
from app.core.hardware import hardware_monitor
from app.core.config import settings

logger = logging.getLogger("ruby.services.analytics")

# Estimated cost table ($ per 1M tokens blend)
MODEL_PRICING_PER_1M: Dict[str, float] = {
    "gpt-4o": 5.00,
    "gpt-4o-mini": 0.35,
    "gpt-4-turbo": 15.00,
    "claude-3-5-sonnet": 6.00,
    "claude-3-haiku": 0.50,
    "gemini-1.5-pro": 2.50,
    "gemini-1.5-flash": 0.20,
    "openrouter": 2.00,
}


class AnalyticsService:
    """Computes measured analytics across documents, study sessions, tokens, and system health."""

    async def get_document_analytics(self, session: AsyncSession) -> Dict[str, Any]:
        """Calculates document counts, storage consumption, format distributions, and chunk counts."""
        # Total documents & storage
        total_docs = await session.scalar(select(func.count(Document.id))) or 0
        total_bytes = await session.scalar(select(func.sum(Document.file_size_bytes))) or 0
        total_chunks = await session.scalar(select(func.count(DocumentChunk.id))) or 0

        # By File Type
        file_types_stmt = (
            select(Document.file_type, func.count(Document.id))
            .group_by(Document.file_type)
        )
        type_rows = (await session.execute(file_types_stmt)).all()
        by_file_type = {r[0]: r[1] for r in type_rows}

        # By Ingestion Status
        status_stmt = select(Document.status, func.count(Document.id)).group_by(Document.status)
        status_rows = (await session.execute(status_stmt)).all()
        by_status = {r[0]: r[1] for r in status_rows}

        # By Subject
        subject_stmt = (
            select(Subject.name, func.count(Document.id))
            .outerjoin(Document, Document.subject_id == Subject.id)
            .group_by(Subject.name)
        )
        subj_rows = (await session.execute(subject_stmt)).all()
        by_subject = {r[0]: r[1] for r in subj_rows}

        return {
            "total_documents": total_docs,
            "total_storage_bytes": total_bytes,
            "total_storage_mb": round(total_bytes / (1024 * 1024), 2),
            "total_chunks": total_chunks,
            "by_file_type": by_file_type,
            "by_status": by_status,
            "by_subject": by_subject,
        }

    async def get_study_analytics(self, session: AsyncSession) -> Dict[str, Any]:
        """Calculates FSRS card retention, review ratings, quiz accuracy, and study sessions."""
        # Flashcards & Reviews
        total_cards = await session.scalar(select(func.count(Flashcard.id))) or 0
        avg_stability = await session.scalar(select(func.avg(Flashcard.stability))) or 0.0
        avg_difficulty = await session.scalar(select(func.avg(Flashcard.difficulty))) or 0.0
        total_reviews = await session.scalar(select(func.count(ReviewLog.id))) or 0

        # Review Rating Distribution
        rating_stmt = select(ReviewLog.rating, func.count(ReviewLog.id)).group_by(ReviewLog.rating)
        rating_rows = (await session.execute(rating_stmt)).all()
        rating_map = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}
        ratings_distribution = {rating_map.get(r[0], f"Rating {r[0]}"): r[1] for r in rating_rows}

        # Quizzes
        total_quizzes = await session.scalar(select(func.count(QuizSession.id))) or 0
        avg_quiz_score = (
            await session.scalar(
                select(func.avg(QuizSession.score_percentage)).where(QuizSession.status == "completed")
            )
            or 0.0
        )
        total_questions = await session.scalar(select(func.count(QuizQuestion.id))) or 0
        correct_questions = (
            await session.scalar(select(func.count(QuizQuestion.id)).where(QuizQuestion.is_correct == True))  # noqa: E712
            or 0
        )

        # Study Sessions
        total_study_minutes = await session.scalar(select(func.sum(StudySession.duration_minutes))) or 0
        study_sessions_count = await session.scalar(select(func.count(StudySession.id))) or 0

        # Knowledge Graph concepts
        total_concepts = await session.scalar(select(func.count(KnowledgeNode.id))) or 0
        verified_concepts = (
            await session.scalar(select(func.count(KnowledgeNode.id)).where(KnowledgeNode.is_verified == True))  # noqa: E712
            or 0
        )

        return {
            "flashcards": {
                "total_cards": total_cards,
                "total_reviews": total_reviews,
                "average_stability_days": round(avg_stability, 1),
                "average_difficulty": round(avg_difficulty, 1),
                "ratings_distribution": ratings_distribution,
            },
            "quizzes": {
                "total_quizzes_taken": total_quizzes,
                "average_score_percentage": round(avg_quiz_score, 1),
                "total_questions_answered": total_questions,
                "correct_answers": correct_questions,
                "accuracy_percentage": round((correct_questions / max(1, total_questions)) * 100, 1),
            },
            "study_time": {
                "total_sessions": study_sessions_count,
                "total_minutes": total_study_minutes,
                "total_hours": round(total_study_minutes / 60, 2),
            },
            "knowledge_graph": {
                "total_concepts": total_concepts,
                "verified_concepts": verified_concepts,
                "ai_suggested_concepts": total_concepts - verified_concepts,
            },
        }

    async def get_token_and_cost_analytics(self, session: AsyncSession) -> Dict[str, Any]:
        """Calculates AI tokens used, provider distribution, latency, and estimated cost."""
        total_messages = await session.scalar(select(func.count(Message.id))) or 0
        total_tokens = await session.scalar(select(func.sum(Message.tokens_used))) or 0

        # Tokens by provider
        prov_stmt = (
            select(Message.provider_used, func.sum(Message.tokens_used), func.count(Message.id))
            .where(Message.provider_used != None)
            .group_by(Message.provider_used)
        )
        prov_rows = (await session.execute(prov_stmt)).all()

        by_provider: Dict[str, Dict[str, Any]] = {}
        total_estimated_cost = 0.0

        for row in prov_rows:
            p_name = row[0] or "unknown"
            p_tokens = row[1] or 0
            p_count = row[2] or 0

            # Calculate cost
            if p_name.lower() == "ollama":
                p_cost = 0.0
            else:
                rate = MODEL_PRICING_PER_1M.get(p_name.lower(), 2.00)
                p_cost = (p_tokens / 1_000_000) * rate

            total_estimated_cost += p_cost

            by_provider[p_name] = {
                "tokens": p_tokens,
                "message_count": p_count,
                "estimated_cost_usd": round(p_cost, 4),
            }

        # Tokens by model
        model_stmt = (
            select(Message.model_used, func.sum(Message.tokens_used), func.count(Message.id))
            .where(Message.model_used != None)
            .group_by(Message.model_used)
        )
        model_rows = (await session.execute(model_stmt)).all()
        by_model = {r[0] or "unknown": {"tokens": r[1] or 0, "messages": r[2] or 0} for r in model_rows}

        # Tokens by mode
        mode_stmt = (
            select(Message.mode, func.count(Message.id), func.sum(Message.tokens_used))
            .group_by(Message.mode)
        )
        mode_rows = (await session.execute(mode_stmt)).all()
        by_mode = {r[0]: {"messages": r[1], "tokens": r[2] or 0} for r in mode_rows}

        return {
            "total_messages": total_messages,
            "total_tokens_consumed": total_tokens,
            "total_estimated_cost_usd": round(total_estimated_cost, 4),
            "by_provider": by_provider,
            "by_model": by_model,
            "by_mode": by_mode,
        }

    async def generate_sanitized_diagnostic_report(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Builds a comprehensive diagnostic health report with all API secrets and PII strictly redacted.
        """
        # Hardware & OS
        cpu = hardware_monitor.get_cpu_metrics()
        ram = hardware_monitor.get_ram_metrics()
        disk = hardware_monitor.get_disk_metrics()
        gpu = await hardware_monitor.get_gpu_metrics()
        ollama = await hardware_monitor.get_ollama_metrics()

        # Database Row Counts
        table_counts: Dict[str, int] = {}
        for entity, name in [
            (Document, "documents"),
            (DocumentChunk, "document_chunks"),
            (Subject, "subjects"),
            (Conversation, "conversations"),
            (Message, "messages"),
            (Memory, "memories"),
            (Flashcard, "flashcards"),
            (ReviewLog, "review_logs"),
            (QuizSession, "quiz_sessions"),
            (KnowledgeNode, "knowledge_nodes"),
            (KnowledgeEdge, "knowledge_edges"),
        ]:
            table_counts[name] = await session.scalar(select(func.count(entity.id))) or 0

        # Providers (Secrets REDACTED)
        prov_stmt = select(ProviderConfig)
        provs = (await session.execute(prov_stmt)).scalars().all()
        sanitized_providers = [
            {
                "id": p.id,
                "name": p.name,
                "provider_type": p.provider_type,
                "model_name": p.model_name,
                "is_enabled": p.is_enabled,
                "is_default": p.is_default,
                "api_key": "[REDACTED_SECRET]",
            }
            for p in provs
        ]

        # ChromaDB info
        chroma_exists = os.path.exists(settings.chroma_dir)
        chroma_size_mb = 0.0
        if chroma_exists:
            total_size = sum(
                os.path.getsize(os.path.join(dirpath, f))
                for dirpath, _, filenames in os.walk(settings.chroma_dir)
                for f in filenames
            )
            chroma_size_mb = round(total_size / (1024 * 1024), 2)

        return {
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "ruby_version": "0.1.0",
            "environment": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "processor": platform.processor(),
                "executable": sys.executable,
                "data_directory": str(settings.data_dir),
                "localhost_only": True,
            },
            "hardware": {
                "cpu_cores": cpu.core_count,
                "cpu_percent": cpu.percent,
                "ram_total_mb": ram.total_mb,
                "ram_used_mb": ram.used_mb,
                "gpu_available": gpu.available,
                "gpu_name": gpu.name,
                "vram_total_mb": gpu.vram_total_mb,
                "disk_free_gb": disk.free_gb,
                "ollama_running": ollama.running,
                "ollama_installed_models": ollama.installed_models,
            },
            "storage_diagnostics": {
                "database_tables": table_counts,
                "chromadb_directory": str(settings.chroma_dir),
                "chromadb_exists": chroma_exists,
                "chromadb_size_mb": chroma_size_mb,
            },
            "configured_providers": sanitized_providers,
            "security_compliance": {
                "cloud_leakage_prevention": "Strict localhost default with explicit manual opt-in",
                "secret_protection": "Keyring & AES-256-GCM fallback (No plaintext stored or exported)",
                "sandbox_isolation": "Restricted subprocess with AST validation (os/sys/network blocked)",
            },
        }


analytics_service = AnalyticsService()
