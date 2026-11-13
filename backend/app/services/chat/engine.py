import time
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import Conversation, Message, Memory
from app.services.retrieval.hybrid import hybrid_retriever, RetrievedChunk
from app.services.retrieval.provenance import context_assembler, citation_validator
from app.services.ai.manager import provider_manager
from app.services.ai.base import ChatMessage
from app.services.search.searxng import searxng_client
from app.services.memory.service import memory_service

logger = logging.getLogger("ruby.chat.engine")


class ThinkTagParser:
    """
    Streaming parser that detects <think>...</think> blocks in real-time,
    emitting thought tokens separately from content tokens.
    """
    def __init__(self):
        self.in_thinking = False
        self.thought_text = ""
        self.response_text = ""
        self.buffer = ""

    def feed(self, delta: str) -> List[tuple[str, str]]:
        self.buffer += delta
        out: List[tuple[str, str]] = []
        while self.buffer:
            if not self.in_thinking:
                if "<think>" in self.buffer:
                    before, _, after = self.buffer.partition("<think>")
                    if before:
                        out.append(("content", before))
                        self.response_text += before
                    self.in_thinking = True
                    self.buffer = after
                else:
                    has_partial = False
                    for i in range(len("<think>") - 1, 0, -1):
                        prefix = "<think>"[:i]
                        if self.buffer.endswith(prefix):
                            safe_part = self.buffer[:-i]
                            if safe_part:
                                out.append(("content", safe_part))
                                self.response_text += safe_part
                            self.buffer = prefix
                            has_partial = True
                            break
                    if has_partial:
                        break
                    else:
                        out.append(("content", self.buffer))
                        self.response_text += self.buffer
                        self.buffer = ""
            else:
                if "</think>" in self.buffer:
                    thought_chunk, _, after = self.buffer.partition("</think>")
                    if thought_chunk:
                        out.append(("think", thought_chunk))
                        self.thought_text += thought_chunk
                    self.in_thinking = False
                    self.buffer = after
                else:
                    has_partial = False
                    for i in range(len("</think>") - 1, 0, -1):
                        prefix = "</think>"[:i]
                        if self.buffer.endswith(prefix):
                            safe_part = self.buffer[:-i]
                            if safe_part:
                                out.append(("think", safe_part))
                                self.thought_text += safe_part
                            self.buffer = prefix
                            has_partial = True
                            break
                    if has_partial:
                        break
                    else:
                        out.append(("think", self.buffer))
                        self.thought_text += self.buffer
                        self.buffer = ""
        return out

    def flush(self) -> List[tuple[str, str]]:
        out: List[tuple[str, str]] = []
        if self.buffer:
            if self.in_thinking:
                out.append(("think", self.buffer))
                self.thought_text += self.buffer
            else:
                out.append(("content", self.buffer))
                self.response_text += self.buffer
            self.buffer = ""
        return out


class StepTracker:
    """
    Lifecycle step tracer for academic chat pipeline.
    Tracks step statuses and timestamps similar to Claude / ChatGPT reasoning traces.
    """
    def __init__(self):
        self.steps: List[Dict[str, Any]] = []

    def update(
        self,
        step_id: str,
        label: str,
        status: str,
        description: str = "",
        details: Any = None,
    ) -> Dict[str, Any]:
        obj = {
            "id": step_id,
            "label": label,
            "status": status,
            "description": description,
            "details": details,
        }
        for i, s in enumerate(self.steps):
            if s["id"] == step_id:
                self.steps[i] = obj
                return obj
        self.steps.append(obj)
        return obj


class ChatEngine:
    """
    Academic Chat Orchestration Engine.
    Handles mode dispatch (Resource-grounded, General, Hybrid, Research, Web Search),
    SearXNG web search integration, context assembly, SSE token streaming,
    live step tracing, thought parsing, and post-generation citation validation.
    """

    def _build_system_prompt(
        self,
        mode: str,
        conversation_prompt: Optional[str] = None,
        has_web_sources: bool = False,
        has_memories: bool = False,
    ) -> str:
        base_instruction = (
            "You are RUBY, a rigorous, local-first personal academic intelligence assistant.\n"
            "Format mathematical equations in LaTeX using $...$ for inline and $$...$$ for block formulas.\n"
            "Use GitHub-flavored markdown with clean headings, bullet points, and code blocks with syntax tags."
        )

        if mode == "resource-grounded":
            mode_instruction = (
                "ANSWER MODE: RESOURCE-GROUNDED (NotebookLM Style).\n"
                "- Ground all claims strictly on the provided Academic Resource Context.\n"
                "- Include exact citations for every factual statement using: [Doc: <Title>, Page: <Page #>, Section: <Section>].\n"
                "- For slides use [Doc: <Title>, Slide: <Slide #>]. For sheets use [Doc: <Title>, Sheet: <Sheet>, Cell: <Cell>].\n"
                "- If the context does not contain sufficient evidence to answer the user's query, state explicitly:\n"
                "  'I did not find sufficient evidence in the uploaded documents to answer this question.'\n"
                "- NEVER fabricate citations, page numbers, or unsupported facts."
            )
        elif mode in ("web-search", "web"):
            mode_instruction = (
                "ANSWER MODE: WEB SEARCH (Live Online Search via SearXNG).\n"
                "- Answer the user's question directly and authoritatively using the provided Live Web Search Results.\n"
                "- Do NOT reference local course documents or fabricate citations.\n"
                "- Attribute facts directly to the search results using clickable markdown links [Source Title](URL) or [Web #X].\n"
                "- Provide up-to-date, comprehensive information from the live internet."
            )
        elif mode == "hybrid":
            mode_instruction = (
                "ANSWER MODE: HYBRID (Grounded Evidence + General Knowledge).\n"
                "- First, provide the answer grounded in the uploaded documents, citing each fact as [Doc: <Title>, Page: <Page #>].\n"
                "- Then, if helpful, add a clearly marked section '### Supplementary General Knowledge' to expand on the topic using general academic knowledge."
            )
        elif mode == "research":
            mode_instruction = (
                "ANSWER MODE: ACADEMIC RESEARCH & COMPARISON.\n"
                "- Synthesize information across multiple uploaded resources.\n"
                "- Compare viewpoints, highlight agreements and discrepancies in definitions or formulas, and cite source documents explicitly.\n"
                "- Maintain rigorous scholarly tone with clear structured analysis."
            )
        else:  # "general"
            mode_instruction = (
                "ANSWER MODE: GENERAL KNOWLEDGE.\n"
                "- Answer using your general academic knowledge base.\n"
                "- Note that no specific document context has been attached for this query."
            )

        web_instruction = ""
        if has_web_sources:
            web_instruction = (
                "\n\nLIVE WEB SEARCH INTEGRATION (SearXNG):\n"
                "- You have access to real-time live web search results.\n"
                "- Cite web facts directly with clickable markdown links: [Source Title](URL) or [Web #X].\n"
                "- Clearly distinguish web search results from locally indexed course materials.\n"
                "- Never fabricate URLs or citations."
            )

        memory_instruction = ""
        if has_memories:
            memory_instruction = (
                "\n\nPERSISTENT LONG-TERM MEMORY:\n"
                "- Verified user profile attributes, background facts, and study preferences are provided in the RECALLED MEMORIES context block.\n"
                "- Naturally adopt and honor the user's stored preferences (e.g. style, notation, language).\n"
                "- When the user asks what you know or remember about them, answer accurately using the recalled memories.\n"
                "- If the user asks you to remember something new, confirm that you have stored it in your long-term memory."
            )

        thinking_instruction = (
            "\n\nREASONING & CHAIN-OF-THOUGHT:\n"
            "- If you reason through complex steps, calculations, or source comparisons before answering, you may enclose your preliminary reasoning inside <think>...</think> tags."
        )

        custom = f"\nCustom Instructions:\n{conversation_prompt}\n" if conversation_prompt else ""
        return f"{base_instruction}\n\n{mode_instruction}{web_instruction}{memory_instruction}{thinking_instruction}{custom}"

    async def stream_chat(
        self,
        session: AsyncSession,
        conversation_id: str,
        user_content: str,
        mode: str = "resource-grounded",
        subject_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        provider_id: Optional[str] = None,
        web_search: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        start_time = time.perf_counter()
        step_tracker = StepTracker()

        # Initial intent analysis step
        mode_label = mode.replace("-", " ").title()
        step_intent = step_tracker.update(
            step_id="intent",
            label="Analyzing Query & Routing Mode",
            status="running",
            description=f"Routing in {mode_label} mode...",
        )
        yield {"type": "step", "step": step_intent}

        # 1. Fetch conversation
        conv_stmt = select(Conversation).where(Conversation.id == conversation_id)
        conv = (await session.execute(conv_stmt)).scalars().first()
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found.")

        # Update conversation title if default
        if conv.title == "New Conversation":
            conv.title = user_content[:40] + ("..." if len(user_content) > 40 else "")

        # 2. Save User Message to SQLite
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=user_content,
            mode=mode,
        )
        session.add(user_msg)
        await session.commit()

        target_subject = subject_id or conv.subject_id
        if mode in ("web-search", "web"):
            step_intent = step_tracker.update(
                step_id="intent",
                label="Mode Routed: Web Search",
                status="completed",
                description="Targeting live web search (SearXNG) without local document retrieval.",
            )
        elif mode in ("resource-grounded", "hybrid", "research"):
            step_intent = step_tracker.update(
                step_id="intent",
                label=f"Mode Routed: {mode_label}",
                status="completed",
                description=f"Targeting local course documents ({target_subject or 'All Course Materials'}).",
            )
        else:
            step_intent = step_tracker.update(
                step_id="intent",
                label="Mode Routed: General Knowledge",
                status="completed",
                description="Using general academic knowledge without document retrieval.",
            )
        yield {"type": "step", "step": step_intent}

        # 2.5 Long-Term Memory Step (Candidate Extraction & Recalling)
        step_mem = step_tracker.update(
            step_id="memory",
            label="Recalling Memory",
            status="running",
            description="Searching active long-term memories and user preferences...",
        )
        yield {"type": "step", "step": step_mem}

        newly_formed_memories: List[Memory] = []
        try:
            candidates = await memory_service.extract_candidates(
                session=session,
                text=user_content,
                conversation_id=conversation_id,
            )
            for cand in candidates:
                if not cand.get("is_duplicate"):
                    stmt_to_save = cand.get("normalized_content") or cand["content"]
                    new_mem = await memory_service.create_memory(
                        session=session,
                        content=stmt_to_save,
                        memory_type=cand["memory_type"],
                        importance_score=cand["importance_score"],
                        confidence=cand["confidence"],
                        is_pinned=(cand["memory_type"] == "profile" or cand.get("is_explicit", False)),
                        source_conversation_id=conversation_id,
                        source_event="chat_auto_extraction",
                    )
                    newly_formed_memories.append(new_mem)
                    yield {
                        "type": "memory_saved",
                        "memory": {
                            "id": new_mem.id,
                            "content": new_mem.content,
                            "memory_type": new_mem.memory_type,
                            "importance_score": new_mem.importance_score,
                            "is_pinned": new_mem.is_pinned,
                        },
                    }
                    logger.info("Chat auto-formed memory: %s", new_mem.content)
        except Exception as e:
            logger.warning("Error during memory candidate extraction: %s", e)

        recalled_memories: List[Memory] = []
        try:
            recalled_memories = await memory_service.get_context_memories(
                session=session,
                query=user_content,
                top_k=4,
            )
        except Exception as e:
            logger.warning("Error recalling memories: %s", e)

        if recalled_memories or newly_formed_memories:
            desc_parts = []
            if recalled_memories:
                desc_parts.append(f"Loaded {len(recalled_memories)} active long-term memories.")
            if newly_formed_memories:
                desc_parts.append(f"Stored {len(newly_formed_memories)} new memory statement.")
            step_mem = step_tracker.update(
                step_id="memory",
                label="Memory Recalled",
                status="completed",
                description=" ".join(desc_parts),
            )
            yield {"type": "step", "step": step_mem}
            yield {
                "type": "memories",
                "memories": [
                    {
                        "id": m.id,
                        "content": m.content,
                        "memory_type": m.memory_type,
                        "is_pinned": m.is_pinned,
                    }
                    for m in recalled_memories
                ],
            }
        else:
            step_mem = step_tracker.update(
                step_id="memory",
                label="Memory Checked",
                status="completed",
                description="0 relevant prior memories found.",
            )
            yield {"type": "step", "step": step_mem}

        # 3. Retrieval Step (if grounded, hybrid, or research)
        retrieved_chunks: List[RetrievedChunk] = []
        retrieval_latency_ms = 0.0

        if mode in ("resource-grounded", "hybrid", "research"):
            step_ret = step_tracker.update(
                step_id="retrieval",
                label="Searching Course Documents",
                status="running",
                description=f"Searching hybrid vector & keyword indexes for: \"{user_content[:60]}...\"",
            )
            yield {"type": "step", "step": step_ret}

            ret_start = time.perf_counter()
            try:
                ret_result = await hybrid_retriever.search(
                    session=session,
                    query=user_content,
                    top_k=8 if mode == "research" else 5,
                    document_ids=document_ids,
                    subject_id=target_subject,
                )
                retrieval_latency_ms = (time.perf_counter() - ret_start) * 1000.0
                retrieved_chunks = ret_result.chunks

                chunk_details = [
                    f"{c.document_title} (Page {c.page_number or 1})"
                    for c in retrieved_chunks[:4]
                ]
                step_ret = step_tracker.update(
                    step_id="retrieval",
                    label="Course Documents Retrieved",
                    status="completed",
                    description=f"Retrieved {len(retrieved_chunks)} relevant sections in {round(retrieval_latency_ms)}ms",
                    details=chunk_details,
                )
                yield {"type": "step", "step": step_ret}

                # Yield sources event so UI can display them immediately
                yield {
                    "type": "sources",
                    "chunks": [c.model_dump() for c in retrieved_chunks],
                    "retrieval_latency_ms": round(retrieval_latency_ms, 2),
                }
            except Exception as e:
                logger.exception("Retrieval error: %s", e)
                step_ret = step_tracker.update(
                    step_id="retrieval",
                    label="Document Retrieval Failed",
                    status="failed",
                    description=f"Error: {str(e)}",
                )
                yield {"type": "step", "step": step_ret}
                yield {
                    "type": "sources_error",
                    "error": f"Document retrieval error: {str(e)}",
                }

        # 4. SearXNG Web Search Step (Web-Search Mode, Manual Toggle, or Auto-Detection)
        web_search_sources: List[Dict[str, Any]] = []
        should_web_search = (
            (mode in ("web-search", "web"))
            or web_search
            or (
                mode in ("general", "hybrid", "research")
                and searxng_client.is_configured()
                and searxng_client.detect_web_search_need(user_content)
            )
        )

        if should_web_search:
            step_web = step_tracker.update(
                step_id="web_search",
                label="Searching Live Web (SearXNG)",
                status="running",
                description=f"Querying SearXNG for: \"{user_content[:60]}...\"",
            )
            yield {"type": "step", "step": step_web}
            yield {
                "type": "web_search_start",
                "query": user_content,
            }

            try:
                web_res = await searxng_client.search(query=user_content, num_results=5)
                if web_res.results:
                    web_search_sources = [r.model_dump() for r in web_res.results]
                    web_details = [
                        {"title": s["title"], "url": s["url"]}
                        for s in web_search_sources
                    ]
                    step_web = step_tracker.update(
                        step_id="web_search",
                        label="Web Search Complete",
                        status="completed",
                        description=f"Found {len(web_search_sources)} live web sources in {round(web_res.latency_ms)}ms",
                        details=web_details,
                    )
                    yield {"type": "step", "step": step_web}
                    yield {
                        "type": "web_sources",
                        "sources": web_search_sources,
                    }
                elif web_res.error:
                    step_web = step_tracker.update(
                        step_id="web_search",
                        label="Web Search Unavailable",
                        status="failed",
                        description=web_res.error,
                    )
                    yield {"type": "step", "step": step_web}
                    yield {
                        "type": "web_search_error",
                        "error": web_res.error,
                    }
                else:
                    step_web = step_tracker.update(
                        step_id="web_search",
                        label="Web Search Returned No Results",
                        status="completed",
                        description="SearXNG returned 0 results for this query.",
                    )
                    yield {"type": "step", "step": step_web}
            except Exception as e:
                logger.exception("SearXNG search error: %s", e)
                step_web = step_tracker.update(
                    step_id="web_search",
                    label="Web Search Error",
                    status="failed",
                    description=str(e),
                )
                yield {"type": "step", "step": step_web}
                yield {
                    "type": "web_search_error",
                    "error": f"SearXNG search error: {str(e)}",
                }

        # 5. Assemble Context & System Prompt
        context_block = context_assembler.assemble_context(retrieved_chunks) if retrieved_chunks else None
        
        web_context_block = None
        if web_search_sources:
            web_lines = [
                "=== LIVE WEB SEARCH RESULTS (SearXNG) ===",
                "Information retrieved from the live web for this query:",
            ]
            for i, src in enumerate(web_search_sources, 1):
                web_lines.append(f"[Web #{i}] {src['title']}\nURL: {src['url']}\nSnippet: {src['snippet']}\n")
            web_lines.append("=========================================")
            web_context_block = "\n".join(web_lines)

        memory_context_block = None
        if recalled_memories:
            mem_lines = [
                "=== RECALLED MEMORIES (Long-term User Memory) ===",
                "The following are persistent memories, verified user profile facts, and preferences stored in Ruby's long-term memory:",
            ]
            for m in recalled_memories:
                pinned_badge = " [Pinned]" if m.is_pinned else ""
                mem_lines.append(f"- [{m.memory_type.upper()}{pinned_badge}] {m.content}")
            mem_lines.append("=================================================")
            memory_context_block = "\n".join(mem_lines)

        system_prompt = self._build_system_prompt(
            mode=mode,
            conversation_prompt=conv.system_prompt,
            has_web_sources=bool(web_search_sources),
            has_memories=bool(recalled_memories),
        )

        # 6. Fetch previous conversation history (last 10 messages for context)
        hist_stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        prev_messages = (await session.execute(hist_stmt)).scalars().all()

        ai_messages: List[ChatMessage] = [ChatMessage(role="system", content=system_prompt)]
        
        # Add past turns
        for m in prev_messages[:-1]:  # exclude the one we just inserted
            ai_messages.append(ChatMessage(role=m.role, content=m.content))

        # Build final user prompt with context blocks
        prompt_parts: List[str] = []
        if memory_context_block:
            prompt_parts.append(memory_context_block)
        if context_block and mode in ("resource-grounded", "hybrid", "research"):
            prompt_parts.append(context_block)
        if web_context_block:
            prompt_parts.append(web_context_block)
        prompt_parts.append(f"User Question:\n{user_content}")
        final_prompt = "\n\n".join(prompt_parts)

        ai_messages.append(ChatMessage(role="user", content=final_prompt))

        step_ctx = step_tracker.update(
            step_id="context",
            label="Context & Guidelines Prepared",
            status="completed",
            description=f"Assembled context with {len(prompt_parts)} blocks for inference.",
        )
        yield {"type": "step", "step": step_ctx}

        # 7. Stream from active AI Provider
        try:
            adapter = await provider_manager.get_active_adapter(session, provider_id=provider_id)
        except Exception as e:
            logger.exception("Failed to initialize active AI provider: %s", e)
            error_msg = (
                f"Error: Could not connect to AI provider ({str(e)}). "
                "Please check that Ollama is running or configure an AI provider in Settings."
            )
            step_fail = step_tracker.update(
                step_id="generation",
                label="AI Provider Unavailable",
                status="failed",
                description=str(e),
            )
            yield {"type": "step", "step": step_fail}
            yield {"type": "token", "content": error_msg}
            yield {
                "type": "done",
                "message_id": "",
                "full_content": error_msg,
                "citations": [],
                "web_sources": [],
                "steps": step_tracker.steps,
                "thinking_content": "",
                "diagnostics": {"error": str(e), "steps": step_tracker.steps},
            }
            return

        model_name = getattr(adapter, "default_model", getattr(adapter, "model_name", adapter.name))
        step_gen = step_tracker.update(
            step_id="generation",
            label=f"Synthesizing Response ({model_name})",
            status="running",
            description=f"Streaming response with {model_name}...",
        )
        yield {"type": "step", "step": step_gen}

        gen_start = time.perf_counter()
        parser = ThinkTagParser()
        first_think = True

        try:
            async for chunk in adapter.stream_chat(ai_messages):
                delta = chunk.content_delta
                for item_type, text in parser.feed(delta):
                    if item_type == "think":
                        if first_think:
                            first_think = False
                            step_think = step_tracker.update(
                                step_id="thinking",
                                label="AI Internal Reasoning",
                                status="running",
                                description="Generating chain-of-thought breakdown...",
                            )
                            yield {"type": "step", "step": step_think}
                        yield {
                            "type": "think_token",
                            "content": text,
                        }
                    else:
                        yield {
                            "type": "token",
                            "content": text,
                        }

            # Flush any remaining buffer in parser
            for item_type, text in parser.flush():
                if item_type == "think":
                    yield {
                        "type": "think_token",
                        "content": text,
                    }
                else:
                    yield {
                        "type": "token",
                        "content": text,
                    }

            if not first_think:
                step_think = step_tracker.update(
                    step_id="thinking",
                    label="Reasoning Complete",
                    status="completed",
                    description="Internal chain of thought concluded.",
                )
                yield {"type": "step", "step": step_think}

        except Exception as e:
            logger.exception("AI provider generation error: %s", e)
            error_msg = f"\n\n[Inference Error: {str(e)}]"
            parser.response_text += error_msg
            yield {
                "type": "token",
                "content": error_msg,
            }

        full_response = parser.response_text.strip()
        thinking_content = parser.thought_text.strip()

        # Handle empty model response (Root Cause Fix for Issue A)
        if not full_response:
            logger.warning("AI provider yielded empty response; generating helpful fallback message.")
            full_response = (
                "The AI model returned an empty response. "
                "This may happen if the local model is loading into memory or timed out. "
                "Please click Retry below to resubmit your message."
            )
            yield {
                "type": "token",
                "content": full_response,
            }

        gen_latency_ms = (time.perf_counter() - gen_start) * 1000.0
        total_latency_ms = (time.perf_counter() - start_time) * 1000.0

        step_gen = step_tracker.update(
            step_id="generation",
            label=f"Response Synthesized ({model_name})",
            status="completed",
            description=f"Generated answer in {round(gen_latency_ms)}ms",
        )
        yield {"type": "step", "step": step_gen}

        # If general mode without web search, append clear indication
        if mode == "general" and not web_search_sources:
            tag = "\n\n*[General Knowledge: Answered using model knowledge without document grounding]*"
            full_response += tag
            yield {"type": "token", "content": tag}

        # 8. Post-generation Citation Validation
        if retrieved_chunks:
            step_val = step_tracker.update(
                step_id="validation",
                label="Verifying Citations & Grounding",
                status="running",
                description="Cross-referencing claims against source chunks...",
            )
            yield {"type": "step", "step": step_val}

            validation_report = citation_validator.validate_response(
                response_text=full_response,
                retrieved_chunks=retrieved_chunks,
            )

            step_val = step_tracker.update(
                step_id="validation",
                label="Grounding Verified",
                status="completed" if validation_report.is_grounded else "failed",
                description=f"Validated {len(validation_report.citations)} citations • {validation_report.message}",
            )
            yield {"type": "step", "step": step_val}
        else:
            validation_report = citation_validator.validate_response(
                response_text=full_response,
                retrieved_chunks=[],
            )
            step_val = step_tracker.update(
                step_id="validation",
                label="Direct Synthesis",
                status="completed",
                description="Answer generated from live web search / general knowledge without local document citations.",
            )
            yield {"type": "step", "step": step_val}

        diagnostics = {
            "retrieval_latency_ms": round(retrieval_latency_ms, 2),
            "generation_latency_ms": round(gen_latency_ms, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "mode": mode,
            "provider": adapter.provider_type,
            "model": model_name,
            "grounding": validation_report.model_dump(),
            "web_sources_count": len(web_search_sources),
            "web_sources": web_search_sources,
            "recalled_memories_count": len(recalled_memories),
            "recalled_memories": [
                {"id": m.id, "content": m.content, "memory_type": m.memory_type}
                for m in recalled_memories
            ],
            "newly_formed_memories_count": len(newly_formed_memories),
            "newly_formed_memories": [
                {"id": m.id, "content": m.content, "memory_type": m.memory_type}
                for m in newly_formed_memories
            ],
            "steps": step_tracker.steps,
            "thinking_content": thinking_content,
        }

        # 9. Save Assistant Message to SQLite
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
            mode=mode,
            provider_used=adapter.provider_type,
            model_used=model_name,
            citations=[c.model_dump() for c in validation_report.citations],
            diagnostics=diagnostics,
            tokens_used=len(full_response) // 4,
        )
        session.add(assistant_msg)
        await session.commit()

        # 10. Final Done Event
        yield {
            "type": "done",
            "message_id": assistant_msg.id,
            "full_content": full_response,
            "citations": [c.model_dump() for c in validation_report.citations],
            "web_sources": web_search_sources,
            "recalled_memories": [
                {"id": m.id, "content": m.content, "memory_type": m.memory_type}
                for m in recalled_memories
            ],
            "newly_formed_memories": [
                {"id": m.id, "content": m.content, "memory_type": m.memory_type}
                for m in newly_formed_memories
            ],
            "steps": step_tracker.steps,
            "thinking_content": thinking_content,
            "diagnostics": diagnostics,
        }

    async def generate_message_sync(
        self,
        session: AsyncSession,
        conversation_id: str,
        user_content: str,
        mode: str = "resource-grounded",
        subject_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        provider_id: Optional[str] = None,
        web_search: bool = False,
    ) -> Message:
        """Non-streaming fallback method."""
        last_event: Dict[str, Any] = {}
        async for evt in self.stream_chat(
            session=session,
            conversation_id=conversation_id,
            user_content=user_content,
            mode=mode,
            subject_id=subject_id,
            document_ids=document_ids,
            provider_id=provider_id,
            web_search=web_search,
        ):
            if evt["type"] == "done":
                last_event = evt

        msg_id = last_event.get("message_id")
        if not msg_id:
            # If done had no message_id (e.g. error), fetch last message
            stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.desc())
            return (await session.execute(stmt)).scalars().first()

        stmt = select(Message).where(Message.id == msg_id)
        return (await session.execute(stmt)).scalars().first()


chat_engine = ChatEngine()
