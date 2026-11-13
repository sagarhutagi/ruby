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

logger = logging.getLogger("ruby.ai.openai")


class OpenAIAdapter(BaseAIProvider):
    """Adapter for OpenAI API."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.base_url:
            self.base_url = "https://api.openai.com/v1"

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        url = f"{self.base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.get(url, headers=self._headers())
                latency = round((time.perf_counter() - start) * 1000, 2)
                if res.status_code == 200:
                    models = res.json().get("data", [])
                    return {
                        "success": True,
                        "latency_ms": latency,
                        "message": f"Connected to OpenAI ({len(models)} models available)",
                        "model_count": len(models),
                    }
                return {
                    "success": False,
                    "latency_ms": latency,
                    "message": f"OpenAI HTTP {res.status_code}: {res.text}",
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
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            res = await client.get(url, headers=self._headers())
            if res.status_code != 200:
                raise RuntimeError(f"OpenAI list models failed: {res.text}")
            data = res.json().get("data", [])
            models: List[ModelInfo] = []
            for item in data:
                m_id = item.get("id", "")
                if "gpt" in m_id or "o1" in m_id or "o3" in m_id or "chat" in m_id:
                    models.append(
                        ModelInfo(
                            id=m_id,
                            name=m_id,
                            provider_type="openai",
                            capabilities=[ProviderCapability.CHAT, ProviderCapability.STREAM],
                            is_local=False,
                            description="OpenAI cloud model",
                        )
                    )
            return sorted(models, key=lambda m: m.id)

    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatResponse:
        url = f"{self.base_url}/chat/completions"
        target_model = model or self.default_model or "gpt-4o-mini"
        payload = {
            "model": target_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature if temperature is not None else self.temperature,
        }
        if max_tokens or self.max_tokens:
            payload["max_tokens"] = max_tokens or self.max_tokens

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            res = await client.post(url, headers=self._headers(), json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"OpenAI chat request failed ({res.status_code}): {res.text}")
            data = res.json()
            choice = data["choices"][0]
            tokens = data.get("usage", {}).get("total_tokens")
            return ChatResponse(
                content=choice["message"]["content"],
                model=target_model,
                tokens_used=tokens,
                finish_reason=choice.get("finish_reason"),
            )

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[ChatResponseChunk, None]:
        url = f"{self.base_url}/chat/completions"
        target_model = model or self.default_model or "gpt-4o-mini"
        payload = {
            "model": target_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature if temperature is not None else self.temperature,
            "stream": True,
        }
        if max_tokens or self.max_tokens:
            payload["max_tokens"] = max_tokens or self.max_tokens

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream("POST", url, headers=self._headers(), json=payload) as response:
                if response.status_code != 200:
                    err = await response.aread()
                    raise RuntimeError(f"OpenAI stream failed ({response.status_code}): {err.decode('utf-8', errors='ignore')}")

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        yield ChatResponseChunk(content_delta="", is_done=True, finish_reason="stop")
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {}).get("content", "")
                        finish = choices[0].get("finish_reason")
                        yield ChatResponseChunk(
                            content_delta=delta,
                            is_done=(finish is not None),
                            finish_reason=finish,
                        )
                    except json.JSONDecodeError:
                        continue
