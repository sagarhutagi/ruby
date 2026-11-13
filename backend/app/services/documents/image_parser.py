from pathlib import Path
from typing import List
from PIL import Image
import pytesseract
from app.services.documents.base import BaseDocumentParser, ParsedDocument, ParsedChunk


class ImageOcrParser(BaseDocumentParser):
    """OCR parser for standalone images (PNG, JPG, JPEG, WEBP, TIFF)."""

    def supported_extensions(self) -> List[str]:
        return [".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif"]

    async def parse(self, file_path: Path) -> ParsedDocument:
        title = file_path.stem.replace("_", " ").title()
        ext = file_path.suffix.lower()

        try:
            with Image.open(file_path) as img:
                width, height = img.size
                # Convert palette/RGBA to RGB for tesseract
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                text = pytesseract.image_to_string(img).strip()

                chunk = ParsedChunk(
                    content=text if text else "[No readable text detected in image]",
                    section_heading="Image OCR",
                    element_type="image_ocr",
                    meta_info={
                        "width": width,
                        "height": height,
                        "format": ext.lstrip("."),
                    },
                )
                chunk.chunk_index = 0
                chunk.token_count = max(1, len(chunk.content.split()))

                return ParsedDocument(
                    title=title,
                    file_type=ext.lstrip("."),
                    total_pages=1,
                    chunks=[chunk],
                    metadata={"width": width, "height": height, "byte_size": file_path.stat().st_size},
                    has_ocr=True,
                )
        except Exception as e:
            return ParsedDocument(
                title=title,
                file_type=ext.lstrip("."),
                total_pages=1,
                chunks=[
                    ParsedChunk(
                        content=f"[OCR processing failed: {str(e)}]",
                        section_heading="OCR Error",
                        element_type="image_ocr",
                    )
                ],
                metadata={"error": str(e)},
                has_ocr=True,
            )
