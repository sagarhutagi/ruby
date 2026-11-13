import asyncio
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import async_session_factory
from app.models.entities import Document, DocumentChunk, IngestionJob
from app.database.fts import index_chunk_fts
from app.services.documents.registry import parser_registry

logger = logging.getLogger("ruby.workers.ingestion")


async def process_ingestion_job(job_id: str) -> None:
    """Async background worker task to parse, chunk, and index a document."""
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
            job.progress_percentage = 25
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

            # Stage 2: Storing chunks & FTS5 indexing
            job.stage = "indexing"
            job.progress_percentage = 65
            await session.commit()

            total_chunks = len(parsed_doc.chunks)
            for idx, p_chunk in enumerate(parsed_doc.chunks):
                chunk_model = DocumentChunk(
                    document_id=document.id,
                    chunk_index=idx,
                    content=p_chunk.content,
                    token_count=p_chunk.token_count,
                    page_number=p_chunk.page_number,
                    slide_number=p_chunk.slide_number,
                    sheet_name=p_chunk.sheet_name,
                    cell_range=p_chunk.cell_range,
                    section_heading=p_chunk.section_heading,
                    meta_info=p_chunk.meta_info,
                )
                session.add(chunk_model)
                await session.flush()

                # Index in SQLite FTS5 for hybrid search
                await index_chunk_fts(
                    session=session,
                    chunk_id=chunk_model.id,
                    document_id=document.id,
                    content=chunk_model.content,
                )

            # Stage 3: Completed
            document.status = "indexed"
            document.title = parsed_doc.title or document.title
            document.page_count = parsed_doc.total_pages
            document.meta_info = parsed_doc.metadata

            job.status = "completed"
            job.stage = "done"
            job.progress_percentage = 100
            await session.commit()
            logger.info("Ingestion job %s completed (%d chunks indexed).", job_id, total_chunks)

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
