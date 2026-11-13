import json
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.models.entities import ProviderConfig, SecretRef
from app.core.secrets_manager import secrets_manager
from app.services.ai.base import ChatMessage, ModelInfo
from app.services.ai.manager import provider_manager
from app.schemas.provider import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse,
    TestConnectionResponse,
    ChatStreamRequest,
)

logger = logging.getLogger("ruby.api.providers")
router = APIRouter(prefix="/providers", tags=["AI Providers"])


def _to_provider_response(config: ProviderConfig, sec_ref: SecretRef | None = None) -> ProviderResponse:
    return ProviderResponse(
        id=config.id,
        name=config.name,
        provider_type=config.provider_type,
        base_url=config.base_url,
        model_name=config.model_name,
        is_enabled=config.is_enabled,
        is_default=config.is_default,
        timeout_seconds=config.timeout_seconds,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        context_window=config.context_window,
        has_api_key=(sec_ref is not None),
        masked_key=(sec_ref.masked_preview if sec_ref else None),
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get("", response_model=List[ProviderResponse], summary="List AI Providers")
async def list_providers(db: AsyncSession = Depends(get_db)):
    stmt = select(ProviderConfig).order_by(ProviderConfig.is_default.desc(), ProviderConfig.name)
    result = await db.execute(stmt)
    configs = result.scalars().all()

    # Load secret refs to show masked previews
    responses = []
    for c in configs:
        sec_stmt = select(SecretRef).where(SecretRef.provider_id == c.id)
        sec_res = await db.execute(sec_stmt)
        sec = sec_res.scalars().first()
        responses.append(_to_provider_response(c, sec))
    return responses


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED, summary="Create AI Provider")
async def create_provider(payload: ProviderCreate, db: AsyncSession = Depends(get_db)):
    # Check for name uniqueness
    existing_stmt = select(ProviderConfig).where(ProviderConfig.name == payload.name)
    existing = (await db.execute(existing_stmt)).scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider with name '{payload.name}' already exists.",
        )

    # If this is marked as default, unset other defaults
    if payload.is_default:
        all_configs = (await db.execute(select(ProviderConfig))).scalars().all()
        for conf in all_configs:
            conf.is_default = False

    config = ProviderConfig(
        name=payload.name,
        provider_type=payload.provider_type,
        base_url=payload.base_url,
        model_name=payload.model_name,
        is_enabled=payload.is_enabled,
        is_default=payload.is_default,
        timeout_seconds=payload.timeout_seconds,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        context_window=payload.context_window,
        custom_headers=payload.custom_headers,
        extra_params=payload.extra_params,
    )
    db.add(config)
    await db.flush()

    sec_ref = None
    if payload.api_key:
        key_name = f"provider_{config.id}_key"
        backend_used = secrets_manager.store_secret(key_name, payload.api_key)
        sec_ref = SecretRef(
            provider_id=config.id,
            key_name=key_name,
            backend_type=backend_used,
            masked_preview=secrets_manager.mask_secret(payload.api_key),
        )
        db.add(sec_ref)

    await db.commit()
    await db.refresh(config)
    return _to_provider_response(config, sec_ref)


@router.get("/{provider_id}", response_model=ProviderResponse, summary="Get AI Provider")
async def get_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ProviderConfig).where(ProviderConfig.id == provider_id)
    config = (await db.execute(stmt)).scalars().first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")

    sec_stmt = select(SecretRef).where(SecretRef.provider_id == provider_id)
    sec_ref = (await db.execute(sec_stmt)).scalars().first()
    return _to_provider_response(config, sec_ref)


@router.put("/{provider_id}", response_model=ProviderResponse, summary="Update AI Provider")
async def update_provider(provider_id: str, payload: ProviderUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(ProviderConfig).where(ProviderConfig.id == provider_id)
    config = (await db.execute(stmt)).scalars().first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")

    update_data = payload.model_dump(exclude_unset=True)
    api_key_update = update_data.pop("api_key", None)

    if update_data.get("is_default"):
        all_configs = (await db.execute(select(ProviderConfig))).scalars().all()
        for conf in all_configs:
            if conf.id != provider_id:
                conf.is_default = False

    for field, val in update_data.items():
        setattr(config, field, val)

    sec_stmt = select(SecretRef).where(SecretRef.provider_id == provider_id)
    sec_ref = (await db.execute(sec_stmt)).scalars().first()

    if api_key_update is not None:
        if api_key_update == "":
            # Delete secret
            if sec_ref:
                secrets_manager.delete_secret(sec_ref.key_name)
                await db.delete(sec_ref)
                sec_ref = None
        else:
            # Store or update secret
            key_name = f"provider_{provider_id}_key"
            backend_used = secrets_manager.store_secret(key_name, api_key_update)
            if sec_ref:
                sec_ref.masked_preview = secrets_manager.mask_secret(api_key_update)
                sec_ref.backend_type = backend_used
            else:
                sec_ref = SecretRef(
                    provider_id=provider_id,
                    key_name=key_name,
                    backend_type=backend_used,
                    masked_preview=secrets_manager.mask_secret(api_key_update),
                )
                db.add(sec_ref)

    await db.commit()
    await db.refresh(config)
    return _to_provider_response(config, sec_ref)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete AI Provider")
async def delete_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ProviderConfig).where(ProviderConfig.id == provider_id)
    config = (await db.execute(stmt)).scalars().first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")

    # Remove associated secrets
    sec_stmt = select(SecretRef).where(SecretRef.provider_id == provider_id)
    sec_ref = (await db.execute(sec_stmt)).scalars().first()
    if sec_ref:
        secrets_manager.delete_secret(sec_ref.key_name)

    await db.delete(config)
    await db.commit()
    return None


@router.post("/{provider_id}/test", response_model=TestConnectionResponse, summary="Test Provider Connection")
async def test_provider_connection(provider_id: str, db: AsyncSession = Depends(get_db)):
    try:
        adapter = await provider_manager.get_provider_instance(db, provider_id)
        result = await adapter.test_connection()
        return TestConnectionResponse(**result)
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            latency_ms=0.0,
            message=f"Test failed: {str(e)}",
        )


@router.get("/{provider_id}/models", response_model=List[ModelInfo], summary="Discover Models for Provider")
async def discover_provider_models(provider_id: str, db: AsyncSession = Depends(get_db)):
    try:
        adapter = await provider_manager.get_provider_instance(db, provider_id)
        models = await adapter.list_models()
        return models
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to discover models from provider: {str(e)}",
        )


@router.post("/chat/stream", summary="Streaming Chat Probe via SSE")
async def stream_chat_probe(request: ChatStreamRequest, db: AsyncSession = Depends(get_db)):
    """SSE streaming endpoint for real-time model interaction."""
    if request.provider_id:
        adapter = await provider_manager.get_provider_instance(db, request.provider_id)
    else:
        adapter = await provider_manager.get_default_provider(db)

    messages = []
    if request.system_prompt:
        messages.append(ChatMessage(role="system", content=request.system_prompt))
    messages.append(ChatMessage(role="user", content=request.prompt))

    async def event_generator():
        try:
            async for chunk in adapter.stream_chat(
                messages,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                payload = json.dumps({
                    "delta": chunk.content_delta,
                    "is_done": chunk.is_done,
                    "finish_reason": chunk.finish_reason,
                    "tokens_used": chunk.tokens_used,
                })
                yield f"data: {payload}\n\n"
        except Exception as e:
            err_payload = json.dumps({"error": str(e), "is_done": True})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
