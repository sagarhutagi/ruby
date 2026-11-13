import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services.memory.service import memory_service

logger = logging.getLogger("ruby.api.memories")

router = APIRouter(prefix="/memories", tags=["memories"])
memory_alias_router = APIRouter(prefix="/memory", tags=["memories"])


class MemoryCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    memory_type: str = Field(default="semantic", description="working, episodic, semantic, profile, procedural")
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_pinned: bool = False
    source_conversation_id: Optional[str] = None
    source_event: Optional[str] = None


class MemoryUpdateRequest(BaseModel):
    content: Optional[str] = None
    memory_type: Optional[str] = None
    importance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    is_pinned: Optional[bool] = None


class MemoryResponse(BaseModel):
    id: str
    memory_type: str
    content: str
    importance_score: float
    confidence: float
    is_pinned: bool
    status: str
    source_conversation_id: Optional[str] = None
    source_event: Optional[str] = None
    created_at: str
    updated_at: str


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    memory_types: Optional[List[str]] = None
    top_k: int = Field(default=5, ge=1, le=50)


class CandidateExtractionRequest(BaseModel):
    text: str = Field(..., min_length=5)
    conversation_id: Optional[str] = None


class AuditEventResponse(BaseModel):
    id: str
    memory_id: str
    action: str
    details: Optional[dict] = None
    created_at: str


def _to_memory_response(m) -> MemoryResponse:
    return MemoryResponse(
        id=m.id,
        memory_type=m.memory_type,
        content=m.content,
        importance_score=m.importance_score,
        confidence=m.confidence,
        is_pinned=m.is_pinned,
        status=m.status,
        source_conversation_id=m.source_conversation_id,
        source_event=m.source_event,
        created_at=m.created_at.isoformat(),
        updated_at=m.updated_at.isoformat(),
    )


@router.get("", response_model=List[MemoryResponse], summary="List Memories")
async def list_memories(
    memory_type: Optional[str] = Query(None, description="Filter by category (working, episodic, semantic, profile, procedural)"),
    status_filter: str = Query("active", alias="status"),
    is_pinned: Optional[bool] = Query(None),
    q: Optional[str] = Query(None, description="Search keyword in memory content"),
    db: AsyncSession = Depends(get_db),
):
    mems = await memory_service.list_memories(
        session=db,
        memory_type=memory_type,
        status=status_filter,
        is_pinned=is_pinned,
        q=q,
    )
    return [_to_memory_response(m) for m in mems]


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED, summary="Create Memory")
async def create_memory(
    data: MemoryCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    mem = await memory_service.create_memory(
        session=db,
        content=data.content,
        memory_type=data.memory_type,
        importance_score=data.importance_score,
        confidence=data.confidence,
        is_pinned=data.is_pinned,
        source_conversation_id=data.source_conversation_id,
        source_event=data.source_event,
    )
    return _to_memory_response(mem)


@router.get("/audit/trail", response_model=List[AuditEventResponse], summary="Get Memory Audit Trail")
async def get_audit_trail(
    memory_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    audits = await memory_service.get_audit_trail(session=db, memory_id=memory_id)
    return [
        AuditEventResponse(
            id=a.id,
            memory_id=a.memory_id,
            action=a.action,
            details=a.details,
            created_at=a.created_at.isoformat(),
        )
        for a in audits
    ]


@router.post("/search", summary="Semantic Memory Search")
async def search_memories(
    req: MemorySearchRequest,
    db: AsyncSession = Depends(get_db),
):
    results = await memory_service.search_memories(
        session=db,
        query=req.query,
        memory_types=req.memory_types,
        top_k=req.top_k,
    )
    return [
        {
            "memory": _to_memory_response(r["memory"]),
            "similarity": r["similarity"],
            "distance": r["distance"],
        }
        for r in results
    ]


@router.post("/extract-candidates", summary="Extract Memory Candidates from Text")
@router.post("/candidates", summary="Extract Memory Candidates from Text (Alias)")
async def extract_candidates(
    req: CandidateExtractionRequest,
    db: AsyncSession = Depends(get_db),
):
    return await memory_service.extract_candidates(
        session=db,
        text=req.text,
        conversation_id=req.conversation_id,
    )


@router.get("/export", summary="Export Memories")
async def export_memories(db: AsyncSession = Depends(get_db)):
    return await memory_service.export_memories(session=db)


@router.post("/import", summary="Import Memories")
async def import_memories(
    items: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
):
    count = await memory_service.import_memories(session=db, items=items)
    return {"imported_count": count}


@router.patch("/{memory_id}", response_model=MemoryResponse, summary="Update Memory")
async def update_memory(
    memory_id: str,
    data: MemoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        mem = await memory_service.update_memory(
            session=db,
            memory_id=memory_id,
            content=data.content,
            memory_type=data.memory_type,
            importance_score=data.importance_score,
            confidence=data.confidence,
            is_pinned=data.is_pinned,
        )
        return _to_memory_response(mem)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Memory")
async def delete_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
):
    await memory_service.delete_memory(session=db, memory_id=memory_id, hard_delete=True)
    return None


@router.post("/{memory_id}/pin", response_model=MemoryResponse, summary="Toggle Pin Memory")
async def toggle_pin(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        mem = await memory_service.toggle_pin(session=db, memory_id=memory_id)
        return _to_memory_response(mem)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@memory_alias_router.get("", include_in_schema=False)
async def list_memories_alias(db: AsyncSession = Depends(get_db)):
    mems = await memory_service.list_memories(session=db, status="active")
    return [_to_memory_response(m) for m in mems]
