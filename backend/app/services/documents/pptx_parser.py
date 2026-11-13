from pathlib import Path
from typing import List
from pptx import Presentation
from app.services.documents.base import BaseDocumentParser, ParsedDocument, ParsedChunk


class PptxParser(BaseDocumentParser):
    """Parser for Microsoft PowerPoint (.pptx) presentations preserving slide numbers."""

    def supported_extensions(self) -> List[str]:
        return [".pptx"]

    async def parse(self, file_path: Path) -> ParsedDocument:
        prs = Presentation(file_path)
        title = file_path.stem.replace("_", " ").title()

        chunks: List[ParsedChunk] = []

        for slide_idx, slide in enumerate(prs.slides, start=1):
            slide_title = None
            slide_texts: List[str] = []

            # Check for title shape
            if slide.shapes.title and slide.shapes.title.text.strip():
                slide_title = slide.shapes.title.text.strip()

            heading = slide_title or f"Slide {slide_idx}"

            for shape in slide.shapes:
                # Text Frame
                if shape.has_text_frame:
                    if shape == slide.shapes.title:
                        continue  # already captured as heading
                    for paragraph in shape.text_frame.paragraphs:
                        txt = paragraph.text.strip()
                        if txt:
                            slide_texts.append(txt)

                # Table shape
                elif shape.has_table:
                    table_rows = []
                    for row in shape.table.rows:
                        cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                        table_rows.append("| " + " | ".join(cells) + " |")
                    if table_rows:
                        col_count = len(shape.table.columns)
                        sep = "| " + " | ".join(["---"] * col_count) + " |"
                        table_md = table_rows[0] + "\n" + sep + "\n" + "\n".join(table_rows[1:])
                        chunks.append(
                            ParsedChunk(
                                content=table_md,
                                slide_number=slide_idx,
                                section_heading=heading,
                                element_type="table",
                            )
                        )

            if slide_texts:
                combined_text = "\n".join(slide_texts)
                chunks.append(
                    ParsedChunk(
                        content=combined_text,
                        slide_number=slide_idx,
                        section_heading=heading,
                        element_type="text",
                    )
                )

        for i, c in enumerate(chunks):
            c.chunk_index = i
            c.token_count = max(1, len(c.content.split()))

        return ParsedDocument(
            title=title,
            file_type="pptx",
            total_pages=len(prs.slides),
            chunks=chunks,
            metadata={"slide_count": len(prs.slides), "byte_size": file_path.stat().st_size},
        )
