import os
import hashlib
import asyncio
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.core.config import settings
from app.database.session import get_db
from app.models.entities import Document, DocumentChunk, IngestionJob
from app.database.fts import delete_document_fts
from app.services.retrieval.chroma_store import chroma_store
from app.workers.ingestion import process_ingestion_job
from app.services.documents.registry import DocumentParserRegistry

parser_registry = DocumentParserRegistry()
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    ChunkResponse,
    IngestionJobResponse,
)

router = APIRouter(prefix="/documents", tags=["Document Ingestion & Library"])


def _to_doc_response(doc: Document, chunk_count: int = 0) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size_bytes=doc.file_size_bytes,
        file_hash=doc.file_hash,
        page_count=doc.page_count,
        status=doc.status,
        error_message=doc.error_message,
        subject_id=doc.subject_id,
        collection_id=doc.collection_id,
        chunk_count=chunk_count,
        meta_info=doc.meta_info,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post("/upload", response_model=List[DocumentUploadResponse], status_code=status.HTTP_201_CREATED, summary="Upload Documents")
async def upload_documents(
    files: List[UploadFile] = File(...),
    subject_id: Optional[str] = Form(None),
    collection_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    upload_responses: List[DocumentUploadResponse] = []
    settings.ensure_directories()

    for file in files:
        content = await file.read()
        file_size = len(content)
        file_hash = hashlib.sha256(content).hexdigest()
        ext = Path(file.filename or "unknown.txt").suffix.lower()

        # Validate supported file type to prevent unauthorized executable/script uploads
        if ext not in parser_registry.get_supported_extensions():
            upload_responses.append(
                DocumentUploadResponse(
                    document_id="unsupported",
                    job_id="rejected",
                    title=file.filename or "unknown",
                    filename=file.filename or "unknown",
                    file_type=ext.lstrip(".") or "unknown",
                    file_size_bytes=file_size,
                    status="failed",
                    is_duplicate=False,
                    message=f"Unsupported or restricted file format '{ext}'. Allowed extensions: {', '.join(parser_registry.get_supported_extensions())}",
                )
            )
            continue

        # Check for duplicate document
        existing = await db.scalar(select(Document).where(Document.file_hash == file_hash))
        if existing:
            # Document with this exact SHA-256 already exists
            job = await db.scalar(select(IngestionJob).where(IngestionJob.document_id == existing.id))
            job_id = job.id if job else "completed"
            upload_responses.append(
                DocumentUploadResponse(
                    document_id=existing.id,
                    job_id=job_id,
                    title=existing.title,
                    filename=existing.filename,
                    file_type=existing.file_type,
                    file_size_bytes=existing.file_size_bytes,
                    status=existing.status,
                    is_duplicate=True,
                    message="Document already ingested (SHA-256 duplicate matched).",
                )
            )
            continue

        # Save to storage directory
        stored_filename = f"{file_hash}{ext}"
        destination = settings.documents_dir / stored_filename
        destination.write_bytes(content)

        clean_title = Path(file.filename or "Document").stem.replace("_", " ").title()
        doc = Document(
            title=clean_title,
            filename=file.filename or "unnamed",
            file_path=str(destination.resolve()),
            file_hash=file_hash,
            file_type=ext.lstrip("."),
            file_size_bytes=file_size,
            status="pending",
            subject_id=subject_id,
            collection_id=collection_id,
        )
        db.add(doc)
        await db.flush()

        # Create persistent ingestion job
        job = IngestionJob(
            document_id=doc.id,
            status="queued",
            stage="init",
            progress_percentage=0,
        )
        db.add(job)
        await db.commit()

        # Trigger background processing
        asyncio.create_task(process_ingestion_job(job.id))

        upload_responses.append(
            DocumentUploadResponse(
                document_id=doc.id,
                job_id=job.id,
                title=doc.title,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size_bytes=doc.file_size_bytes,
                status=doc.status,
                is_duplicate=False,
            )
        )

    return upload_responses


@router.get("", response_model=List[DocumentResponse], summary="List Documents with Filters")
async def list_documents(
    q: Optional[str] = Query(None, description="Search keyword in filename or title"),
    subject_id: Optional[str] = Query(None, description="Filter by subject"),
    collection_id: Optional[str] = Query(None, description="Filter by collection"),
    status: Optional[str] = Query(None, description="Filter by status (pending, parsing, indexed, failed)"),
    file_type: Optional[str] = Query(None, description="Filter by extension (pdf, docx, etc.)"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document)
    if q:
        stmt = stmt.where(or_(Document.title.ilike(f"%{q}%"), Document.filename.ilike(f"%{q}%")))
    if subject_id:
        stmt = stmt.where(Document.subject_id == subject_id)
    if collection_id:
        stmt = stmt.where(Document.collection_id == collection_id)
    if status:
        stmt = stmt.where(Document.status == status)
    if file_type:
        stmt = stmt.where(Document.file_type == file_type.lower().lstrip("."))

    stmt = stmt.order_by(Document.created_at.desc())
    docs = (await db.execute(stmt)).scalars().all()

    responses = []
    for d in docs:
        c_count = await db.scalar(select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == d.id)) or 0
        responses.append(_to_doc_response(d, c_count))
    return responses


@router.get("/{document_id}", response_model=DocumentResponse, summary="Get Document Details")
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.scalar(select(Document).where(Document.id == document_id))
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    c_count = await db.scalar(select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc.id)) or 0
    return _to_doc_response(doc, c_count)


@router.get("/{document_id}/chunks", response_model=List[ChunkResponse], summary="Get Document Chunks with Provenance")
async def get_document_chunks(
    document_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.scalar(select(Document).where(Document.id == document_id))
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .limit(limit)
        .offset(offset)
    )
    chunks = (await db.execute(stmt)).scalars().all()

    return [
        ChunkResponse(
            id=c.id,
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            content=c.content,
            token_count=c.token_count,
            page_number=c.page_number,
            slide_number=c.slide_number,
            sheet_name=c.sheet_name,
            cell_range=c.cell_range,
            section_heading=c.section_heading,
            meta_info=c.meta_info,
        )
        for c in chunks
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Document")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.scalar(select(Document).where(Document.id == document_id))
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Remove FTS5 keyword index entries & ChromaDB vector index entries
    await delete_document_fts(db, document_id)
    chroma_store.delete_by_document(document_id)

    # Delete physical file
    try:
        p = Path(doc.file_path)
        if p.exists():
            p.unlink()
    except Exception:
        pass

    await db.delete(doc)
    await db.commit()
    return None


@router.post("/{document_id}/reindex", summary="Re-index Document")
async def reindex_document(document_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.scalar(select(Document).where(Document.id == document_id))
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Clear existing chunks and FTS5 entries
    await delete_document_fts(db, document_id)
    del_chunks = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    chunks = (await db.execute(del_chunks)).scalars().all()
    for c in chunks:
        await db.delete(c)

    job = IngestionJob(
        document_id=doc.id,
        status="queued",
        stage="init",
        progress_percentage=0,
    )
    db.add(job)
    doc.status = "pending"
    await db.commit()

    asyncio.create_task(process_ingestion_job(job.id))
    return {"message": "Document queued for re-indexing", "job_id": job.id}


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse, summary="Poll Ingestion Job Status")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.scalar(select(IngestionJob).where(IngestionJob.id == job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return IngestionJobResponse(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        stage=job.stage,
        progress_percentage=job.progress_percentage,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("/jobs/{job_id}/cancel", summary="Cancel Ingestion Job")
async def cancel_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.scalar(select(IngestionJob).where(IngestionJob.id == job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    job.status = "cancelled"
    job.stage = "cancelled"
    await db.commit()
    return {"message": "Job marked as cancelled", "job_id": job.id}
