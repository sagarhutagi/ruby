import uuid
from typing import Optional, List
from sqlalchemy import (
    String, Text, Integer, Float, Boolean, ForeignKey, Index, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base
from app.models.base import TimestampMixin


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ProviderConfig(Base, TimestampMixin):
    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ollama, openai, gemini, anthropic, openrouter, generic
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    context_window: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    custom_headers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    extra_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    secrets: Mapped[List["SecretRef"]] = relationship("SecretRef", back_populates="provider", cascade="all, delete-orphan")


class SecretRef(Base, TimestampMixin):
    __tablename__ = "secret_refs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    provider_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("provider_configs.id", ondelete="CASCADE"), nullable=True)
    key_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    backend_type: Mapped[str] = mapped_column(String(50), default="keyring", nullable=False)  # keyring, encrypted_file, env
    masked_preview: Mapped[str] = mapped_column(String(20), nullable=False)

    provider: Mapped[Optional[ProviderConfig]] = relationship("ProviderConfig", back_populates="secrets")


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(20), default="#6366f1", nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(50), default="book", nullable=True)

    collections: Mapped[List["Collection"]] = relationship("Collection", back_populates="subject", cascade="all, delete-orphan")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="subject")


class Collection(Base, TimestampMixin):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    subject_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    subject: Mapped[Optional[Subject]] = relationship("Subject", back_populates="collections")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="collection")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # SHA-256
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, docx, pptx, xlsx, txt, md, etc.
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # pending, parsing, indexed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    subject_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    collection_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("collections.id", ondelete="SET NULL"), nullable=True)

    subject: Mapped[Optional[Subject]] = relationship("Subject", back_populates="documents")
    collection: Mapped[Optional[Collection]] = relationship("Collection", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    slide_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sheet_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cell_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    section_heading: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meta_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    document: Mapped[Document] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("idx_doc_chunk", "document_id", "chunk_index"),
    )


class IngestionJob(Base, TimestampMixin):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)  # queued, running, completed, failed, cancelled
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stage: Mapped[str] = mapped_column(String(50), default="init", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), default="New Conversation", nullable=False)
    subject_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    messages: Mapped[List["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(30), default="resource-grounded", nullable=False)  # resource-grounded, general, hybrid, research
    provider_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    citations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    diagnostics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")


class Memory(Base, TimestampMixin):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    memory_type: Mapped[str] = mapped_column(String(30), nullable=False)  # working, episodic, semantic, profile, procedural
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, archived, deleted
    source_conversation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    source_event: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class MemoryAuditEvent(Base, TimestampMixin):
    __tablename__ = "memory_audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    memory_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # created, updated, consolidated, deleted
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class FlashcardDeck(Base, TimestampMixin):
    __tablename__ = "flashcard_decks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)

    cards: Mapped[List["Flashcard"]] = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan")


class Flashcard(Base, TimestampMixin):
    __tablename__ = "flashcards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    deck_id: Mapped[str] = mapped_column(String(36), ForeignKey("flashcard_decks.id", ondelete="CASCADE"), nullable=False)
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    hints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # FSRS scheduling state
    state: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0=New, 1=Learning, 2=Review, 3=Relearning
    difficulty: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    stability: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lapses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    elapsed_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scheduled_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    due_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    deck: Mapped[FlashcardDeck] = relationship("FlashcardDeck", back_populates="cards")
    reviews: Mapped[List["ReviewLog"]] = relationship("ReviewLog", back_populates="card", cascade="all, delete-orphan")


class ReviewLog(Base, TimestampMixin):
    __tablename__ = "review_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    card_id: Mapped[str] = mapped_column(String(36), ForeignKey("flashcards.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=Again, 2=Hard, 3=Good, 4=Easy
    scheduled_days: Mapped[int] = mapped_column(Integer, nullable=False)
    elapsed_days: Mapped[int] = mapped_column(Integer, nullable=False)
    review_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    card: Mapped[Flashcard] = relationship("Flashcard", back_populates="reviews")


class QuizSession(Base, TimestampMixin):
    __tablename__ = "quiz_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_limit_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)  # in_progress, completed, abandoned

    questions: Mapped[List["QuizQuestion"]] = relationship("QuizQuestion", back_populates="session", cascade="all, delete-orphan")


class QuizQuestion(Base, TimestampMixin):
    __tablename__ = "quiz_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), default="mcq", nullable=False)  # mcq, multi_select, true_false, numerical, conceptual
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped[QuizSession] = relationship("QuizSession", back_populates="questions")


class StudySession(Base, TimestampMixin):
    __tablename__ = "study_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    subject_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class KnowledgeNode(Base, TimestampMixin):
    __tablename__ = "knowledge_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    subject_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), default="concept", nullable=False)  # subject, topic, concept, document, formula
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    position_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class KnowledgeEdge(Base, TimestampMixin):
    __tablename__ = "knowledge_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), default="RELATED_TO", nullable=False)  # PREREQUISITE_OF, RELATED_TO, EXPLAINED_IN, PART_OF, CONTRADICTS
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
