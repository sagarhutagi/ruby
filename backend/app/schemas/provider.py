from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    name: str = Field(..., max_length=100, description="Display name for the provider")
    provider_type: str = Field(..., description="Provider type: ollama, openai, gemini, anthropic, openrouter, generic")
    base_url: Optional[str] = Field(default=None, description="Custom base URL if applicable")
    model_name: str = Field(..., description="Default model identifier")
    api_key: Optional[str] = Field(default=None, description="Sensitive API key (stored in keyring, never saved in plaintext)")
    is_enabled: bool = Field(default=True)
    is_default: bool = Field(default=False)
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    context_window: Optional[int] = Field(default=None, ge=512)
    custom_headers: Optional[Dict[str, str]] = None
    extra_params: Optional[Dict[str, Any]] = None


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None  # If provided, updates secret; if empty string, removes secret
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    timeout_seconds: Optional[int] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    custom_headers: Optional[Dict[str, str]] = None
    extra_params: Optional[Dict[str, Any]] = None


class ProviderResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    base_url: Optional[str] = None
    model_name: str
    is_enabled: bool
    is_default: bool
    timeout_seconds: int
    temperature: float
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    has_api_key: bool = False
    masked_key: Optional[str] = None  # Strictly masked preview (e.g. sk-••••4a2b), never plaintext
    created_at: datetime
    updated_at: datetime


class TestConnectionResponse(BaseModel):
    success: bool
    latency_ms: float
    message: str
    model_count: Optional[int] = None


class ChatStreamRequest(BaseModel):
    provider_id: Optional[str] = None
    model: Optional[str] = None
    prompt: str = Field(..., description="Prompt or query")
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
