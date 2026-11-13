import csv
from pathlib import Path
from typing import List
import openpyxl
from app.services.documents.base import BaseDocumentParser, ParsedDocument, ParsedChunk


class TabularParser(BaseDocumentParser):
    """Parser for Excel (.xlsx) and CSV spreadsheets preserving sheet names and cell ranges."""

    def supported_extensions(self) -> List[str]:
        return [".xlsx", ".csv"]

    async def parse(self, file_path: Path) -> ParsedDocument:
        ext = file_path.suffix.lower()
        title = file_path.stem.replace("_", " ").title()

        chunks: List[ParsedChunk] = []

        if ext == ".csv":
            chunks = self._parse_csv(file_path)
        elif ext == ".xlsx":
            chunks = self._parse_xlsx(file_path)

        for i, c in enumerate(chunks):
            c.chunk_index = i
            c.token_count = max(1, len(c.content.split()))

        return ParsedDocument(
            title=title,
            file_type=ext.lstrip("."),
            total_pages=len(chunks),
            chunks=chunks,
            metadata={"byte_size": file_path.stat().st_size},
        )

    def _parse_csv(self, file_path: Path) -> List[ParsedChunk]:
        rows = []
        with open(file_path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for row in reader:
                if any(cell.strip() for cell in row):
                    rows.append(row)

        if not rows:
            return []

        # Split into blocks of up to 50 rows to avoid gigantic chunks
        chunks = []
        header = rows[0]
        col_count = len(header)
        data_rows = rows[1:]

        batch_size = 50
        for i in range(0, max(1, len(data_rows)), batch_size):
            slice_rows = data_rows[i : i + batch_size]
            start_row = i + 2
            end_row = i + 1 + len(slice_rows)

            table_lines = ["| " + " | ".join(header) + " |"]
            table_lines.append("| " + " | ".join(["---"] * col_count) + " |")
            for r in slice_rows:
                # Pad row to match header
                padded = r + [""] * (col_count - len(r))
                table_lines.append("| " + " | ".join(padded[:col_count]) + " |")

            table_content = "\n".join(table_lines)
            cell_range = f"A1:{chr(64 + min(26, col_count))}{end_row}"
            chunks.append(
                ParsedChunk(
                    content=table_content,
                    sheet_name="Default",
                    cell_range=cell_range,
                    section_heading=f"Rows {start_row} - {end_row}",
                    element_type="table",
                )
            )

        return chunks

    def _parse_xlsx(self, file_path: Path) -> List[ParsedChunk]:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        chunks = []

        for sheet in wb.worksheets:
            sheet_rows = list(sheet.iter_rows(values_only=True))
            # Filter empty rows
            cleaned_rows = [
                [str(c) if c is not None else "" for c in row]
                for row in sheet_rows
                if any(c is not None and str(c).strip() for c in row)
            ]
            if not cleaned_rows:
                continue

            header = cleaned_rows[0]
            col_count = len(header)
            data_rows = cleaned_rows[1:]

            batch_size = 50
            if not data_rows:
                # Single header row only
                table_md = "| " + " | ".join(header) + " |\n| " + " | ".join(["---"] * col_count) + " |"
                chunks.append(
                    ParsedChunk(
                        content=table_md,
                        sheet_name=sheet.title,
                        cell_range=f"A1:{chr(64 + min(26, col_count))}1",
                        section_heading=f"Sheet: {sheet.title}",
                        element_type="table",
                    )
                )
                continue

            for i in range(0, len(data_rows), batch_size):
                slice_rows = data_rows[i : i + batch_size]
                start_row = i + 2
                end_row = i + 1 + len(slice_rows)

                table_lines = ["| " + " | ".join(header) + " |"]
                table_lines.append("| " + " | ".join(["---"] * col_count) + " |")
                for r in slice_rows:
                    padded = r + [""] * (col_count - len(r))
                    table_lines.append("| " + " | ".join(padded[:col_count]) + " |")

                table_content = "\n".join(table_lines)
                cell_range = f"A{start_row}:{chr(64 + min(26, col_count))}{end_row}"
                chunks.append(
                    ParsedChunk(
                        content=table_content,
                        sheet_name=sheet.title,
                        cell_range=cell_range,
                        section_heading=f"Sheet: {sheet.title} (Rows {start_row}-{end_row})",
                        element_type="table",
                    )
                )

        wb.close()
        return chunks
