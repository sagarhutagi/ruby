import asyncio
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import async_session_factory
from app.models.entities import Document, DocumentChunk, IngestionJob
from app.database.fts import index_chunk_fts
from app.services.documents.registry import parser_registry
from app.services.retrieval.chunker import StructureAwareChunker
from app.services.retrieval.embeddings import embedding_manager
from app.services.retrieval.chroma_store import chroma_store

logger = logging.getLogger("ruby.workers.ingestion")


async def process_ingestion_job(job_id: str) -> None:
    """Async background worker task to parse, chunk, index in FTS5, and embed into ChromaDB."""
    async with async_session_factory() as session:
        # Load job & document
        job_stmt = select(IngestionJob).where(IngestionJob.id == job_id)
        job = (await session.execute(job_stmt)).scalars().first()
        if not job or job.status == "cancelled":
            return

        doc_stmt = select(Document).where(Document.id == job.document_id)
        document = (await session.execute(doc_stmt)).scalars().first()
        if not document:
            job.status = "failed"
            job.error_message = "Associated document record missing."
            await session.commit()
            return

        try:
            # Stage 1: Parsing
            job.status = "running"
            job.stage = "parsing"
            job.progress_percentage = 20
            document.status = "parsing"
            await session.commit()

            file_path = Path(document.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found on disk at {file_path}")

            # Run CPU parsing in thread pool to not block asyncio event loop
            loop = asyncio.get_running_loop()
            parsed_doc = await loop.run_in_executor(
                None, lambda: asyncio.run(parser_registry.parse_file(file_path))
            )

            # Check if cancelled during parsing
            await session.refresh(job)
            if job.status == "cancelled":
                logger.info("Ingestion job %s cancelled during parsing.", job_id)
                return

            # Stage 2: Structure-aware chunking
            job.stage = "chunking"
            job.progress_percentage = 45
            await session.commit()

            chunker = StructureAwareChunker(max_chunk_chars=1500, overlap_chars=150)
            structured_chunks = chunker.chunk_parsed_document(parsed_doc)

            # Clean any previous chunks or vectors if re-indexing
            chroma_store.delete_by_document(document.id)

            # Stage 3: Database storage & SQLite FTS5 Indexing
            job.stage = "indexing"
            job.progress_percentage = 65
            await session.commit()

            db_chunk_models = []
            chunk_ids = []
            chunk_texts = []
            chunk_metas = []

            for s_chunk in structured_chunks:
                chunk_model = DocumentChunk(
                    document_id=document.id,
                    chunk_index=s_chunk.chunk_index,
                    content=s_chunk.content,
                    token_count=s_chunk.token_count,
                    page_number=s_chunk.page_number,
                    slide_number=s_chunk.slide_number,
                    sheet_name=s_chunk.sheet_name,
                    cell_range=s_chunk.cell_range,
                    section_heading=s_chunk.section_heading,
                    meta_info=s_chunk.meta_info,
                )
                session.add(chunk_model)
                await session.flush()
                db_chunk_models.append(chunk_model)

                # Index in SQLite FTS5
                await index_chunk_fts(
                    session=session,
                    chunk_id=chunk_model.id,
                    document_id=document.id,
                    content=chunk_model.content,
                )

                chunk_ids.append(chunk_model.id)
                chunk_texts.append(chunk_model.content)
                chunk_metas.append({
                    "chunk_id": chunk_model.id,
                    "document_id": document.id,
                    "document_title": parsed_doc.title or document.title,
                    "chunk_index": chunk_model.chunk_index,
                    "page_number": chunk_model.page_number if chunk_model.page_number is not None else -1,
                    "slide_number": chunk_model.slide_number if chunk_model.slide_number is not None else -1,
                    "sheet_name": chunk_model.sheet_name or "",
                    "cell_range": chunk_model.cell_range or "",
                    "section_heading": chunk_model.section_heading or "",
                    "subject_id": document.subject_id or "",
                })

            # Stage 4: Dense Vector Embedding & ChromaDB Upsert
            job.stage = "embedding"
            job.progress_percentage = 85
            await session.commit()

            if chunk_texts:
                embedding_provider = embedding_manager.get_provider()
                embeddings = await embedding_provider.embed_texts(chunk_texts)
                chroma_store.add_chunks(
                    chunk_ids=chunk_ids,
                    documents=chunk_texts,
                    embeddings=embeddings,
                    metadatas=chunk_metas,
                )

            # Stage 5: Completed
            document.status = "indexed"
            document.title = parsed_doc.title or document.title
            document.page_count = parsed_doc.total_pages
            document.meta_info = parsed_doc.metadata

            job.status = "completed"
            job.stage = "done"
            job.progress_percentage = 100
            await session.commit()
            logger.info("Ingestion job %s completed (%d chunks indexed and embedded).", job_id, len(structured_chunks))

        except Exception as e:
            logger.exception("Ingestion failed for job %s: %s", job_id, e)
            await session.rollback()
            async with async_session_factory() as err_session:
                j = (await err_session.execute(select(IngestionJob).where(IngestionJob.id == job_id))).scalars().first()
                d = (await err_session.execute(select(Document).where(Document.id == job.document_id))).scalars().first()
                if j:
                    j.status = "failed"
                    j.error_message = str(e)
                if d:
                    d.status = "failed"
                    d.error_message = str(e)
                await err_session.commit()
