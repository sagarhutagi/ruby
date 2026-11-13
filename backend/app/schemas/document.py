from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    document_id: str
    job_id: str
    title: str
    filename: str
    file_type: str
    file_size_bytes: int
    status: str
    is_duplicate: bool = False
    message: str = "Document uploaded and queued for processing."


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    sheet_name: Optional[str] = None
    cell_range: Optional[str] = None
    section_heading: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None


class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    file_type: str
    file_size_bytes: int
    file_hash: str
    page_count: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    subject_id: Optional[str] = None
    collection_id: Optional[str] = None
    chunk_count: int = 0
    meta_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class IngestionJobResponse(BaseModel):
    id: str
    document_id: str
    status: str
    stage: str
    progress_percentage: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
