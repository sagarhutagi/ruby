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

logger = logging.getLogger("ruby.ai.claude")


class ClaudeAdapter(BaseAIProvider):
    """Adapter for Anthropic Claude API."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.base_url:
            self.base_url = "https://api.anthropic.com/v1"

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        url = f"{self.base_url}/messages"
        payload = {
            "model": self.default_model or "claude-3-5-haiku-latest",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.post(url, headers=self._headers(), json=payload)
                latency = round((time.perf_counter() - start) * 1000, 2)
                # Anthropic returns 200 on success
                if res.status_code == 200:
                    return {
                        "success": True,
                        "latency_ms": latency,
                        "message": "Connected to Anthropic Claude API",
                        "model_count": 4,
                    }
                return {
                    "success": False,
                    "latency_ms": latency,
                    "message": f"Claude HTTP {res.status_code}: {res.text}",
                }
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "success": False,
                "latency_ms": latency,
                "message": f"Connection error: {str(e)}",
            }

    async def list_models(self) -> List[ModelInfo]:
        claude_models = [
            ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", "Most intelligent reasoning model"),
            ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku", "Fast and lightweight model"),
            ("claude-3-opus-20240229", "Claude 3 Opus", "Deep analytical intelligence"),
        ]
        return [
            ModelInfo(
                id=m_id,
                name=m_name,
                provider_type="anthropic",
                capabilities=[ProviderCapability.CHAT, ProviderCapability.STREAM, ProviderCapability.VISION],
                is_local=False,
                description=m_desc,
            )
            for m_id, m_name, m_desc in claude_models
        ]

    def _split_system_message(self, messages: List[ChatMessage]) -> tuple[Optional[str], List[Dict[str, str]]]:
        system_text = None
        user_msgs = []
        for m in messages:
            if m.role == "system":
                system_text = m.content
            else:
                user_msgs.append({"role": m.role, "content": m.content})
        return system_text, user_msgs

    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatResponse:
        url = f"{self.base_url}/messages"
        target_model = model or self.default_model or "claude-3-5-sonnet-20241022"
        system_prompt, formatted_msgs = self._split_system_message(messages)

        payload = {
            "model": target_model,
            "max_tokens": max_tokens or self.max_tokens or 4096,
            "messages": formatted_msgs,
            "temperature": temperature if temperature is not None else self.temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            res = await client.post(url, headers=self._headers(), json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"Claude request failed ({res.status_code}): {res.text}")
            data = res.json()
            content_blocks = data.get("content", [])
            content = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            usage = data.get("usage", {})
            tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            return ChatResponse(
                content=content,
                model=target_model,
                tokens_used=tokens,
                finish_reason=data.get("stop_reason"),
            )

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[ChatResponseChunk, None]:
        url = f"{self.base_url}/messages"
        target_model = model or self.default_model or "claude-3-5-sonnet-20241022"
        system_prompt, formatted_msgs = self._split_system_message(messages)

        payload = {
            "model": target_model,
            "max_tokens": max_tokens or self.max_tokens or 4096,
            "messages": formatted_msgs,
            "temperature": temperature if temperature is not None else self.temperature,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream("POST", url, headers=self._headers(), json=payload) as response:
                if response.status_code != 200:
                    err = await response.aread()
                    raise RuntimeError(f"Claude stream failed ({response.status_code}): {err.decode('utf-8', errors='ignore')}")

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type")
                        if event_type == "content_block_delta":
                            delta_text = event.get("delta", {}).get("text", "")
                            yield ChatResponseChunk(content_delta=delta_text, is_done=False)
                        elif event_type == "message_stop":
                            yield ChatResponseChunk(content_delta="", is_done=True, finish_reason="stop")
                    except json.JSONDecodeError:
                        continue
