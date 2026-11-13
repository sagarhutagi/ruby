from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field


class ParsedChunk(BaseModel):
    """Atomic unit of parsed document content with exact provenance tracking."""
    content: str = Field(..., description="Extracted textual content")
    chunk_index: int = Field(default=0, description="Sequential index within document")
    page_number: Optional[int] = Field(default=None, description="1-indexed page number for PDFs/books")
    slide_number: Optional[int] = Field(default=None, description="1-indexed slide number for PPTX")
    sheet_name: Optional[str] = Field(default=None, description="Sheet name for spreadsheets")
    cell_range: Optional[str] = Field(default=None, description="Cell coordinates e.g. A1:D20")
    section_heading: Optional[str] = Field(default=None, description="Nearest section heading")
    element_type: str = Field(default="text", description="'text', 'table', 'code', 'image_ocr'")
    token_count: int = Field(default=0, description="Estimated token count")
    meta_info: Dict[str, Any] = Field(default_factory=dict, description="Format-specific metadata")


class ParsedDocument(BaseModel):
    """Complete parsed document with structure and chunks."""
    title: str
    file_type: str
    total_pages: Optional[int] = None
    chunks: List[ParsedChunk] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    has_ocr: bool = False


class BaseDocumentParser(ABC):
    """Base interface for all format-specific document parsers."""

    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """List of file extensions this parser supports (e.g. ['.pdf'])."""
        pass

    @abstractmethod
    async def parse(self, file_path: Path) -> ParsedDocument:
        """Parse document from disk and return structured ParsedDocument."""
        pass
