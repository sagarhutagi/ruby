import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import PlainTextResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.database.session import get_db
from app.models.entities import Conversation, Message, Subject
from app.services.chat.engine import chat_engine

logger = logging.getLogger("ruby.api.chat")

router = APIRouter(prefix="", tags=["chat"])


# Models
class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    subject_id: Optional[str] = None
    system_prompt: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    subject_id: Optional[str] = None
    system_prompt: Optional[str] = None


class MessageItem(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    mode: str
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    citations: Optional[List[dict]] = None
    diagnostics: Optional[dict] = None
    tokens_used: Optional[int] = None
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    title: str
    subject_id: Optional[str] = None
    system_prompt: Optional[str] = None
    created_at: str
    updated_at: str
    messages: List[MessageItem]


class ConversationSummary(BaseModel):
    id: str
    title: str
    subject_id: Optional[str] = None
    system_prompt: Optional[str] = None
    message_count: int
    last_message_preview: Optional[str] = None
    created_at: str
    updated_at: str


class SendMessageRequest(BaseModel):
    conversation_id: str
    content: str = Field(..., min_length=1)
    mode: str = Field(default="resource-grounded", description="resource-grounded, general, hybrid, research")
    subject_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    provider_id: Optional[str] = None


# Endpoints
@router.get("/conversations", response_model=List[ConversationSummary], summary="List Conversations")
async def list_conversations(
    q: Optional[str] = Query(None, description="Search keyword in conversation title"),
    subject_id: Optional[str] = Query(None, description="Filter by subject"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Conversation)
    if q:
        stmt = stmt.where(Conversation.title.ilike(f"%{q}%"))
    if subject_id:
        stmt = stmt.where(Conversation.subject_id == subject_id)
    stmt = stmt.order_by(Conversation.updated_at.desc())
    convs = (await db.execute(stmt)).scalars().all()

    summaries = []
    for c in convs:
        # Get count and last message
        cnt = await db.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id)) or 0
        last_msg = (
            await db.execute(
                select(Message.content)
                .where(Message.conversation_id == c.id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
        ).scalars().first()

        summaries.append(
            ConversationSummary(
                id=c.id,
                title=c.title,
                subject_id=c.subject_id,
                system_prompt=c.system_prompt,
                message_count=cnt,
                last_message_preview=last_msg[:60] if last_msg else None,
                created_at=c.created_at.isoformat(),
                updated_at=c.updated_at.isoformat(),
            )
        )
    return summaries


@router.post("/conversations", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED, summary="Create Conversation")
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    conv = Conversation(
        title=data.title or "New Conversation",
        subject_id=data.subject_id,
        system_prompt=data.system_prompt,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        subject_id=conv.subject_id,
        system_prompt=conv.system_prompt,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        messages=[],
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail, summary="Get Conversation Detail")
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    conv = await db.scalar(select(Conversation).where(Conversation.id == conversation_id))
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    msg_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = (await db.execute(msg_stmt)).scalars().all()

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        subject_id=conv.subject_id,
        system_prompt=conv.system_prompt,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        messages=[
            MessageItem(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                mode=m.mode,
                provider_used=m.provider_used,
                model_used=m.model_used,
                citations=m.citations,
                diagnostics=m.diagnostics,
                tokens_used=m.tokens_used,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationDetail, summary="Update Conversation")
async def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    conv = await db.scalar(select(Conversation).where(Conversation.id == conversation_id))
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    if data.title is not None:
        conv.title = data.title
    if data.subject_id is not None:
        conv.subject_id = data.subject_id if data.subject_id else None
    if data.system_prompt is not None:
        conv.system_prompt = data.system_prompt

    await db.commit()
    await db.refresh(conv)
    return await get_conversation(conversation_id, db)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Conversation")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    conv = await db.scalar(select(Conversation).where(Conversation.id == conversation_id))
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    await db.delete(conv)
    await db.commit()
    return None


@router.get("/conversations/{conversation_id}/export", response_class=PlainTextResponse, summary="Export Conversation Markdown")
async def export_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    conv = await db.scalar(select(Conversation).where(Conversation.id == conversation_id))
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    msg_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = (await db.execute(msg_stmt)).scalars().all()

    lines = [
        f"# Conversation: {conv.title}",
        f"**Date:** {conv.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Conversation ID:** `{conv.id}`",
        "",
        "---",
        "",
    ]

    for m in messages:
        sender = "**User**" if m.role == "user" else f"**Assistant ({m.model_used or 'AI'})**"
        lines.append(f"### {sender} ({m.mode})")
        lines.append(f"*{m.created_at.strftime('%H:%M:%S')}*")
        lines.append("")
        lines.append(m.content)
        lines.append("")

        if m.citations:
            lines.append("**Citations:**")
            for c in m.citations:
                lines.append(f"- {c.get('raw_tag', 'Citation')} (Verified: {c.get('is_verified')})")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


@router.post("/chat/message", response_model=MessageItem, summary="Send Message (Sync Fallback)")
async def send_message_sync(
    req: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    msg = await chat_engine.generate_message_sync(
        session=db,
        conversation_id=req.conversation_id,
        user_content=req.content,
        mode=req.mode,
        subject_id=req.subject_id,
        document_ids=req.document_ids,
        provider_id=req.provider_id,
    )
    return MessageItem(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        mode=msg.mode,
        provider_used=msg.provider_used,
        model_used=msg.model_used,
        citations=msg.citations,
        diagnostics=msg.diagnostics,
        tokens_used=msg.tokens_used,
        created_at=msg.created_at.isoformat(),
    )


@router.post("/chat/stream", summary="Stream Chat Response (SSE)")
async def stream_chat_endpoint(
    req: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events (SSE) streaming endpoint.
    Emits events:
      - event: sources (retrieved document chunks with provenance)
      - event: token (incremental LLM text delta)
      - event: done (final message ID, verified citations, latency diagnostics)
    """
    async def event_generator():
        try:
            async for event_data in chat_engine.stream_chat(
                session=db,
                conversation_id=req.conversation_id,
                user_content=req.content,
                mode=req.mode,
                subject_id=req.subject_id,
                document_ids=req.document_ids,
                provider_id=req.provider_id,
            ):
                evt_type = event_data.get("type", "message")
                yield {
                    "event": evt_type,
                    "data": json.dumps(event_data),
                }
        except Exception as e:
            logger.exception("Error in SSE chat stream: %s", e)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())


@router.post("/chat/regenerate/{conversation_id}", response_model=MessageItem, summary="Regenerate Last Assistant Message")
async def regenerate_message(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    # Find last assistant message and last user message
    msg_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(2)
    )
    latest_messages = (await db.execute(msg_stmt)).scalars().all()

    if not latest_messages:
        raise HTTPException(status_code=400, detail="No messages in conversation to regenerate.")

    last_user_msg: Optional[Message] = None
    if latest_messages[0].role == "assistant":
        # Delete last assistant message
        await db.delete(latest_messages[0])
        await db.commit()
        if len(latest_messages) > 1 and latest_messages[1].role == "user":
            last_user_msg = latest_messages[1]
    elif latest_messages[0].role == "user":
        last_user_msg = latest_messages[0]

    if not last_user_msg:
        raise HTTPException(status_code=400, detail="Cannot find user message to regenerate from.")

    # Re-run generation
    msg = await chat_engine.generate_message_sync(
        session=db,
        conversation_id=conversation_id,
        user_content=last_user_msg.content,
        mode=last_user_msg.mode,
    )

    return MessageItem(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        mode=msg.mode,
        provider_used=msg.provider_used,
        model_used=msg.model_used,
        citations=msg.citations,
        diagnostics=msg.diagnostics,
        tokens_used=msg.tokens_used,
        created_at=msg.created_at.isoformat(),
    )
