import pytest
import io
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.documents.markup_parser import MarkupParser
from app.services.documents.tabular_parser import TabularParser
from app.services.documents.registry import parser_registry

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_markup_parser_markdown():
    parser = MarkupParser()
    md_file = FIXTURES_DIR / "sample.md"
    parsed = await parser.parse(md_file)

    assert parsed.title == "Sample"
    assert parsed.file_type in ["md", "markdown"]
    assert len(parsed.chunks) >= 2

    headings = [c.section_heading for c in parsed.chunks]
    assert "Dijkstra's Algorithm" in headings
    assert "Dynamic Programming" in headings
    assert any("O((V + E) log V)" in c.content for c in parsed.chunks)


@pytest.mark.asyncio
async def test_markup_parser_html_table():
    parser = MarkupParser()
    html_file = FIXTURES_DIR / "sample.html"
    parsed = await parser.parse(html_file)

    assert parsed.title == "Computer Networks Overview"
    table_chunks = [c for c in parsed.chunks if c.element_type == "table"]
    assert len(table_chunks) >= 1
    assert "Application" in table_chunks[0].content
    assert "HTTP / DNS" in table_chunks[0].content


@pytest.mark.asyncio
async def test_markup_parser_json_and_txt():
    parser = MarkupParser()
    json_parsed = await parser.parse(FIXTURES_DIR / "sample.json")
    assert len(json_parsed.chunks) >= 1
    assert "Boolean Algebra" in json_parsed.chunks[0].content

    txt_parsed = await parser.parse(FIXTURES_DIR / "sample.txt")
    assert len(txt_parsed.chunks) >= 1
    assert any("Coffman conditions" in c.content for c in txt_parsed.chunks)


@pytest.mark.asyncio
async def test_tabular_parser_csv():
    parser = TabularParser()
    csv_file = FIXTURES_DIR / "sample.csv"
    parsed = await parser.parse(csv_file)

    assert len(parsed.chunks) >= 1
    chunk = parsed.chunks[0]
    assert chunk.element_type == "table"
    assert chunk.sheet_name == "Default"
    assert "Student_ID" in chunk.content
    assert "S1001" in chunk.content


@pytest.mark.asyncio
async def test_parser_registry_extensions_and_unsupported():
    supported = parser_registry.get_supported_extensions()
    assert ".pdf" in supported
    assert ".docx" in supported
    assert ".pptx" in supported
    assert ".xlsx" in supported
    assert ".csv" in supported
    assert ".md" in supported

    with pytest.raises(ValueError) as exc:
        await parser_registry.parse_file(Path("unsupported_test.xyz_unknown"))
    assert "Unsupported file format" in str(exc.value)


@pytest.mark.asyncio
async def test_document_upload_and_duplicate_detection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a test text file
        file_bytes = b"Algorithmic analysis of Red-Black Trees: A balanced binary search tree with logarithmic height."
        files = {"files": ("rbt.txt", io.BytesIO(file_bytes), "text/plain")}

        # 1. First upload
        res1 = await client.post("/api/v1/documents/upload", files=files)
        assert res1.status_code == 201
        data1 = res1.json()
        assert len(data1) == 1
        doc_id = data1[0]["document_id"]
        job_id = data1[0]["job_id"]
        assert data1[0]["is_duplicate"] is False

        # 2. Duplicate upload with identical content
        files_dup = {"files": ("rbt_copy.txt", io.BytesIO(file_bytes), "text/plain")}
        res2 = await client.post("/api/v1/documents/upload", files=files_dup)
        assert res2.status_code == 201
        data2 = res2.json()
        assert data2[0]["is_duplicate"] is True
        assert data2[0]["document_id"] == doc_id

        # 3. List documents
        list_res = await client.get("/api/v1/documents?q=rbt")
        assert list_res.status_code == 200
        docs = list_res.json()
        assert any(d["id"] == doc_id for d in docs)

        # 4. Delete document
        del_res = await client.delete(f"/api/v1/documents/{doc_id}")
        assert del_res.status_code == 204
