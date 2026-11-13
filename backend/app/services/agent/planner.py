import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from app.services.ai.base import BaseAIProvider, ChatMessage
from app.services.tools.sanitizer import search_query_sanitizer

logger = logging.getLogger("ruby.agent.planner")

MODE_DESCRIPTIONS = {
    "resource-grounded": "Study & Course Notes: Answers strictly from uploaded materials with exact page citations.",
    "web-search": "Live Web Search: Up-to-date real-time external information from SearXNG.",
    "research": "Academic Research: Multi-document comparison, literature synthesis, and cross-source analysis.",
    "coding": "Coding & Algorithm Sandbox: Python algorithm execution, DSA traces, and technical debugging.",
    "general": "General Knowledge: Broad academic conceptual explanations without document grounding.",
}


class AgentPlanner:
    """
    Intelligent Intent Classifier, Mode Router, and Focused Tool Planner.
    Uses the currently selected conversational LLM without introducing
    a separate routing model or external downloads.
    """

    @classmethod
    async def plan_intent_and_tools(
        cls,
        provider: BaseAIProvider,
        prompt: str,
        mode: str = "auto",
        conversation_history: Optional[List[ChatMessage]] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Analyzes the prompt, determines effective mode, and selects tools with focused arguments.
        """
        # If user explicitly selected a manual mode, honor it directly
        effective_mode = mode
        if mode == "auto":
            effective_mode = cls._heuristic_classify_mode(prompt)
        elif mode in ("study", "grounded"):
            effective_mode = "resource-grounded"
        elif mode in ("web", "websearch"):
            effective_mode = "web-search"

        mode_explanation = MODE_DESCRIPTIONS.get(
            effective_mode,
            f"Routing in {effective_mode.replace('-', ' ').title()} mode based on query characteristics.",
        )

        # Decide tools required based on query & effective mode
        tools_to_call: List[Dict[str, Any]] = []

        # 1. Math / Equation detection
        math_match = cls._detect_math_need(prompt)
        if math_match:
            tools_to_call.append(math_match)

        # 2. DSA / Algorithm Trace detection
        dsa_match = cls._detect_dsa_need(prompt)
        if dsa_match:
            tools_to_call.append(dsa_match)

        # 3. Web Search detection
        web_match = cls._detect_web_need(prompt, effective_mode)
        if web_match:
            tools_to_call.append(web_match)

        # 4. Document Search detection
        doc_match = cls._detect_document_need(prompt, effective_mode)
        if doc_match:
            tools_to_call.append(doc_match)

        # 5. System hardware detection
        if any(w in prompt.lower() for w in ["gpu", "vram", "hardware stats", "system info", "cpu usage"]):
            if "gpu" in prompt.lower() or "vram" in prompt.lower():
                tools_to_call.append({"name": "get_gpu_stats", "arguments": {}})
            else:
                tools_to_call.append({"name": "get_system_info", "arguments": {}})

        # 6. Explicit Memory Save detection
        if any(w in prompt.lower() for w in ["store in memory", "save in memory", "save to memory", "store my", "save my", "remember my", "remember this", "save this", "store this"]):
            mem_type = "profile" if any(w in prompt.lower() for w in ["my name", "my favorite", "i prefer", "call me"]) else "episodic"
            tools_to_call.append({
                "name": "save_memory",
                "arguments": {
                    "content": prompt,
                    "memory_type": mem_type,
                    "is_pinned": mem_type == "profile",
                },
            })

        return {
            "effective_mode": effective_mode,
            "mode_explanation": mode_explanation,
            "selected_tools": tools_to_call,
            "objective": f"Address user request in {effective_mode} mode using {len(tools_to_call)} tool(s).",
        }

    @classmethod
    def _heuristic_classify_mode(cls, prompt: str) -> str:
        lower = prompt.lower()

        # 1. Live online info / current events -> Web Search
        if any(w in lower for w in ["latest", "current", "news", "today", "searxng", "documentation online", "release", "2026", "real-time"]):
            return "web-search"

        # 2. Math / Equations -> Study / resource-grounded
        if any(w in lower for w in ["solve", "equation", "derivative", "integral", "differentiate", "calculate", "eigenvalue", "matrix determinant"]):
            return "resource-grounded"

        # 3. Code / DSA -> Coding
        if any(w in lower for w in ["python", "code", "implement", "debug", "trace", "binary search", "bubble sort", "algorithm", "complexity"]):
            return "coding"

        # 4. Cross-document comparison / Literature -> Research
        if any(w in lower for w in ["compare", "literature review", "across notes", "different papers", "contrast definitions", "synthesize"]):
            return "research"

        # 5. Uploaded course materials / syllabus / slides -> resource-grounded
        if any(w in lower for w in ["notes", "lecture", "textbook", "slides", "syllabus", "cn material", "exam notes"]):
            return "resource-grounded"

        return "general"

    @classmethod
    def _detect_web_need(cls, prompt: str, mode: str) -> Optional[Dict[str, Any]]:
        lower = prompt.lower()
        needs_web = (
            mode in ("web-search", "web")
            or any(w in lower for w in ["search the web", "web search", "latest developments", "recent updates", "current status", "find online", "searxng"])
            or (mode in ("research", "general") and any(w in lower for w in ["latest", "recent", "newest", "2026"]))
        )
        if not needs_web:
            return None

        # Generate focused, concise search queries (NOT the raw prompt!)
        focused_queries = search_query_sanitizer.extract_queries_from_prompt(prompt, max_queries=2)
        if not focused_queries:
            focused_queries = [search_query_sanitizer.sanitize_single_query(prompt) or "recent developments"]

        return {
            "name": "web_search",
            "arguments": {
                "queries": focused_queries,
                "num_results": 4,
            },
        }

    @classmethod
    def _detect_document_need(cls, prompt: str, mode: str) -> Optional[Dict[str, Any]]:
        if mode in ("resource-grounded", "research", "hybrid"):
            # Distill clean semantic query
            clean_query = search_query_sanitizer.sanitize_single_query(prompt, max_words=15) or prompt[:80]
            return {
                "name": "document_search",
                "arguments": {
                    "query": clean_query,
                    "top_k": 6 if mode == "research" else 4,
                },
            }
        return None

    @classmethod
    def _detect_math_need(cls, prompt: str) -> Optional[Dict[str, Any]]:
        lower = prompt.lower()
        # Check equation solving
        eq_patterns = [
            r"solve\s+(?:the\s+equation\s+)?([a-zA-Z0-9\s\+\-\*\/\^\=]+)(?:\s+for\s+([a-zA-Z]))?",
            r"(?:what\s+is\s+)?(?:the\s+solution\s+to\s+)?([a-zA-Z0-9\s\+\-\*\/\^]+\s*=\s*[a-zA-Z0-9\s\+\-\*\/\^]+)",
        ]
        for pat in eq_patterns:
            m = re.search(pat, prompt, flags=re.IGNORECASE)
            if m:
                eq_str = m.group(1).strip()
                var_str = m.group(2).strip() if (m.lastindex and m.lastindex >= 2 and m.group(2)) else "x"
                if len(eq_str) > 2 and any(c in eq_str for c in ["x", "y", "z", "+", "-", "*", "="]):
                    return {
                        "name": "solve_equation",
                        "arguments": {"equation": eq_str, "variable": var_str},
                    }

        # Check pure calculation (e.g. 2**10 + 5 or derivative)
        if any(w in lower for w in ["calculate", "evaluate", "compute"]):
            calc_expr = re.sub(r"^(calculate|evaluate|compute)\s+", "", prompt, flags=re.IGNORECASE).strip(" ?.")
            if calc_expr:
                return {
                    "name": "calculate",
                    "arguments": {"expression": calc_expr},
                }

        return None

    @classmethod
    def _detect_dsa_need(cls, prompt: str) -> Optional[Dict[str, Any]]:
        lower = prompt.lower()
        if "binary search" in lower:
            # Extract array and target if present
            numbers = [int(n) for n in re.findall(r"\b\d+\b", prompt)]
            target = numbers[-1] if len(numbers) > 1 else (numbers[0] if numbers else 7)
            arr = sorted(list(set(numbers[:-1]))) if len(numbers) > 1 else [1, 3, 5, 7, 9, 11, 13, 15]
            return {
                "name": "trace_dsa",
                "arguments": {"algorithm": "binary_search", "array": arr, "target": target},
            }
        elif "bubble sort" in lower:
            numbers = [int(n) for n in re.findall(r"\b\d+\b", prompt)]
            arr = numbers if len(numbers) >= 3 else [64, 34, 25, 12, 22, 11, 90]
            return {
                "name": "trace_dsa",
                "arguments": {"algorithm": "bubble_sort", "array": arr},
            }
        return None
