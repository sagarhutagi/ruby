from pathlib import Path
from typing import List
from docx import Document
from app.services.documents.base import BaseDocumentParser, ParsedDocument, ParsedChunk


class DocxParser(BaseDocumentParser):
    """Parser for Microsoft Word (.docx) documents with heading and table structure preservation."""

    def supported_extensions(self) -> List[str]:
        return [".docx"]

    async def parse(self, file_path: Path) -> ParsedDocument:
        doc = Document(file_path)
        title = doc.core_properties.title or file_path.stem.replace("_", " ").title()

        chunks: List[ParsedChunk] = []
        current_heading = "Overview"
        current_text_block: List[str] = []

        # Iterate through block elements in the document
        for block in doc.iter_inner_content():
            # Paragraph
            if hasattr(block, "text") and hasattr(block, "style"):
                style_name = block.style.name.lower() if block.style else ""
                text = block.text.strip()
                if not text:
                    continue

                if "heading" in style_name or "title" in style_name:
                    if current_text_block:
                        chunks.append(
                            ParsedChunk(
                                content="\n".join(current_text_block),
                                section_heading=current_heading,
                                element_type="text",
                            )
                        )
                        current_text_block = []
                    current_heading = text
                else:
                    current_text_block.append(text)

            # Table
            elif hasattr(block, "rows"):
                if current_text_block:
                    chunks.append(
                        ParsedChunk(
                            content="\n".join(current_text_block),
                            section_heading=current_heading,
                            element_type="text",
                        )
                    )
                    current_text_block = []

                # Format table as Markdown
                table_rows = []
                for row in block.rows:
                    cell_texts = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    table_rows.append("| " + " | ".join(cell_texts) + " |")

                if table_rows:
                    col_count = len(block.columns)
                    sep = "| " + " | ".join(["---"] * col_count) + " |"
                    table_md = table_rows[0] + "\n" + sep + "\n" + "\n".join(table_rows[1:])
                    chunks.append(
                        ParsedChunk(
                            content=table_md,
                            section_heading=current_heading,
                            element_type="table",
                        )
                    )

        if current_text_block:
            chunks.append(
                ParsedChunk(
                    content="\n".join(current_text_block),
                    section_heading=current_heading,
                    element_type="text",
                )
            )

        for i, c in enumerate(chunks):
            c.chunk_index = i
            c.token_count = max(1, len(c.content.split()))

        return ParsedDocument(
            title=title,
            file_type="docx",
            total_pages=None,  # Word documents do not have fixed page numbers without rendering
            chunks=chunks,
            metadata={
                "author": doc.core_properties.author or "Unknown",
                "byte_size": file_path.stat().st_size,
            },
        )
