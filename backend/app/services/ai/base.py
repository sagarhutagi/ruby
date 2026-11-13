from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, AsyncGenerator, Dict, Any
from pydantic import BaseModel, Field


class ProviderCapability(str, Enum):
    CHAT = "chat"
    STREAM = "stream"
    EMBEDDINGS = "embeddings"
    RERANK = "rerank"
    VISION = "vision"


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text")
    images: Optional[List[str]] = Field(default=None, description="Base64 or paths of images")


class ChatResponseChunk(BaseModel):
    content_delta: str = ""
    is_done: bool = False
    finish_reason: Optional[str] = None
    tokens_used: Optional[int] = None


class ChatResponse(BaseModel):
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None


class ModelInfo(BaseModel):
    id: str
    name: str
    provider_type: str
    capabilities: List[ProviderCapability]
    context_window: Optional[int] = None
    is_local: bool = True
    description: Optional[str] = None


class BaseAIProvider(ABC):
    """Abstract interface for all AI model providers in Ruby."""

    def __init__(
        self,
        name: str,
        provider_type: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_model: str = "",
        timeout_seconds: int = 60,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.provider_type = provider_type
        self.base_url = base_url.rstrip("/") if base_url else None
        self.api_key = api_key
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_params = extra_params or {}

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test API reachability and authentication. Returns { 'success': bool, 'latency_ms': float, 'message': str }."""
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """Discover available models from the provider."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatResponse:
        """Execute a non-streaming chat request."""
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[ChatResponseChunk, None]:
        """Stream response chunks in real-time."""
        pass
