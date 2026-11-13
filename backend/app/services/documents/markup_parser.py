import json
import re
from pathlib import Path
from typing import List
from bs4 import BeautifulSoup
from app.services.documents.base import BaseDocumentParser, ParsedDocument, ParsedChunk


class MarkupParser(BaseDocumentParser):
    """Parser for Markdown, TXT, HTML, JSON, and XML documents."""

    def supported_extensions(self) -> List[str]:
        return [".txt", ".md", ".markdown", ".html", ".htm", ".json", ".xml"]

    async def parse(self, file_path: Path) -> ParsedDocument:
        ext = file_path.suffix.lower()
        title = file_path.stem.replace("_", " ").title()
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")

        chunks: List[ParsedChunk] = []

        if ext in [".md", ".markdown"]:
            chunks = self._parse_markdown(raw_text)
        elif ext in [".html", ".htm"]:
            chunks, extracted_title = self._parse_html(raw_text)
            if extracted_title:
                title = extracted_title
        elif ext == ".json":
            chunks = self._parse_json(raw_text)
        elif ext == ".xml":
            chunks = self._parse_xml(raw_text)
        else:  # .txt
            chunks = self._parse_txt(raw_text)

        # Set sequential indices
        for i, c in enumerate(chunks):
            c.chunk_index = i
            c.token_count = max(1, len(c.content.split()))

        return ParsedDocument(
            title=title,
            file_type=ext.lstrip("."),
            total_pages=1,
            chunks=chunks,
            metadata={"byte_size": file_path.stat().st_size},
        )

    def _parse_markdown(self, text: str) -> List[ParsedChunk]:
        chunks = []
        lines = text.split("\n")
        current_heading = "Introduction"
        current_block = []

        for line in lines:
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading_match:
                if current_block:
                    block_content = "\n".join(current_block).strip()
                    if block_content:
                        chunks.append(
                            ParsedChunk(
                                content=block_content,
                                section_heading=current_heading,
                                element_type="text",
                            )
                        )
                    current_block = []
                current_heading = heading_match.group(2).strip()
                current_block.append(line)
            else:
                current_block.append(line)

        if current_block:
            block_content = "\n".join(current_block).strip()
            if block_content:
                chunks.append(
                    ParsedChunk(
                        content=block_content,
                        section_heading=current_heading,
                        element_type="text",
                    )
                )

        return chunks or [ParsedChunk(content=text.strip(), section_heading=current_heading)]

    def _parse_html(self, html_str: str) -> tuple[List[ParsedChunk], str]:
        soup = BeautifulSoup(html_str, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        # Remove script and style elements
        for script in soup(["script", "style", "noscript"]):
            script.decompose()

        chunks = []
        current_heading = title or "Document"

        for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "table", "pre", "ul", "ol"]):
            tag = element.name.lower()
            if tag in ["h1", "h2", "h3", "h4"]:
                current_heading = element.get_text().strip()
            elif tag == "table":
                # Convert HTML table to Markdown table
                rows = []
                for tr in element.find_all("tr"):
                    cells = [td.get_text().strip().replace("\n", " ") for td in tr.find_all(["td", "th"])]
                    if cells:
                        rows.append("| " + " | ".join(cells) + " |")
                if rows:
                    if len(rows) > 1:
                        col_count = len(rows[0].split("|")) - 2
                        separator = "| " + " | ".join(["---"] * col_count) + " |"
                        table_md = rows[0] + "\n" + separator + "\n" + "\n".join(rows[1:])
                    else:
                        table_md = "\n".join(rows)
                    chunks.append(
                        ParsedChunk(
                            content=table_md,
                            section_heading=current_heading,
                            element_type="table",
                        )
                    )
            else:
                txt = element.get_text().strip()
                if txt:
                    chunks.append(
                        ParsedChunk(
                            content=txt,
                            section_heading=current_heading,
                            element_type="code" if tag == "pre" else "text",
                        )
                    )

        if not chunks:
            raw = soup.get_text(separator="\n", strip=True)
            chunks.append(ParsedChunk(content=raw, section_heading=current_heading))

        return chunks, title

    def _parse_json(self, json_str: str) -> List[ParsedChunk]:
        try:
            data = json.loads(json_str)
            pretty = json.dumps(data, indent=2)
            return [ParsedChunk(content=pretty, section_heading="JSON Root", element_type="code")]
        except Exception:
            return [ParsedChunk(content=json_str, section_heading="Raw JSON", element_type="text")]

    def _parse_xml(self, xml_str: str) -> List[ParsedChunk]:
        soup = BeautifulSoup(xml_str, "xml")
        text = soup.get_text(separator="\n", strip=True)
        return [ParsedChunk(content=text, section_heading="XML Content", element_type="text")]

    def _parse_txt(self, text: str) -> List[ParsedChunk]:
        paragraphs = text.split("\n\n")
        chunks = []
        for p in paragraphs:
            cleaned = p.strip()
            if cleaned:
                chunks.append(ParsedChunk(content=cleaned, section_heading="General", element_type="text"))
        return chunks or [ParsedChunk(content=text.strip(), section_heading="General")]
