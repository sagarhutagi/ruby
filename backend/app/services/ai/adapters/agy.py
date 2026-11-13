import asyncio
import json
import logging
import os
import shutil
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.services.ai.base import (
    BaseAIProvider,
    ChatMessage,
    ChatResponse,
    ChatResponseChunk,
    ModelInfo,
    ProviderCapability,
)

logger = logging.getLogger("ruby.ai.agy")


class AGYAdapter(BaseAIProvider):
    """
    Adapter for Google Antigravity CLI (AGY).
    Uses host subprocess execution with streaming JSON output,
    model discovery, quota extraction, and usage tracking.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bin_path = self._find_agy_executable()
        if not self.default_model:
            self.default_model = "gemini-3.8-flash-high"

    @classmethod
    def _find_agy_executable(cls) -> Optional[str]:
        env_path = os.environ.get("AGY_BIN_PATH")
        if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
            return env_path

        found = shutil.which("agy")
        if found:
            return found

        candidates = [
            os.path.expanduser("~/.local/bin/agy"),
            "/usr/local/bin/agy",
            "/usr/bin/agy",
        ]
        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        return None

    def is_available(self) -> bool:
        return self.bin_path is not None

    async def get_version(self) -> Optional[str]:
        if not self.bin_path:
            return None
        try:
            proc = await asyncio.create_subprocess_exec(
                self.bin_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            if proc.returncode == 0:
                return stdout.decode().strip()
        except Exception as e:
            logger.debug("Failed to get AGY version: %s", e)
        return None

    async def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        if not self.bin_path:
            return {
                "success": False,
                "latency_ms": 0.0,
                "message": "AGY CLI executable not found on system PATH (checked ~/.local/bin/agy and /usr/local/bin/agy).",
            }

        version = await self.get_version()
        latency = round((time.perf_counter() - start) * 1000, 2)

        if version:
            return {
                "success": True,
                "latency_ms": latency,
                "version": version,
                "message": f"Connected to AGY CLI v{version}",
                "executable_path": self.bin_path,
                "model_count": 6,
            }
        else:
            return {
                "success": True,
                "latency_ms": latency,
                "version": "unknown",
                "message": f"AGY CLI binary detected at {self.bin_path}",
                "executable_path": self.bin_path,
                "model_count": 6,
            }

    async def list_models(self) -> List[ModelInfo]:
        """Discovers available models from AGY CLI via 'agy models'."""
        default_known_models = [
            ("gemini-3.8-flash-high", "Gemini 3.8 Flash (High)", "Fast high-capacity reasoning model"),
            ("gemini-3.8-flash-medium", "Gemini 3.8 Flash (Medium)", "Balanced latency and intelligence"),
            ("gemini-3.8-flash-low", "Gemini 3.8 Flash (Low)", "Ultra-low latency model"),
            ("claude-sonnet-4-6", "Claude Sonnet 4.6 (Thinking)", "Deep analytical reasoning model"),
            ("claude-opus-4-6-thinking", "Claude Opus 4.6 (Thinking)", "High intelligence research model"),
            ("gpt-oss-120b-medium", "GPT-OSS 120B (Medium)", "Open-weights frontier model"),
        ]

        if not self.bin_path:
            return [
                ModelInfo(
                    id=m_id,
                    name=m_name,
                    provider_type="agy",
                    capabilities=[ProviderCapability.CHAT, ProviderCapability.STREAM],
                    is_local=False,
                    description=desc,
                )
                for m_id, m_name, desc in default_known_models
            ]

        try:
            proc = await asyncio.create_subprocess_exec(
                self.bin_path,
                "models",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8.0)
            if proc.returncode == 0:
                raw_out = stdout.decode()
                parsed_models: List[ModelInfo] = []
                for line in raw_out.splitlines():
                    line = line.strip()
                    if not line or line.startswith("⠋") or line.startswith("⠙") or line.startswith("⠹") or "Fetching" in line:
                        continue
                    parts = line.split(None, 1)
                    if len(parts) >= 2:
                        m_id, m_name = parts[0], parts[1]
                        parsed_models.append(
                            ModelInfo(
                                id=m_id,
                                name=m_name,
                                provider_type="agy",
                                capabilities=[ProviderCapability.CHAT, ProviderCapability.STREAM],
                                is_local=False,
                                description=f"AGY provider model ({m_name})",
                            )
                        )
                if parsed_models:
                    return parsed_models
        except Exception as e:
            logger.warning("Error running 'agy models': %s", e)

        return [
            ModelInfo(
                id=m_id,
                name=m_name,
                provider_type="agy",
                capabilities=[ProviderCapability.CHAT, ProviderCapability.STREAM],
                is_local=False,
                description=desc,
            )
            for m_id, m_name, desc in default_known_models
        ]

    def _assemble_prompt(self, messages: List[ChatMessage]) -> str:
        """Flattens conversation turns into a clean structured prompt for AGY CLI."""
        system_instructions = []
        conversation_turns = []

        for m in messages:
            if m.role == "system":
                system_instructions.append(m.content)
            elif m.role == "user":
                conversation_turns.append(f"User: {m.content}")
            elif m.role == "assistant":
                conversation_turns.append(f"Assistant: {m.content}")

        full_prompt = ""
        if system_instructions:
            full_prompt += "INSTRUCTIONS:\n" + "\n\n".join(system_instructions) + "\n\n"
        full_prompt += "\n\n".join(conversation_turns)
        return full_prompt.strip()

    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatResponse:
        if not self.bin_path:
            raise RuntimeError("AGY CLI is not installed or available on this system.")

        target_model = model or self.default_model or "gemini-3.8-flash-high"
        prompt_text = self._assemble_prompt(messages)

        cmd = [
            self.bin_path,
            "-p",
            prompt_text,
            "--output-format",
            "json",
            "--model",
            target_model,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=float(self.timeout_seconds)
            )

            if proc.returncode != 0:
                err_msg = stderr.decode(errors="ignore").strip()
                raise RuntimeError(f"AGY CLI execution failed (exit code {proc.returncode}): {err_msg}")

            raw_str = stdout.decode(errors="ignore").strip()
            data = json.loads(raw_str)
            response_content = data.get("response", "")
            usage = data.get("usage", {})
            total_tokens = usage.get("total_tokens")

            return ChatResponse(
                content=response_content,
                model=target_model,
                tokens_used=total_tokens,
                finish_reason="stop",
            )
        except Exception as e:
            logger.exception("AGY chat execution error: %s", e)
            raise

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[ChatResponseChunk, None]:
        if not self.bin_path:
            raise RuntimeError("AGY CLI is not installed or available on this system.")

        target_model = model or self.default_model or "gemini-3.8-flash-high"
        prompt_text = self._assemble_prompt(messages)

        cmd = [
            self.bin_path,
            "-p",
            prompt_text,
            "--output-format",
            "stream-json",
            "--model",
            target_model,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                line_str = line.decode(errors="ignore").strip()
                if not line_str:
                    continue
                try:
                    event_data = json.loads(line_str)
                    event_type = event_data.get("event")

                    if event_type == "step_update":
                        step_update = event_data.get("step_update", {})
                        text_delta = step_update.get("text_delta")
                        if text_delta:
                            yield ChatResponseChunk(content_delta=text_delta)

                    elif event_type == "result":
                        res_obj = event_data.get("result", {})
                        usage = res_obj.get("usage", {})
                        total_tokens = usage.get("total_tokens")
                        yield ChatResponseChunk(
                            content_delta="",
                            is_done=True,
                            tokens_used=total_tokens,
                            finish_reason="stop",
                        )
                except json.JSONDecodeError:
                    continue

            await proc.wait()
            if proc.returncode != 0:
                err_text = (await proc.stderr.read()).decode(errors="ignore").strip()
                if err_text:
                    logger.warning("AGY stream stderr: %s", err_text)

        except asyncio.CancelledError:
            try:
                proc.terminate()
                await proc.wait()
            except Exception:
                pass
            raise

    async def get_quota_summary(self) -> Dict[str, Any]:
        """
        Executes 'agy -p "/usage" --output-format json' and parses
        command.data.groups for weekly and 5-hour quota windows.
        """
        if not self.bin_path:
            return {"success": False, "error": "AGY CLI not available."}

        cmd = [self.bin_path, "-p", "/usage", "--output-format", "json"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=25.0)

            if proc.returncode != 0:
                return {
                    "success": False,
                    "error": f"Exit code {proc.returncode}: {stderr.decode(errors='ignore').strip()}",
                }

            data = json.loads(stdout.decode(errors="ignore").strip())
            cmd_data = data.get("command", {}).get("data", {})
            raw_groups = cmd_data.get("groups", [])

            parsed_groups = []
            for g in raw_groups:
                g_name = g.get("name", "")
                g_desc = g.get("description", "")
                parsed_buckets = []
                for b in g.get("buckets", []):
                    remaining_fraction = b.get("remaining_fraction", 1.0)
                    remaining_pct = round(remaining_fraction * 100, 1)
                    used_pct = round((1.0 - remaining_fraction) * 100, 1)
                    reset_time_raw = b.get("reset_time")

                    parsed_buckets.append({
                        "id": b.get("id"),
                        "name": b.get("name"),
                        "description": b.get("description", ""),
                        "window": b.get("window"),
                        "remaining_fraction": remaining_fraction,
                        "remaining_percentage": remaining_pct,
                        "used_percentage": used_pct,
                        "reset_time": reset_time_raw,
                    })
                parsed_groups.append({
                    "name": g_name,
                    "description": g_desc,
                    "buckets": parsed_buckets,
                })

            return {
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "groups": parsed_groups,
                "general_description": cmd_data.get("description", ""),
            }

        except Exception as e:
            logger.exception("Failed to fetch AGY quota usage: %s", e)
            return {"success": False, "error": str(e)}
