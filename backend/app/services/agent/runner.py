from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.agent.cancellation import CancellationToken
from app.services.agent.compactor import ContextCompactor
from app.services.agent.events import AgentEvent, EventType
from app.services.agent.permissions import PermissionManager, permission_manager as default_pm
from app.services.agent.planner import AgentPlanner
from app.services.ai.base import BaseAIProvider, ChatMessage, ChatResponseChunk
from app.services.memory.academic_service import academic_memory_service
from app.services.tools.registry import ToolRegistry, tool_registry as default_tr

logger = logging.getLogger("ruby.agent.runner")


class AgentRunner:
    """
    Core Action/Observation Agent Execution Loop for Ruby.
    Adopts OpenHands action/observation event streams, OpenCode's fine-grained
    wildcard permission interceptor, cooperative cancellation tokens,
    and model-aware context window compaction.
    """

    def __init__(
        self,
        provider: BaseAIProvider,
        tool_registry: Optional[ToolRegistry] = None,
        permission_manager: Optional[PermissionManager] = None,
        compactor: Optional[ContextCompactor] = None,
    ):
        self.provider = provider
        self.tool_registry = tool_registry or default_tr
        self.permission_manager = permission_manager or default_pm
        self.compactor = compactor or ContextCompactor()

    async def run(
        self,
        prompt: str,
        conversation_id: str,
        mode: str = "auto",
        model: Optional[str] = None,
        cancellation_token: Optional[CancellationToken] = None,
        session: Optional[AsyncSession] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Executes the agent loop, streaming typed AgentEvents for each
        state transition, tool action, approval request, and token delta.
        """
        token = cancellation_token or CancellationToken()
        start_time = time.perf_counter()

        try:
            # 1. Initialization and Planning Step
            token.check_cancelled()
            plan_step_id = f"step_plan_{uuid.uuid4().hex[:8]}"
            yield AgentEvent(
                type=EventType.STEP_START,
                conversation_id=conversation_id,
                step_id=plan_step_id,
                payload={"label": "Intent & Tool Planning", "status": "running"},
            )

            plan = await AgentPlanner.plan_intent_and_tools(
                provider=self.provider,
                prompt=prompt,
                mode=mode,
            )

            effective_mode = plan["effective_mode"]
            selected_tools = plan.get("selected_tools", [])

            yield AgentEvent(
                type=EventType.STEP_COMPLETE,
                conversation_id=conversation_id,
                step_id=plan_step_id,
                payload={
                    "label": f"Mode Routed: {effective_mode.replace('-', ' ').title()}",
                    "effective_mode": effective_mode,
                    "mode_explanation": plan.get("mode_explanation", ""),
                    "tools_count": len(selected_tools),
                    "status": "completed",
                },
            )

            # 2. Tool Execution Phase (Actions and Observations)
            tool_results = []
            web_sources = []
            retrieved_chunks = []

            for idx, tool_call in enumerate(selected_tools):
                token.check_cancelled()
                tool_name = tool_call["name"]
                tool_args = tool_call.get("arguments", {})
                action_step_id = f"step_tool_{tool_name}_{idx}_{uuid.uuid4().hex[:6]}"

                # Emit Action Event
                yield AgentEvent(
                    type=EventType.ACTION_TOOL_CALL,
                    conversation_id=conversation_id,
                    step_id=action_step_id,
                    payload={
                        "tool_name": tool_name,
                        "arguments": tool_args,
                        "status": "awaiting_execution",
                    },
                )

                # Permission Gate Evaluation
                req_id = f"perm_{uuid.uuid4().hex[:8]}"
                effect = self.permission_manager.evaluate(tool_name)

                if effect == "ask":
                    yield AgentEvent(
                        type=EventType.PERMISSION_REQUEST,
                        conversation_id=conversation_id,
                        step_id=action_step_id,
                        payload={
                            "request_id": req_id,
                            "tool_name": tool_name,
                            "arguments": tool_args,
                            "effect": effect,
                            "message": f"Tool '{tool_name}' requires approval before execution.",
                        },
                    )

                is_allowed = await self.permission_manager.check_or_request_approval(
                    tool_name=tool_name,
                    arguments=tool_args,
                    request_id=req_id,
                )

                if not is_allowed:
                    logger.warning("Execution of '%s' denied by policy or user", tool_name)
                    obs = {
                        "tool_name": tool_name,
                        "success": False,
                        "error": "Tool execution was denied by permission policy or user rejection.",
                        "execution_time_ms": 0.0,
                    }
                    tool_results.append(obs)
                    yield AgentEvent(
                        type=EventType.OBSERVATION_TOOL_RESULT,
                        conversation_id=conversation_id,
                        step_id=action_step_id,
                        payload=obs,
                    )
                    continue

                # Execute Tool with exception boundary
                t_start = time.perf_counter()
                exec_res = await self.tool_registry.execute(
                    name=tool_name,
                    arguments=tool_args,
                    session=session,
                )
                t_elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

                obs = {
                    "tool_name": tool_name,
                    "success": exec_res.success,
                    "data": exec_res.data,
                    "error": exec_res.error,
                    "execution_time_ms": t_elapsed_ms,
                }
                tool_results.append(obs)

                if exec_res.success and exec_res.data:
                    if tool_name == "web_search" and isinstance(exec_res.data, dict):
                        web_sources.extend(exec_res.data.get("results", []))
                    elif tool_name == "document_search" and isinstance(exec_res.data, dict):
                        retrieved_chunks.extend(exec_res.data.get("chunks", []))

                yield AgentEvent(
                    type=EventType.OBSERVATION_TOOL_RESULT,
                    conversation_id=conversation_id,
                    step_id=action_step_id,
                    payload=obs,
                )

            # 3. Context Assembly & Final Synthesis
            token.check_cancelled()
            synth_step_id = f"step_synth_{uuid.uuid4().hex[:8]}"
            yield AgentEvent(
                type=EventType.STEP_START,
                conversation_id=conversation_id,
                step_id=synth_step_id,
                payload={"label": "Synthesizing Final Response", "status": "running"},
            )

            # Construct Prompt Context
            system_msg = (
                f"You are Ruby, an academic AI assistant. Current mode: {effective_mode}.\n"
                "Provide an accurate, rigorous, and clearly structured answer."
            )
            context_blocks = []
            if web_sources:
                context_blocks.append("LIVE WEB SOURCES:\n" + "\n".join(
                    f"- [{s.get('title')}]({s.get('url')}): {s.get('snippet')}"
                    for s in web_sources[:5]
                ))
            if retrieved_chunks:
                context_blocks.append("ACADEMIC NOTES & DOCUMENTS:\n" + "\n".join(
                    f"[{c.get('subject_code', 'DOC')} p.{c.get('page_number', '?')}]: {c.get('content')}"
                    for c in retrieved_chunks[:5]
                ))
            for tr in tool_results:
                if tr["tool_name"] not in ("web_search", "document_search") and tr["success"]:
                    context_blocks.append(f"TOOL RESULT ({tr['tool_name']}):\n{tr['data']}")

            # Fetch canonical structured academic records if relevant
            if session and any(w in prompt.lower() for w in ["mark", "score", "grade", "gpa", "cgpa", "isa", "esa", "exam", "performance", "result"]):
                try:
                    summary = await academic_memory_service.get_average_performance(session)
                    if summary.get("average_percentage") is not None:
                        context_blocks.append(
                            f"STUDENT ACADEMIC PROFILE (VERIFIED SQL RECORDS):\n"
                            f"- Average Performance: {summary['average_percentage']}%\n"
                            f"- Total Tracked Assessments: {summary['total_assessments']}"
                        )
                except Exception as e:
                    logger.debug("Non-fatal academic record retrieval note: %s", e)

            assembled_user_prompt = prompt
            if context_blocks:
                assembled_user_prompt += "\n\nCONTEXT:\n" + "\n\n".join(context_blocks)

            chat_messages = [
                ChatMessage(role="system", content=system_msg),
                ChatMessage(role="user", content=assembled_user_prompt),
            ]

            # Context Compaction Check & Trigger
            compacted_messages, comp_event = self.compactor.compact(
                system_instruction=system_msg,
                messages=chat_messages,
                tool_results=tool_results,
                retrieved_documents=retrieved_chunks,
                model_name=model,
                provider_type=self.provider.provider_type if hasattr(self.provider, "provider_type") else None,
                conversation_id=conversation_id,
            )

            if comp_event:
                yield comp_event

            # Stream generation tokens using compacted context
            full_response = ""
            async for chunk in self.provider.stream_chat(compacted_messages, model=model):
                token.check_cancelled()
                if chunk.content_delta:
                    full_response += chunk.content_delta
                    yield AgentEvent(
                        type=EventType.TOKEN_DELTA,
                        conversation_id=conversation_id,
                        step_id=synth_step_id,
                        payload={"delta": chunk.content_delta},
                    )

            total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            yield AgentEvent(
                type=EventType.STEP_COMPLETE,
                conversation_id=conversation_id,
                step_id=synth_step_id,
                payload={"label": "Response Complete", "status": "completed"},
            )

            # 4. Agent Completion Event
            yield AgentEvent(
                type=EventType.AGENT_COMPLETE,
                conversation_id=conversation_id,
                payload={
                    "final_answer": full_response,
                    "effective_mode": effective_mode,
                    "tools_executed": len(tool_results),
                    "total_latency_ms": total_latency_ms,
                    "web_sources_count": len(web_sources),
                    "retrieved_chunks_count": len(retrieved_chunks),
                },
            )

        except asyncio.CancelledError:
            logger.info("AgentRunner execution cancelled for conversation %s", conversation_id)
            yield AgentEvent(
                type=EventType.AGENT_CANCEL,
                conversation_id=conversation_id,
                payload={"message": "Execution was cancelled by the user."},
            )
            raise

        except Exception as e:
            logger.exception("AgentRunner unhandled error: %s", e)
            yield AgentEvent(
                type=EventType.AGENT_ERROR,
                conversation_id=conversation_id,
                payload={"error": str(e)},
            )
            raise
