import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    app_name: str = "Ruby - Personal Academic Intelligence System"
    version: str = "0.1.0"
    environment: str = Field(default="development", alias="RUBY_ENV")
    host: str = Field(default="127.0.0.1", alias="RUBY_HOST")
    port: int = Field(default=8000, alias="RUBY_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Allowed CORS Origins (strictly localhost by default)
    cors_origins: List[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]

    # Storage Paths
    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "data",
        alias="RUBY_DATA_DIR",
    )
    db_file: Optional[Path] = Field(default=None, alias="RUBY_DB_FILE")
    chroma_dir: Optional[Path] = Field(default=None, alias="RUBY_CHROMA_DIR")
    documents_dir: Optional[Path] = Field(default=None, alias="RUBY_DOCUMENTS_DIR")
    cache_dir: Optional[Path] = Field(default=None, alias="RUBY_CACHE_DIR")

    # Security & Encryption
    encryption_key: Optional[str] = Field(default=None, alias="RUBY_ENCRYPTION_KEY")

    # Web Search (SearXNG)
    searxng_url: Optional[str] = Field(default=None, alias="SEARXNG_URL")
    searxng_timeout: int = Field(default=10, alias="SEARXNG_TIMEOUT")

    # External AI Providers
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")

    # Default Models
    default_chat_provider: str = Field(default="ollama", alias="DEFAULT_CHAT_PROVIDER")
    default_chat_model: str = Field(default="llama3.2:latest", alias="DEFAULT_CHAT_MODEL")
    default_embedding_provider: str = Field(default="sentence-transformers", alias="DEFAULT_EMBEDDING_PROVIDER")
    default_embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="DEFAULT_EMBEDDING_MODEL")

    def ensure_directories(self) -> None:
        """Create all required data and storage directories if they do not exist."""
        base = self.data_dir.resolve()
        base.mkdir(parents=True, exist_ok=True)

        if self.db_file is None:
            self.db_file = base / "ruby.db"
        else:
            self.db_file = self.db_file.resolve()
            self.db_file.parent.mkdir(parents=True, exist_ok=True)

        if self.chroma_dir is None:
            self.chroma_dir = base / "chroma"
        self.chroma_dir.resolve().mkdir(parents=True, exist_ok=True)

        if self.documents_dir is None:
            self.documents_dir = base / "documents"
        self.documents_dir.resolve().mkdir(parents=True, exist_ok=True)

        if self.cache_dir is None:
            self.cache_dir = base / "cache"
        self.cache_dir.resolve().mkdir(parents=True, exist_ok=True)

    @property
    def database_url(self) -> str:
        """Async SQLite connection string."""
        db_path = self.db_file.resolve() if self.db_file else self.data_dir.resolve() / "ruby.db"
        return f"sqlite+aiosqlite:///{db_path}"

    @property
    def sync_database_url(self) -> str:
        """Synchronous SQLite connection string for Alembic migrations."""
        db_path = self.db_file.resolve() if self.db_file else self.data_dir.resolve() / "ruby.db"
        return f"sqlite:///{db_path}"


settings = Settings()
settings.ensure_directories()
