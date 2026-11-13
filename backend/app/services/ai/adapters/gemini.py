import time
import json
import logging
from typing import List, Optional, AsyncGenerator, Dict, Any
import httpx
from app.services.ai.base import (
    BaseAIProvider,
    ChatMessage,
    ChatResponse,
    ChatResponseChunk,
    ModelInfo,
    ProviderCapability,
)

logger = logging.getLogger("ruby.ai.gemini")


class GeminiAdapter(BaseAIProvider):
    """Adapter for Google Gemini API."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.base_url:
            self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        gemini_contents = []
        for m in messages:
            role = "user" if m.role in ["user", "system"] else "model"
            gemini_contents.append({
                "role": role,
                "parts": [{"text": m.content}],
            })
        return gemini_contents

    async def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        url = f"{self.base_url}/models"
        params = {"key": self.api_key} if self.api_key else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.get(url, params=params)
                latency = round((time.perf_counter() - start) * 1000, 2)
                if res.status_code == 200:
                    models = res.json().get("models", [])
                    return {
                        "success": True,
                        "latency_ms": latency,
                        "message": f"Connected to Google Gemini ({len(models)} models found)",
                        "model_count": len(models),
                    }
                return {
                    "success": False,
                    "latency_ms": latency,
                    "message": f"Gemini HTTP {res.status_code}: {res.text}",
                }
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "success": False,
                "latency_ms": latency,
                "message": f"Connection error: {str(e)}",
            }

    async def list_models(self) -> List[ModelInfo]:
        url = f"{self.base_url}/models"
        params = {"key": self.api_key} if self.api_key else {}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            res = await client.get(url, params=params)
            if res.status_code != 200:
                raise RuntimeError(f"Gemini list models failed: {res.text}")
            data = res.json().get("models", [])
            models: List[ModelInfo] = []
            for item in data:
                m_name = item.get("name", "").replace("models/", "")
                if "gemini" in m_name:
                    models.append(
                        ModelInfo(
                            id=m_name,
                            name=item.get("displayName", m_name),
                            provider_type="gemini",
                            capabilities=[ProviderCapability.CHAT, ProviderCapability.STREAM, ProviderCapability.VISION],
                            is_local=False,
                            description=item.get("description", "Google Gemini model"),
                        )
                    )
            return models

    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatResponse:
        target_model = model or self.default_model or "gemini-1.5-flash"
        url = f"{self.base_url}/models/{target_model}:generateContent"
        params = {"key": self.api_key} if self.api_key else {}
        payload = {
            "contents": self._convert_messages(messages),
            "generationConfig": {
                "temperature": temperature if temperature is not None else self.temperature,
            },
        }
        if max_tokens or self.max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens or self.max_tokens

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            res = await client.post(url, params=params, json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"Gemini generation failed ({res.status_code}): {res.text}")
            data = res.json()
            candidate = data.get("candidates", [{}])[0]
            parts = candidate.get("content", {}).get("parts", [{}])
            content = "".join(p.get("text", "") for p in parts)
            tokens = data.get("usageMetadata", {}).get("totalTokenCount")
            return ChatResponse(
                content=content,
                model=target_model,
                tokens_used=tokens,
                finish_reason=candidate.get("finishReason"),
            )

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[ChatResponseChunk, None]:
        target_model = model or self.default_model or "gemini-1.5-flash"
        url = f"{self.base_url}/models/{target_model}:streamGenerateContent"
        params = {"key": self.api_key, "alt": "sse"} if self.api_key else {"alt": "sse"}
        payload = {
            "contents": self._convert_messages(messages),
            "generationConfig": {
                "temperature": temperature if temperature is not None else self.temperature,
            },
        }
        if max_tokens or self.max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens or self.max_tokens

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream("POST", url, params=params, json=payload) as response:
                if response.status_code != 200:
                    err = await response.aread()
                    raise RuntimeError(f"Gemini stream failed ({response.status_code}): {err.decode('utf-8', errors='ignore')}")

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    try:
                        chunk = json.loads(data_str)
                        candidates = chunk.get("candidates", [])
                        if not candidates:
                            continue
                        candidate = candidates[0]
                        parts = candidate.get("content", {}).get("parts", [])
                        text_piece = "".join(p.get("text", "") for p in parts)
                        finish = candidate.get("finishReason")
                        yield ChatResponseChunk(
                            content_delta=text_piece,
                            is_done=(finish is not None),
                            finish_reason=finish,
                        )
                    except json.JSONDecodeError:
                        continue
