import pytest
from pathlib import Path
import pymupdf
from docx import Document as DocxDocument
from pptx import Presentation
from pptx.util import Inches
import openpyxl
from PIL import Image, ImageDraw
import pytesseract
from app.services.documents.pdf_parser import PdfParser
from app.services.documents.docx_parser import DocxParser
from app.services.documents.pptx_parser import PptxParser
from app.services.documents.tabular_parser import TabularParser
from app.services.documents.image_parser import ImageOcrParser


@pytest.mark.asyncio
async def test_pdf_parser_with_pymupdf(tmp_path: Path):
    pdf_path = tmp_path / "test_math.pdf"
    doc = pymupdf.open()
    page1 = doc.new_page()
    page1.insert_text((50, 72), "Mathematics for Computer Science\nCalculus and Linear Algebra.")
    page2 = doc.new_page()
    page2.insert_text((50, 72), "Eigenvalues and Eigenvectors: Det(A - lambda*I) = 0.")
    doc.save(str(pdf_path))
    doc.close()

    parser = PdfParser()
    parsed = await parser.parse(pdf_path)
    assert parsed.file_type == "pdf"
    assert parsed.total_pages == 2
    assert len(parsed.chunks) == 2
    assert parsed.chunks[0].page_number == 1
    assert "Linear Algebra" in parsed.chunks[0].content
    assert parsed.chunks[1].page_number == 2
    assert "Eigenvalues" in parsed.chunks[1].content


@pytest.mark.asyncio
async def test_docx_parser(tmp_path: Path):
    docx_path = tmp_path / "test_os.docx"
    doc = DocxDocument()
    doc.add_heading("Operating Systems Scheduling", level=1)
    doc.add_paragraph("Round Robin and Shortest Job First are CPU scheduling algorithms.")
    doc.add_heading("Comparison Table", level=2)
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Algorithm"
    table.cell(0, 1).text = "Preemption"
    table.cell(1, 0).text = "Round Robin"
    table.cell(1, 1).text = "Preemptive"
    doc.save(str(docx_path))

    parser = DocxParser()
    parsed = await parser.parse(docx_path)
    assert parsed.file_type == "docx"
    assert len(parsed.chunks) >= 2
    assert any("Round Robin" in c.content for c in parsed.chunks)


@pytest.mark.asyncio
async def test_pptx_parser(tmp_path: Path):
    pptx_path = tmp_path / "test_network.pptx"
    prs = Presentation()
    # Slide 1
    slide_layout = prs.slide_layouts[0]  # Title slide
    slide1 = prs.slides.add_slide(slide_layout)
    slide1.shapes.title.text = "Computer Networks"
    slide1.placeholders[1].text = "TCP/IP Architecture"

    # Slide 2
    slide2 = prs.slides.add_slide(prs.slide_layouts[1])
    slide2.shapes.title.text = "Transport Layer"
    slide2.placeholders[1].text = "TCP provides reliable connection-oriented byte stream."
    prs.save(str(pptx_path))

    parser = PptxParser()
    parsed = await parser.parse(pptx_path)
    assert parsed.file_type == "pptx"
    assert parsed.total_pages == 2
    assert len(parsed.chunks) == 2
    assert parsed.chunks[0].slide_number == 1
    assert parsed.chunks[1].slide_number == 2
    assert "TCP provides reliable" in parsed.chunks[1].content


@pytest.mark.asyncio
async def test_xlsx_parser(tmp_path: Path):
    xlsx_path = tmp_path / "test_grades.xlsx"
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "ExamScores"
    ws1.append(["Student", "Score", "Result"])
    ws1.append(["Alice", "95", "Pass"])
    ws1.append(["Bob", "82", "Pass"])

    ws2 = wb.create_sheet(title="Statistics")
    ws2.append(["Metric", "Value"])
    ws2.append(["Average", "88.5"])
    wb.save(str(xlsx_path))
    wb.close()

    parser = TabularParser()
    parsed = await parser.parse(xlsx_path)
    assert parsed.file_type == "xlsx"
    assert len(parsed.chunks) == 2
    sheets = [c.sheet_name for c in parsed.chunks]
    assert "ExamScores" in sheets
    assert "Statistics" in sheets
    assert any("Alice" in c.content for c in parsed.chunks)


@pytest.mark.asyncio
async def test_image_ocr_parser(tmp_path: Path):
    img_path = tmp_path / "test_ocr.png"
    img = Image.new("RGB", (300, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 40), "RUBY AI", fill=(0, 0, 0))
    img.save(str(img_path))

    parser = ImageOcrParser()
    parsed = await parser.parse(img_path)
    assert parsed.file_type == "png"
    assert parsed.has_ocr is True
    assert len(parsed.chunks) == 1
    # Verify OCR ran without crashing
    assert parsed.chunks[0].element_type == "image_ocr"
