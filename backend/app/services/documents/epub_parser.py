import zipfile
from pathlib import Path
from typing import List
from bs4 import BeautifulSoup
from app.services.documents.base import BaseDocumentParser, ParsedDocument, ParsedChunk


class EpubParser(BaseDocumentParser):
    """Parser for EPUB digital books extracting spine chapters, headings, and paragraphs."""

    def supported_extensions(self) -> List[str]:
        return [".epub"]

    async def parse(self, file_path: Path) -> ParsedDocument:
        title = file_path.stem.replace("_", " ").title()
        chunks: List[ParsedChunk] = []

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # Find OPF package file
                container_xml = zf.read("META-INF/container.xml").decode("utf-8", errors="ignore")
                container_soup = BeautifulSoup(container_xml, "xml")
                rootfile = container_soup.find("rootfile")
                opf_path = rootfile.get("full-path", "OEBPS/content.opf") if rootfile else "OEBPS/content.opf"

                opf_dir = str(Path(opf_path).parent)
                if opf_dir == ".":
                    opf_dir = ""

                # Read OPF metadata & spine
                opf_content = zf.read(opf_path).decode("utf-8", errors="ignore")
                opf_soup = BeautifulSoup(opf_content, "xml")

                # Extract book title
                dc_title = opf_soup.find("dc:title")
                if dc_title and dc_title.string:
                    title = dc_title.string.strip()

                # Build manifest map id -> href
                manifest = {}
                for item in opf_soup.find_all("item"):
                    manifest[item.get("id")] = item.get("href")

                # Read chapters in spine order
                spine = opf_soup.find("spine")
                itemrefs = spine.find_all("itemref") if spine else []

                chapter_idx = 1
                for ref in itemrefs:
                    idref = ref.get("idref")
                    href = manifest.get(idref)
                    if not href:
                        continue

                    full_href = f"{opf_dir}/{href}".lstrip("/") if opf_dir else href
                    if full_href not in zf.namelist():
                        continue

                    chapter_html = zf.read(full_href).decode("utf-8", errors="ignore")
                    ch_soup = BeautifulSoup(chapter_html, "html.parser")

                    # Remove script/style
                    for el in ch_soup(["script", "style"]):
                        el.decompose()

                    h = ch_soup.find(["h1", "h2", "h3"])
                    chapter_heading = h.get_text().strip() if h else f"Chapter {chapter_idx}"

                    text_blocks = []
                    for p in ch_soup.find_all(["p", "blockquote", "li"]):
                        txt = p.get_text().strip()
                        if txt:
                            text_blocks.append(txt)

                    if text_blocks:
                        combined = "\n\n".join(text_blocks)
                        chunks.append(
                            ParsedChunk(
                                content=combined,
                                page_number=chapter_idx,
                                section_heading=chapter_heading,
                                element_type="text",
                            )
                        )
                        chapter_idx += 1

        except Exception as e:
            chunks.append(
                ParsedChunk(
                    content=f"[EPUB parsing failed: {str(e)}]",
                    section_heading="Error",
                    element_type="text",
                )
            )

        for i, c in enumerate(chunks):
            c.chunk_index = i
            c.token_count = max(1, len(c.content.split()))

        return ParsedDocument(
            title=title,
            file_type="epub",
            total_pages=len(chunks),
            chunks=chunks,
            metadata={"byte_size": file_path.stat().st_size},
        )
