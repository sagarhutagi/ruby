import re
from typing import List, Optional
from pydantic import BaseModel, Field
from app.services.documents.base import ParsedChunk, ParsedDocument


class ChunkResult(BaseModel):
    """A semantic, structure-aware chunk ready for database storage and embedding."""
    chunk_index: int
    content: str
    token_count: int
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    sheet_name: Optional[str] = None
    cell_range: Optional[str] = None
    section_heading: Optional[str] = None
    char_start: int = 0
    char_end: int = 0
    meta_info: dict = Field(default_factory=dict)


class StructureAwareChunker:
    """
    Structure-aware, semantic document chunker.
    
    Principles:
    1. Preserves structural boundaries: Never splits inside fenced code blocks or markdown tables
       unless a single atomic block exceeds max_chunk_chars.
    2. Respects headings: Uses markdown headers (# ## ###) to demarcate sections and preserve
       hierarchical provenance.
    3. Respects paragraph and sentence boundaries for natural linguistic flow.
    4. Configurable chunk size and overlap.
    5. Preserves all format-specific metadata (page number, slide number, sheet/cell).
    """

    def __init__(
        self,
        max_chunk_chars: int = 1500,  # ~300-400 words
        overlap_chars: int = 150,
        min_chunk_chars: int = 50,
    ):
        self.max_chunk_chars = max(max_chunk_chars, 200)
        self.overlap_chars = min(overlap_chars, self.max_chunk_chars // 2)
        self.min_chunk_chars = min_chunk_chars

    def estimate_tokens(self, text: str) -> int:
        """Heuristic token estimation: ~4 chars per token for English/code."""
        return max(1, len(text) // 4)

    def chunk_parsed_document(self, parsed_doc: ParsedDocument) -> List[ChunkResult]:
        """
        Splits all parsed chunks in a ParsedDocument into structure-aware,
        bounded chunks while keeping provenance intact.
        """
        all_results: List[ChunkResult] = []
        global_chunk_idx = 0

        for raw_chunk in parsed_doc.chunks:
            # If the raw chunk already fits within chunk size, keep it directly
            raw_text = raw_chunk.content.strip()
            if not raw_text:
                continue

            if len(raw_text) <= self.max_chunk_chars:
                all_results.append(
                    ChunkResult(
                        chunk_index=global_chunk_idx,
                        content=raw_text,
                        token_count=self.estimate_tokens(raw_text),
                        page_number=raw_chunk.page_number,
                        slide_number=raw_chunk.slide_number,
                        sheet_name=raw_chunk.sheet_name,
                        cell_range=raw_chunk.cell_range,
                        section_heading=raw_chunk.section_heading,
                        char_start=0,
                        char_end=len(raw_text),
                        meta_info=raw_chunk.meta_info,
                    )
                )
                global_chunk_idx += 1
                continue

            # Otherwise, split structure-aware
            sub_chunks = self._split_structured_text(
                raw_text,
                fallback_heading=raw_chunk.section_heading,
            )

            for sub in sub_chunks:
                all_results.append(
                    ChunkResult(
                        chunk_index=global_chunk_idx,
                        content=sub["content"],
                        token_count=self.estimate_tokens(sub["content"]),
                        page_number=raw_chunk.page_number,
                        slide_number=raw_chunk.slide_number,
                        sheet_name=raw_chunk.sheet_name,
                        cell_range=raw_chunk.cell_range,
                        section_heading=sub["section_heading"] or raw_chunk.section_heading,
                        char_start=sub["char_start"],
                        char_end=sub["char_end"],
                        meta_info=raw_chunk.meta_info,
                    )
                )
                global_chunk_idx += 1

        return all_results

    def _split_structured_text(
        self,
        text: str,
        fallback_heading: Optional[str] = None,
    ) -> List[dict]:
        """
        Splits text by identifying atomic blocks (fenced code, markdown tables, paragraphs)
        and combining them up to max_chunk_chars with overlap.
        """
        blocks = self._extract_atomic_blocks(text, fallback_heading)
        chunks: List[dict] = []
        
        current_chunk_blocks: List[str] = []
        current_len = 0
        current_heading = fallback_heading
        chunk_start_offset = 0

        for block in blocks:
            b_text = block["text"]
            b_heading = block["heading"] or current_heading
            b_len = len(b_text)

            # If a single atomic block is gigantic, force-split it by lines
            if b_len > self.max_chunk_chars:
                if current_chunk_blocks:
                    content = "\n\n".join(current_chunk_blocks).strip()
                    chunks.append({
                        "content": content,
                        "section_heading": current_heading,
                        "char_start": chunk_start_offset,
                        "char_end": chunk_start_offset + len(content),
                    })
                    current_chunk_blocks = []
                    current_len = 0

                oversized_slices = self._split_oversized_block(b_text)
                for s in oversized_slices:
                    chunks.append({
                        "content": s,
                        "section_heading": b_heading,
                        "char_start": chunk_start_offset,
                        "char_end": chunk_start_offset + len(s),
                    })
                continue

            # Check if adding this block exceeds max_chunk_chars
            if current_len + b_len + 2 > self.max_chunk_chars and current_chunk_blocks:
                content = "\n\n".join(current_chunk_blocks).strip()
                chunks.append({
                    "content": content,
                    "section_heading": current_heading,
                    "char_start": chunk_start_offset,
                    "char_end": chunk_start_offset + len(content),
                })

                # Carry over overlap if possible
                overlap_text = content[-self.overlap_chars:] if self.overlap_chars > 0 else ""
                current_chunk_blocks = [overlap_text, b_text] if overlap_text else [b_text]
                current_len = len(overlap_text) + b_len
                current_heading = b_heading
            else:
                current_chunk_blocks.append(b_text)
                current_len += b_len + 2
                if block["heading"]:
                    current_heading = block["heading"]

        if current_chunk_blocks:
            content = "\n\n".join(current_chunk_blocks).strip()
            if len(content) >= self.min_chunk_chars or not chunks:
                chunks.append({
                    "content": content,
                    "section_heading": current_heading,
                    "char_start": chunk_start_offset,
                    "char_end": chunk_start_offset + len(content),
                })

        return chunks

    def _extract_atomic_blocks(self, text: str, initial_heading: Optional[str]) -> List[dict]:
        """
        Breaks text into atomic structural units:
        - Fenced code blocks (``` ... ```)
        - Markdown tables
        - Markdown headings (# ...)
        - Standard paragraphs (\n\n)
        """
        lines = text.split("\n")
        blocks: List[dict] = []
        
        in_code_block = False
        code_lines: List[str] = []
        in_table = False
        table_lines: List[str] = []
        paragraph_lines: List[str] = []
        current_heading = initial_heading

        def flush_paragraph():
            nonlocal paragraph_lines
            if paragraph_lines:
                p_text = "\n".join(paragraph_lines).strip()
                if p_text:
                    blocks.append({"text": p_text, "heading": current_heading, "type": "paragraph"})
                paragraph_lines = []

        def flush_table():
            nonlocal table_lines, in_table
            if table_lines:
                t_text = "\n".join(table_lines).strip()
                if t_text:
                    blocks.append({"text": t_text, "heading": current_heading, "type": "table"})
                table_lines = []
            in_table = False

        def flush_code():
            nonlocal code_lines, in_code_block
            if code_lines:
                c_text = "\n".join(code_lines).strip()
                if c_text:
                    blocks.append({"text": c_text, "heading": current_heading, "type": "code"})
                code_lines = []
            in_code_block = False

        for line in lines:
            stripped = line.strip()

            # Check for code fence
            if stripped.startswith("```"):
                if in_code_block:
                    code_lines.append(line)
                    flush_code()
                else:
                    flush_paragraph()
                    flush_table()
                    in_code_block = True
                    code_lines.append(line)
                continue

            if in_code_block:
                code_lines.append(line)
                continue

            # Check for heading
            if re.match(r"^#{1,6}\s+", stripped):
                flush_paragraph()
                flush_table()
                current_heading = re.sub(r"^#{1,6}\s+", "", stripped)
                blocks.append({"text": line, "heading": current_heading, "type": "heading"})
                continue

            # Check for table row
            if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2:
                flush_paragraph()
                in_table = True
                table_lines.append(line)
                continue
            elif in_table:
                flush_table()

            # Normal text / paragraph
            if not stripped:
                flush_paragraph()
            else:
                paragraph_lines.append(line)

        flush_code()
        flush_table()
        flush_paragraph()

        return blocks

    def _split_oversized_block(self, text: str) -> List[str]:
        """Splits an oversized block by sentence or line without exceeding max_chunk_chars."""
        lines = text.split("\n")
        slices: List[str] = []
        current: List[str] = []
        cur_len = 0

        for line in lines:
            if cur_len + len(line) + 1 > self.max_chunk_chars and current:
                slices.append("\n".join(current))
                current = [line]
                cur_len = len(line)
            else:
                current.append(line)
                cur_len += len(line) + 1

        if current:
            slices.append("\n".join(current))

        return slices
