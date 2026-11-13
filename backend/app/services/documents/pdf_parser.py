from pathlib import Path
from typing import List
import io
import pymupdf
from PIL import Image
import pytesseract
from app.services.documents.base import BaseDocumentParser, ParsedDocument, ParsedChunk


class PdfParser(BaseDocumentParser):
    """Parser for PDF documents with structure preservation and automatic scanned page OCR."""

    def supported_extensions(self) -> List[str]:
        return [".pdf"]

    async def parse(self, file_path: Path) -> ParsedDocument:
        doc = pymupdf.open(str(file_path))
        title = doc.metadata.get("title") or file_path.stem.replace("_", " ").title()
        author = doc.metadata.get("author") or "Unknown"
        total_pages = len(doc)

        chunks: List[ParsedChunk] = []
        has_ocr = False

        for page_idx, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()

            # Detect scanned page: if textual character count is suspiciously low
            if len(text) < 40:
                try:
                    # Render page as high-res image for OCR
                    pix = page.get_pixmap(dpi=150)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr_text = pytesseract.image_to_string(img).strip()
                    if ocr_text:
                        text = ocr_text
                        has_ocr = True
                except Exception:
                    pass

            if not text:
                continue

            # Identify potential headings (first line or short capitalized line)
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            heading = f"Page {page_idx}"
            if lines and len(lines[0]) < 80 and (lines[0].isupper() or lines[0].istitle()):
                heading = f"Page {page_idx}: {lines[0]}"

            chunks.append(
                ParsedChunk(
                    content=text,
                    page_number=page_idx,
                    section_heading=heading,
                    element_type="text",
                )
            )

        doc.close()

        for i, c in enumerate(chunks):
            c.chunk_index = i
            c.token_count = max(1, len(c.content.split()))

        return ParsedDocument(
            title=title,
            file_type="pdf",
            total_pages=total_pages,
            chunks=chunks,
            metadata={
                "author": author,
                "page_count": total_pages,
                "byte_size": file_path.stat().st_size,
            },
            has_ocr=has_ocr,
        )
