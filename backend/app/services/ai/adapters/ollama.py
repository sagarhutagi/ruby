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

logger = logging.getLogger("ruby.ai.ollama")


class OllamaAdapter(BaseAIProvider):
    """Adapter for local Ollama inference."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.base_url:
            self.base_url = "http://127.0.0.1:11434"

    async def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.get(url)
                latency = round((time.perf_counter() - start) * 1000, 2)
                if res.status_code == 200:
                    models = res.json().get("models", [])
                    return {
                        "success": True,
                        "latency_ms": latency,
                        "message": f"Connected to Ollama ({len(models)} models installed)",
                        "model_count": len(models),
                    }
                return {
                    "success": False,
                    "latency_ms": latency,
                    "message": f"Ollama HTTP {res.status_code}: {res.text}",
                }
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "success": False,
                "latency_ms": latency,
                "message": f"Could not connect to Ollama at {self.base_url}: {str(e)}",
            }

    async def list_models(self) -> List[ModelInfo]:
        url = f"{self.base_url}/api/tags"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            res = await client.get(url)
            if res.status_code != 200:
                raise RuntimeError(f"Ollama list models failed: {res.text}")
            data = res.json().get("models", [])
            models: List[ModelInfo] = []
            for item in data:
                name = item.get("name", "")
                models.append(
                    ModelInfo(
                        id=name,
                        name=name,
                        provider_type="ollama",
                        capabilities=[
                            ProviderCapability.CHAT,
                            ProviderCapability.STREAM,
                            ProviderCapability.EMBEDDINGS,
                        ],
                        is_local=True,
                        description=f"Local model ({item.get('details', {}).get('parameter_size', 'unknown')})",
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
        url = f"{self.base_url}/api/chat"
        target_model = model or self.default_model or "llama3.2:latest"
        payload = {
            "model": target_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
            },
        }
        if max_tokens or self.max_tokens:
            payload["options"]["num_predict"] = max_tokens or self.max_tokens

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"Ollama chat generation failed: {res.text}")
            data = res.json()
            content = data.get("message", {}).get("content", "")
            tokens = data.get("eval_count")
            return ChatResponse(
                content=content,
                model=target_model,
                tokens_used=tokens,
                finish_reason="done" if data.get("done") else None,
            )

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[ChatResponseChunk, None]:
        url = f"{self.base_url}/api/chat"
        target_model = model or self.default_model or "llama3.2:latest"
        payload = {
            "model": target_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
            },
        }
        if max_tokens or self.max_tokens:
            payload["options"]["num_predict"] = max_tokens or self.max_tokens

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    err = await response.aread()
                    raise RuntimeError(f"Ollama streaming failed: {err.decode('utf-8', errors='ignore')}")

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content_piece = chunk.get("message", {}).get("content", "")
                        is_done = chunk.get("done", False)
                        tokens = chunk.get("eval_count")
                        yield ChatResponseChunk(
                            content_delta=content_piece,
                            is_done=is_done,
                            tokens_used=tokens,
                            finish_reason="stop" if is_done else None,
                        )
                    except json.JSONDecodeError:
                        continue

    async def pull_model(self, model_name: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Pull/download model from Ollama library."""
        url = f"{self.base_url}/api/pull"
        async with httpx.AsyncClient(timeout=600) as client:
            async with client.stream("POST", url, json={"name": model_name}) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        yield json.loads(line)

    async def delete_model(self, model_name: str) -> bool:
        """Delete local model from Ollama."""
        url = f"{self.base_url}/api/delete"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            res = await client.request("DELETE", url, json={"name": model_name})
            return res.status_code == 200
