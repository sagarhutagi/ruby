import logging
from pathlib import Path
from typing import Dict, Optional, List
from app.services.documents.base import BaseDocumentParser, ParsedDocument
from app.services.documents.pdf_parser import PdfParser
from app.services.documents.docx_parser import DocxParser
from app.services.documents.pptx_parser import PptxParser
from app.services.documents.tabular_parser import TabularParser
from app.services.documents.markup_parser import MarkupParser
from app.services.documents.epub_parser import EpubParser
from app.services.documents.image_parser import ImageOcrParser
from app.services.documents.legacy_converter import legacy_converter
from app.core.config import settings

logger = logging.getLogger("ruby.parser.registry")


class DocumentParserRegistry:
    """Central registry and dispatcher for all file parsers."""

    def __init__(self):
        self._parsers: List[BaseDocumentParser] = [
            PdfParser(),
            DocxParser(),
            PptxParser(),
            TabularParser(),
            MarkupParser(),
            EpubParser(),
            ImageOcrParser(),
        ]
        self._extension_map: Dict[str, BaseDocumentParser] = {}
        for parser in self._parsers:
            for ext in parser.supported_extensions():
                self._extension_map[ext.lower()] = parser

    def get_supported_extensions(self) -> List[str]:
        supported = list(self._extension_map.keys())
        if legacy_converter.is_available():
            supported.extend([".doc", ".ppt"])
        return sorted(supported)

    def get_parser(self, extension: str) -> Optional[BaseDocumentParser]:
        return self._extension_map.get(extension.lower())

    async def parse_file(self, file_path: Path) -> ParsedDocument:
        ext = file_path.suffix.lower()

        # Handle legacy formats via LibreOffice conversion
        if ext in [".doc", ".ppt"]:
            if not legacy_converter.is_available():
                raise ValueError(f"Legacy format '{ext}' requires LibreOffice on host, which was not found.")
            converted_dir = settings.cache_dir / "converted"
            converted_pdf = await legacy_converter.convert_to_pdf(file_path, converted_dir)
            if not converted_pdf or not converted_pdf.exists():
                raise RuntimeError(f"Failed to convert legacy format '{ext}' to PDF.")
            parser = self.get_parser(".pdf")
            return await parser.parse(converted_pdf)

        parser = self.get_parser(ext)
        if not parser:
            supported = ", ".join(self.get_supported_extensions())
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: {supported}")

        return await parser.parse(file_path)


parser_registry = DocumentParserRegistry()
