from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.agent.dag import TaskDAG, TaskNode, TaskStatus
from app.services.agent.events import AgentEvent, EventType
from app.services.ai.base import ChatMessage

logger = logging.getLogger("ruby.agent.compactor")

try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENCODER = None


# Known provider & model context windows (in tokens)
KNOWN_MODEL_CONTEXT_WINDOWS: Dict[str, int] = {
    # Gemini
    "gemini-3.8-flash-high": 1_000_000,
    "gemini-3.8-flash-medium": 1_000_000,
    "gemini-3.8-flash-low": 1_000_000,
    "gemini-1.5-pro": 2_000_000,
    "gemini-1.5-flash": 1_000_000,
    "gemini-2.0-flash": 1_000_000,
    # Claude
    "claude-sonnet-4-6": 200_000,
    "claude-opus-4-6-thinking": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
    "claude-3-7-sonnet": 200_000,
    # OpenAI & Frontier OSS
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-oss-120b-medium": 128_000,
    # Local Ollama Models
    "qwen2.5:7b": 32_768,
    "qwen2.5:4b": 32_768,
    "qwen3:4b": 32_768,
    "llama3.2:latest": 8_192,
    "llama3.2:3b": 8_192,
    "llama3.1:8b": 16_384,
    "mistral:latest": 8_192,
}

DEFAULT_FALLBACK_CONTEXT_WINDOW = 8_192


@dataclass
class ContextBreakdown:
    system_tokens: int = 0
    history_tokens: int = 0
    tools_tokens: int = 0
    retrieval_tokens: int = 0
    task_state_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "system_tokens": self.system_tokens,
            "history_tokens": self.history_tokens,
            "tools_tokens": self.tools_tokens,
            "retrieval_tokens": self.retrieval_tokens,
            "task_state_tokens": self.task_state_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class CompactionCheckpoint:
    version: int = 1
    summarized_rounds: int = 0
    running_summary: str = ""
    preserved_facts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "summarized_rounds": self.summarized_rounds,
            "running_summary": self.running_summary,
            "preserved_facts": self.preserved_facts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CompactionCheckpoint:
        return cls(
            version=data.get("version", 1),
            summarized_rounds=data.get("summarized_rounds", 0),
            running_summary=data.get("running_summary", ""),
            preserved_facts=data.get("preserved_facts", []),
        )


class ContextCompactor:
    """
    Model-aware context management and compaction service for Ruby.
    Calculates context token utilization across system prompt, messages, tools,
    RAG documents, and DAG task state. Preserves active tasks, pending approvals,
    formulas, and exact identifiers while incrementally condensing older turns.
    """

    def __init__(
        self,
        headroom: Optional[float] = None,
        token_budget: Optional[int] = None,
        recent_turns_to_keep: int = 2,
    ):
        self.headroom = headroom if headroom is not None else settings.agent_context_compaction_headroom
        self.token_budget = token_budget if token_budget is not None else settings.agent_token_budget
        self.recent_turns_to_keep = recent_turns_to_keep
        self.checkpoint = CompactionCheckpoint()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimates token count using tiktoken (cl100k_base) or char heuristic."""
        if not text:
            return 0
        if _ENCODER is not None:
            try:
                return len(_ENCODER.encode(text, disallowed_special=()))
            except Exception:
                pass
        return max(1, len(text) // 4)

    @classmethod
    def resolve_model_context_limit(
        cls,
        model_name: Optional[str] = None,
        provider_type: Optional[str] = None,
        explicit_limit: Optional[int] = None,
    ) -> int:
        """Resolves the maximum context window for the selected provider and model."""
        if explicit_limit and explicit_limit > 0:
            return explicit_limit

        m_key = (model_name or "").lower().strip()
        for known_key, limit in KNOWN_MODEL_CONTEXT_WINDOWS.items():
            if known_key in m_key or m_key in known_key:
                return limit

        # Provider heuristics if model name is generic
        p_type = (provider_type or "").lower().strip()
        if p_type == "gemini":
            return 1_000_000
        elif p_type in ("anthropic", "claude"):
            return 200_000
        elif p_type == "openai":
            return 128_000
        elif p_type == "ollama":
            return 8_192

        return DEFAULT_FALLBACK_CONTEXT_WINDOW

    def calculate_effective_limit(
        self,
        model_name: Optional[str] = None,
        provider_type: Optional[str] = None,
        explicit_limit: Optional[int] = None,
    ) -> int:
        """Calculates effective allowable token ceiling after applying safety headroom."""
        raw_limit = self.resolve_model_context_limit(model_name, provider_type, explicit_limit)
        headroom_allowed = int(raw_limit * (1.0 - self.headroom))
        return min(headroom_allowed, self.token_budget)

    def analyze_context(
        self,
        system_instruction: str,
        messages: List[ChatMessage],
        tool_results: Optional[List[Dict[str, Any]]] = None,
        retrieved_documents: Optional[List[Dict[str, Any]]] = None,
        dag: Optional[TaskDAG] = None,
    ) -> ContextBreakdown:
        """Computes exact token breakdown across all context components."""
        sys_tokens = self.estimate_tokens(system_instruction)

        msg_tokens = sum(
            self.estimate_tokens(m.content) + 4
            for m in messages
        )

        tools_tokens = 0
        if tool_results:
            tools_tokens = self.estimate_tokens(json.dumps(tool_results))

        retrieval_tokens = 0
        if retrieved_documents:
            retrieval_tokens = sum(
                self.estimate_tokens(d.get("content", "")) + 10
                for d in retrieved_documents
            )

        dag_tokens = 0
        if dag:
            dag_tokens = sum(
                self.estimate_tokens(f"{n.title} {n.status.value} {n.tool_name} {n.error}")
                for n in dag.nodes.values()
            )

        total = sys_tokens + msg_tokens + tools_tokens + retrieval_tokens + dag_tokens
        return ContextBreakdown(
            system_tokens=sys_tokens,
            history_tokens=msg_tokens,
            tools_tokens=tools_tokens,
            retrieval_tokens=retrieval_tokens,
            task_state_tokens=dag_tokens,
            total_tokens=total,
        )

    def should_compact(
        self,
        breakdown: ContextBreakdown,
        model_name: Optional[str] = None,
        provider_type: Optional[str] = None,
        explicit_limit: Optional[int] = None,
    ) -> bool:
        """Returns True if context exceeds the effective limit."""
        effective_limit = self.calculate_effective_limit(model_name, provider_type, explicit_limit)
        return breakdown.total_tokens >= effective_limit

    def compact(
        self,
        system_instruction: str,
        messages: List[ChatMessage],
        tool_results: Optional[List[Dict[str, Any]]] = None,
        retrieved_documents: Optional[List[Dict[str, Any]]] = None,
        dag: Optional[TaskDAG] = None,
        model_name: Optional[str] = None,
        provider_type: Optional[str] = None,
        conversation_id: str = "default_session",
    ) -> Tuple[List[ChatMessage], Optional[AgentEvent]]:
        """
        Incrementally compacts older conversation turns, verbose tool outputs, and document snippets.
        Preserves active tasks, pending approvals, recent turns, formulas, and exact academic facts.
        """
        initial_breakdown = self.analyze_context(
            system_instruction, messages, tool_results, retrieved_documents, dag
        )

        if not self.should_compact(initial_breakdown, model_name, provider_type):
            return messages, None

        logger.info(
            "Compacting context: %d tokens exceeds limit for %s",
            initial_breakdown.total_tokens, model_name or "default"
        )

        # 1. Separate recent turns from older history
        # We preserve the last (recent_turns_to_keep * 2) user/assistant messages verbatim
        keep_count = max(2, self.recent_turns_to_keep * 2)
        older_messages = messages[:-keep_count] if len(messages) > keep_count else []
        recent_messages = messages[-keep_count:] if len(messages) > keep_count else messages

        # 2. Extract key academic facts, subject codes, formulas from older messages
        preserved_facts = list(self.checkpoint.preserved_facts)
        summary_lines = []

        for m in older_messages:
            content = m.content.strip()
            # Extract specific short formulas, course codes, and exact scores
            fact_matches = re.findall(
                r"\b(?:[A-Z]{2,}\d+[A-Z0-9-]*|dist\[v\]\s*=\s*[^\n,]+|\d+(?:\.\d+)?\s*\/\s*\d+(?:\.\d+)?|CGPA\s*[:=]\s*\d+(?:\.\d+)?)\b",
                content,
                re.IGNORECASE,
            )
            for fm in fact_matches:
                if fm not in preserved_facts:
                    preserved_facts.append(fm)

        # 3. Formulate Consolidated Summary Block
        self.checkpoint.summarized_rounds += len(older_messages)
        summary_bullets = [
            f"{m.role[:1].upper()}: {m.content[:30]}.."
            for m in older_messages
        ]
        combined_summary = f"[Condensed {self.checkpoint.summarized_rounds} turns: {'; '.join(summary_bullets[-4:])}]"
        if preserved_facts:
            combined_summary += f" [Facts: {'; '.join(preserved_facts[-4:])}]"

        self.checkpoint.running_summary = combined_summary
        self.checkpoint.preserved_facts = preserved_facts

        # 4. Synthesize Preserved DAG Task State
        dag_state_block = ""
        if dag:
            unfinished_tasks = [
                n for n in dag.nodes.values()
                if n.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
            ]
            if unfinished_tasks:
                dag_state_block = "[Tasks: " + "; ".join(
                    f"{n.title} ({n.status.value})" for n in unfinished_tasks
                ) + "]"

        # 5. Assemble Compacted Messages
        compacted_messages: List[ChatMessage] = []
        if combined_summary or dag_state_block:
            context_note = combined_summary
            if dag_state_block:
                context_note += "\n" + dag_state_block
            compacted_messages.append(ChatMessage(role="system", content=context_note))

        compacted_messages.extend(recent_messages)

        # 6. Compute new token usage and emit CONTEXT_COMPACTED event
        final_breakdown = self.analyze_context(
            system_instruction, compacted_messages, tool_results, retrieved_documents, None
        )
        tokens_freed = max(1, initial_breakdown.total_tokens - final_breakdown.total_tokens)

        compacted_event = AgentEvent(
            type=EventType.CONTEXT_COMPACTED,
            conversation_id=conversation_id,
            payload={
                "original_tokens": initial_breakdown.total_tokens,
                "compacted_tokens": final_breakdown.total_tokens,
                "tokens_freed": tokens_freed,
                "turns_summarized": len(older_messages),
                "model_name": model_name or "default",
                "effective_limit": self.calculate_effective_limit(model_name, provider_type),
                "checkpoint": self.checkpoint.to_dict(),
            },
        )

        logger.info(
            "Context compacted successfully: %d -> %d tokens (freed %d tokens)",
            initial_breakdown.total_tokens, final_breakdown.total_tokens, tokens_freed
        )

        return compacted_messages, compacted_event
