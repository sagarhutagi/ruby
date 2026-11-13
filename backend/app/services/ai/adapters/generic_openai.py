from typing import Optional, Dict, Any
from app.services.ai.adapters.openai_provider import OpenAIAdapter


class GenericOpenAIAdapter(OpenAIAdapter):
    """Adapter for any OpenAI-compatible server (LM Studio, vLLM, LocalAI, etc.)."""

    def __init__(
        self,
        custom_headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.custom_headers = custom_headers or {}

    def _headers(self) -> Dict[str, str]:
        headers = super()._headers()
        headers.update(self.custom_headers)
        return headers
