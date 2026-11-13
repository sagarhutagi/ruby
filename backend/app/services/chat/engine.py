import time
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import Conversation, Message
from app.services.retrieval.hybrid import hybrid_retriever, RetrievedChunk
from app.services.retrieval.provenance import context_assembler, citation_validator
from app.services.ai.manager import provider_manager
from app.services.ai.base import ChatMessage

logger = logging.getLogger("ruby.chat.engine")


class ChatEngine:
    """
    Academic Chat Orchestration Engine.
    Handles mode dispatch (Resource-grounded, General, Hybrid, Research),
    context assembly, SSE token streaming, and post-generation citation validation.
    """

    def _build_system_prompt(self, mode: str, conversation_prompt: Optional[str] = None) -> str:
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

        custom = f"\nCustom Instructions:\n{conversation_prompt}\n" if conversation_prompt else ""
        return f"{base_instruction}\n\n{mode_instruction}{custom}"

    async def stream_chat(
        self,
        session: AsyncSession,
        conversation_id: str,
        user_content: str,
        mode: str = "resource-grounded",
        subject_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        provider_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        start_time = time.perf_counter()

        # 1. Fetch conversation
        conv_stmt = select(Conversation).where(Conversation.id == conversation_id)
        conv = (await session.execute(conv_stmt)).scalars().first()
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found.")

        # Update conversation title if default
        if conv.title == "New Conversation":
            # Set title from first query snippet
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

        # 3. Retrieval Step (if grounded, hybrid, or research)
        retrieved_chunks: List[RetrievedChunk] = []
        retrieval_latency_ms = 0.0
        target_subject = subject_id or conv.subject_id

        if mode in ("resource-grounded", "hybrid", "research"):
            ret_start = time.perf_counter()
            ret_result = await hybrid_retriever.search(
                session=session,
                query=user_content,
                top_k=8 if mode == "research" else 5,
                document_ids=document_ids,
                subject_id=target_subject,
            )
            retrieval_latency_ms = (time.perf_counter() - ret_start) * 1000.0
            retrieved_chunks = ret_result.chunks

            # Yield sources event so UI can display them immediately
            yield {
                "type": "sources",
                "chunks": [c.model_dump() for c in retrieved_chunks],
                "retrieval_latency_ms": round(retrieval_latency_ms, 2),
            }

        # 4. Assemble Context & System Prompt
        context_block = context_assembler.assemble_context(retrieved_chunks) if retrieved_chunks else None
        system_prompt = self._build_system_prompt(mode, conv.system_prompt)

        # 5. Fetch previous conversation history (last 10 messages for context)
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

        # Add current user prompt with context block
        final_prompt = user_content
        if context_block and mode in ("resource-grounded", "hybrid", "research"):
            final_prompt = f"{context_block}\n\nUser Question:\n{user_content}"
        ai_messages.append(ChatMessage(role="user", content=final_prompt))

        # 6. Stream from active AI Provider
        adapter = await provider_manager.get_active_adapter(session, provider_id=provider_id)
        accumulated_text: List[str] = []
        gen_start = time.perf_counter()

        model_name = getattr(adapter, "default_model", getattr(adapter, "model_name", adapter.name))

        try:
            async for chunk in adapter.stream_chat(ai_messages):
                delta = chunk.content_delta
                accumulated_text.append(delta)
                yield {
                    "type": "token",
                    "content": delta,
                }
        except Exception as e:
            logger.exception("AI provider generation error: %s", e)
            error_msg = f"\n\n[Inference Error: {str(e)}]"
            accumulated_text.append(error_msg)
            yield {
                "type": "token",
                "content": error_msg,
            }

        full_response = "".join(accumulated_text)
        gen_latency_ms = (time.perf_counter() - gen_start) * 1000.0
        total_latency_ms = (time.perf_counter() - start_time) * 1000.0

        # If general mode, append clear indication
        if mode == "general":
            tag = "\n\n*[General Knowledge: Answered using model knowledge without document grounding]*"
            full_response += tag
            yield {"type": "token", "content": tag}

        # 7. Post-generation Citation Validation
        validation_report = citation_validator.validate_response(
            response_text=full_response,
            retrieved_chunks=retrieved_chunks,
        )

        diagnostics = {
            "retrieval_latency_ms": round(retrieval_latency_ms, 2),
            "generation_latency_ms": round(gen_latency_ms, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "mode": mode,
            "provider": adapter.provider_type,
            "model": model_name,
            "grounding": validation_report.model_dump(),
        }

        # 8. Save Assistant Message to SQLite
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

        # 9. Final Done Event
        yield {
            "type": "done",
            "message_id": assistant_msg.id,
            "full_content": full_response,
            "citations": [c.model_dump() for c in validation_report.citations],
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
    ) -> Message:
        """Non-streaming fallback method."""
        full_text = ""
        last_event: Dict[str, Any] = {}
        async for evt in self.stream_chat(
            session=session,
            conversation_id=conversation_id,
            user_content=user_content,
            mode=mode,
            subject_id=subject_id,
            document_ids=document_ids,
            provider_id=provider_id,
        ):
            if evt["type"] == "token":
                full_text += evt["content"]
            elif evt["type"] == "done":
                last_event = evt

        msg_id = last_event.get("message_id")
        stmt = select(Message).where(Message.id == msg_id)
        return (await session.execute(stmt)).scalars().first()


chat_engine = ChatEngine()
