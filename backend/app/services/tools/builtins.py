import asyncio
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.tools.registry import tool_registry
from app.services.tools.sanitizer import search_query_sanitizer
from app.services.search.searxng import searxng_client
from app.services.retrieval.hybrid import hybrid_retriever
from app.services.academic.math_engine import math_engine
from app.services.academic.sandbox import CodeSandbox, DSATracer
from app.core.hardware import hardware_monitor
from app.models.entities import Document, DocumentChunk, Subject
from app.services.academic.quiz_engine import ACADEMIC_QUESTION_TEMPLATES

logger = logging.getLogger("ruby.tools.builtins")


# 1. Web Search Tool
async def tool_web_search(
    queries: Optional[List[str]] = None,
    query: Optional[str] = None,
    num_results: int = 5,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Execute live internet search via SearXNG using focused keyword queries."""
    raw_list = queries if queries else ([query] if query else [])
    sanitized_queries = search_query_sanitizer.deduplicate_and_validate(raw_list, max_queries=3)

    if not sanitized_queries:
        return {
            "success": False,
            "error": "No valid search queries generated. Query was empty or contained only filler words.",
            "results": [],
            "queries_used": [],
        }

    all_results = []
    seen_urls = set()

    for q in sanitized_queries:
        res = await searxng_client.search(query=q, num_results=num_results)
        if res.results:
            for item in res.results:
                if item.url not in seen_urls:
                    seen_urls.add(item.url)
                    all_results.append(item.model_dump())

    return {
        "success": True,
        "queries_used": sanitized_queries,
        "count": len(all_results),
        "results": all_results[:num_results * len(sanitized_queries)],
    }


# 2. Fetch Webpage Content (Trafilatura)
async def tool_fetch_webpage(
    url: str,
    max_chars: int = 4000,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Extract clean readable text and article content from a web page URL."""
    try:
        import trafilatura

        loop = asyncio.get_running_loop()
        downloaded = await loop.run_in_executor(None, lambda: trafilatura.fetch_url(url))
        if not downloaded:
            return {"success": False, "error": f"Failed to download webpage from: {url}"}

        extracted = await loop.run_in_executor(
            None,
            lambda: trafilatura.extract(downloaded, include_links=True, output_format="txt"),
        )
        if not extracted:
            return {"success": False, "error": f"Could not extract clean text content from {url}."}

        snippet = extracted[:max_chars]
        return {
            "success": True,
            "url": url,
            "content": snippet,
            "is_truncated": len(extracted) > max_chars,
            "total_chars": len(extracted),
        }
    except Exception as e:
        return {"success": False, "error": f"Error fetching {url}: {str(e)}"}


# 3. Document Search (RAG)
async def tool_document_search(
    query: str,
    top_k: int = 5,
    subject_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Search uploaded academic course materials and notes using hybrid retrieval."""
    if not session:
        return {"success": False, "error": "Database session required for document search."}

    ret_result = await hybrid_retriever.search(
        session=session,
        query=query,
        top_k=top_k,
        subject_id=subject_id,
        document_ids=document_ids,
    )
    chunks = [c.model_dump() for c in ret_result.chunks]
    return {
        "success": True,
        "query": query,
        "retrieved_count": len(chunks),
        "chunks": chunks,
    }


# 4. List Documents
async def tool_list_documents(
    subject_id: Optional[str] = None,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """List indexed course materials and textbooks."""
    if not session:
        return {"success": False, "error": "Database session required."}

    stmt = select(Document)
    if subject_id:
        stmt = stmt.where(Document.subject_id == subject_id)

    docs = (await session.execute(stmt)).scalars().all()
    return {
        "success": True,
        "count": len(docs),
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "file_type": d.file_type,
                "page_count": d.page_count,
                "chunk_count": d.chunk_count,
                "subject_id": d.subject_id,
            }
            for d in docs
        ],
    }


# 5. Read Document
async def tool_read_document(
    document_id: str,
    page_number: Optional[int] = None,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Read specific pages or excerpts from an indexed course document."""
    if not session:
        return {"success": False, "error": "Database session required."}

    stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    if page_number is not None:
        stmt = stmt.where(DocumentChunk.page_number == page_number)
    stmt = stmt.order_by(DocumentChunk.chunk_index.asc()).limit(10)

    chunks = (await session.execute(stmt)).scalars().all()
    if not chunks:
        return {"success": False, "error": f"No content found for document {document_id}."}

    return {
        "success": True,
        "document_id": document_id,
        "chunks": [
            {
                "page_number": c.page_number,
                "content": c.content,
                "section_heading": c.section_heading,
            }
            for c in chunks
        ],
    }


# 6. Calculate Math Expression
def tool_calculate(expression: str) -> Dict[str, Any]:
    """Evaluate symbolic and arithmetic mathematical expressions using SymPy."""
    res = math_engine.simplify(expression)
    return res


# 7. Solve Equation
def tool_solve_equation(equation: str, variable: str = "x") -> Dict[str, Any]:
    """Solve an algebraic equation f(x) = 0 or lhs = rhs step-by-step."""
    res = math_engine.solve_equation(equation_str=equation, var_str=variable)
    return res


# 8. Plot Mathematical Function Points
def tool_plot_function(
    function: str,
    x_min: float = -10.0,
    x_max: float = 10.0,
    num_points: int = 50,
) -> Dict[str, Any]:
    """Generate coordinate points [x, y] to plot a mathematical function f(x)."""
    try:
        import sympy as sp
        x = sp.Symbol("x")
        expr = sp.sympify(function)
        step = (x_max - x_min) / max(1, num_points - 1)
        points = []

        for i in range(num_points):
            val_x = x_min + i * step
            try:
                val_y = float(expr.evalf(subs={x: val_x}))
                if not (sp.isnan(val_y) or sp.is_infinite(val_y)):
                    points.append({"x": round(val_x, 3), "y": round(val_y, 4)})
            except Exception:
                continue

        return {
            "success": True,
            "function": function,
            "x_range": [x_min, x_max],
            "points": points,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# 9. Execute Code Sandbox
def tool_execute_code(code: str) -> Dict[str, Any]:
    """Execute Python code in an isolated AST-verified sandbox with execution time limit."""
    sandbox = CodeSandbox(timeout_seconds=4.0)
    return sandbox.execute(code)


# 10. Trace DSA Algorithm
def tool_trace_dsa(
    algorithm: str,
    array: List[int],
    target: Optional[int] = None,
) -> Dict[str, Any]:
    """Simulate step-by-step trace of core algorithms (binary search, bubble sort)."""
    if algorithm == "binary_search":
        if target is None:
            return {"success": False, "error": "Target integer required for binary search."}
        return DSATracer.trace_binary_search(array, target)
    elif algorithm == "bubble_sort":
        return DSATracer.trace_bubble_sort(array)
    else:
        return {"success": False, "error": f"Algorithm '{algorithm}' not supported. Choose 'binary_search' or 'bubble_sort'."}


# 11. System Hardware Info
def tool_get_system_info() -> Dict[str, Any]:
    """Check host CPU, RAM, disk, and operating system metrics."""
    cpu = hardware_monitor.get_cpu_metrics()
    ram = hardware_monitor.get_ram_metrics()
    disk = hardware_monitor.get_disk_metrics()
    return {
        "success": True,
        "cpu": {"percent": cpu.percent, "core_count": cpu.core_count, "frequency_mhz": cpu.frequency_mhz},
        "ram": {"total_mb": ram.total_mb, "used_mb": ram.used_mb, "available_mb": ram.available_mb, "percent": ram.percent},
        "disk": {"total_gb": disk.total_gb, "used_gb": disk.used_gb, "free_gb": disk.free_gb, "percent": disk.percent},
    }


# 12. GPU Stats
async def tool_get_gpu_stats() -> Dict[str, Any]:
    """Check local GPU accelerator state and VRAM consumption."""
    gpu = await hardware_monitor.get_gpu_metrics()
    return {
        "success": True,
        "available": gpu.available,
        "device_name": gpu.device_name,
        "backend": gpu.backend,
        "vram_total_mb": gpu.vram_total_mb,
        "vram_used_mb": gpu.vram_used_mb,
        "vram_free_mb": gpu.vram_free_mb,
        "utilization_percent": gpu.utilization_percent,
        "temperature_c": gpu.temperature_c,
    }


# 13. Generate Quiz
def tool_generate_quiz(subject: str = "Operating Systems", count: int = 3) -> Dict[str, Any]:
    """Generate academic practice quiz questions for a chosen subject."""
    matched = [q for q in ACADEMIC_QUESTION_TEMPLATES if subject.lower() in q.get("subject", "").lower()]
    pool = matched if matched else ACADEMIC_QUESTION_TEMPLATES
    selected = pool[:count]
    return {
        "success": True,
        "subject": subject,
        "count": len(selected),
        "questions": selected,
    }


# 14. Create Flashcards
def tool_create_flashcards(
    deck_name: str,
    cards: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Format and prepare spaced repetition flashcards for study review."""
    return {
        "success": True,
        "deck_name": deck_name,
        "card_count": len(cards),
        "cards": cards,
    }


# 15. Search Knowledge Graph
async def tool_search_knowledge_graph(
    concept: str,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Find related concepts, prerequisites, and connections in the academic Knowledge Graph."""
    if not session:
        return {"success": False, "error": "Database session required."}
    from app.services.graph.service import KnowledgeGraphService
    kg = KnowledgeGraphService()
    graph = await kg.get_graph(session=session)
    matching_nodes = [n for n in graph["nodes"] if concept.lower() in n["label"].lower()]
    node_ids = {n["id"] for n in matching_nodes}
    connected_edges = [e for e in graph["edges"] if e["source_id"] in node_ids or e["target_id"] in node_ids]
    return {
        "success": True,
        "concept": concept,
        "matching_nodes": matching_nodes,
        "connected_edges": connected_edges,
    }


def register_all_builtin_tools() -> None:
    """Register all built-in academic and system tools in Ruby ToolRegistry."""
    # 1. web_search
    tool_registry.register(
        name="web_search",
        description="Search the live internet for recent publications, web documentation, or current information via SearXNG. Provide 1 to 3 concise, keyword-focused search queries without conversational words.",
        parameters={
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "1 to 3 concise keyword search queries.",
                },
                "num_results": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of results to retrieve per query.",
                },
            },
            "required": ["queries"],
        },
        handler=tool_web_search,
        permission_level="read",
        timeout_seconds=12.0,
        category="web",
    )

    # 2. fetch_webpage
    tool_registry.register(
        name="fetch_webpage",
        description="Extract and parse clean readable article text from a target webpage URL using Trafilatura.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Canonical HTTP/HTTPS URL of the webpage to fetch."},
                "max_chars": {"type": "integer", "default": 4000, "description": "Maximum characters to extract."},
            },
            "required": ["url"],
        },
        handler=tool_fetch_webpage,
        permission_level="read",
        timeout_seconds=10.0,
        category="web",
    )

    # 3. document_search
    tool_registry.register(
        name="document_search",
        description="Search locally uploaded course materials, notes, and textbook PDFs using hybrid vector and keyword search.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Semantic query describing the academic topic."},
                "top_k": {"type": "integer", "default": 5, "description": "Number of document sections to retrieve."},
                "subject_id": {"type": "string", "description": "Optional subject ID to filter search."},
            },
            "required": ["query"],
        },
        handler=tool_document_search,
        permission_level="read",
        timeout_seconds=10.0,
        category="knowledge",
    )

    # 4. list_documents
    tool_registry.register(
        name="list_documents",
        description="List all available uploaded textbooks, lecture notes, and course documents.",
        parameters={
            "type": "object",
            "properties": {
                "subject_id": {"type": "string", "description": "Optional subject ID filter."},
            },
        },
        handler=tool_list_documents,
        permission_level="read",
        timeout_seconds=5.0,
        category="knowledge",
    )

    # 5. read_document
    tool_registry.register(
        name="read_document",
        description="Read excerpts and chunks from an uploaded document by its ID and optional page number.",
        parameters={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Document ID."},
                "page_number": {"type": "integer", "description": "Page number to read."},
            },
            "required": ["document_id"],
        },
        handler=tool_read_document,
        permission_level="read",
        timeout_seconds=5.0,
        category="knowledge",
    )

    # 6. calculate
    tool_registry.register(
        name="calculate",
        description="Evaluate arithmetic, algebraic, or trigonometric mathematical expressions using SymPy.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Mathematical expression string, e.g. '2**16 - 1' or 'sin(pi/3)'."},
            },
            "required": ["expression"],
        },
        handler=tool_calculate,
        permission_level="read",
        timeout_seconds=5.0,
        category="mathematics",
    )

    # 7. solve_equation
    tool_registry.register(
        name="solve_equation",
        description="Solve an algebraic equation for a target variable step-by-step using SymPy.",
        parameters={
            "type": "object",
            "properties": {
                "equation": {"type": "string", "description": "Equation string, e.g. 'x^2 - 4 = 0' or '3*x + 5 = 20'."},
                "variable": {"type": "string", "default": "x", "description": "Variable to isolate and solve for."},
            },
            "required": ["equation"],
        },
        handler=tool_solve_equation,
        permission_level="read",
        timeout_seconds=8.0,
        category="mathematics",
    )

    # 8. plot_function
    tool_registry.register(
        name="plot_function",
        description="Generate numeric (x, y) plot coordinates for a function f(x) over a specified range.",
        parameters={
            "type": "object",
            "properties": {
                "function": {"type": "string", "description": "Function in terms of x, e.g. 'x**2' or 'cos(x)'."},
                "x_min": {"type": "number", "default": -10.0},
                "x_max": {"type": "number", "default": 10.0},
                "num_points": {"type": "integer", "default": 50},
            },
            "required": ["function"],
        },
        handler=tool_plot_function,
        permission_level="read",
        timeout_seconds=5.0,
        category="mathematics",
    )

    # 9. execute_code
    tool_registry.register(
        name="execute_code",
        description="Execute a Python algorithm or script safely inside a restricted sandbox environment.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source code to execute."},
            },
            "required": ["code"],
        },
        handler=tool_execute_code,
        permission_level="execute",
        timeout_seconds=6.0,
        category="programming",
    )

    # 10. trace_dsa
    tool_registry.register(
        name="trace_dsa",
        description="Trace execution steps of core computer science algorithms ('binary_search' or 'bubble_sort').",
        parameters={
            "type": "object",
            "properties": {
                "algorithm": {"type": "string", "enum": ["binary_search", "bubble_sort"]},
                "array": {"type": "array", "items": {"type": "integer"}},
                "target": {"type": "integer", "description": "Target element for search algorithms."},
            },
            "required": ["algorithm", "array"],
        },
        handler=tool_trace_dsa,
        permission_level="read",
        timeout_seconds=5.0,
        category="programming",
    )

    # 11. get_system_info
    tool_registry.register(
        name="get_system_info",
        description="Retrieve host hardware metrics including CPU utilization, core count, RAM usage, and disk space.",
        parameters={"type": "object", "properties": {}},
        handler=tool_get_system_info,
        permission_level="read",
        timeout_seconds=3.0,
        category="system",
    )

    # 12. get_gpu_stats
    tool_registry.register(
        name="get_gpu_stats",
        description="Retrieve local GPU accelerator telemetry, VRAM usage, and temperatures.",
        parameters={"type": "object", "properties": {}},
        handler=tool_get_gpu_stats,
        permission_level="read",
        timeout_seconds=5.0,
        category="system",
    )

    # 13. generate_quiz
    tool_registry.register(
        name="generate_quiz",
        description="Generate multiple-choice or true/false academic quiz questions for a chosen subject.",
        parameters={
            "type": "object",
            "properties": {
                "subject": {"type": "string", "default": "Operating Systems"},
                "count": {"type": "integer", "default": 3},
            },
        },
        handler=tool_generate_quiz,
        permission_level="read",
        timeout_seconds=4.0,
        category="academic",
    )

    # 14. create_flashcards
    tool_registry.register(
        name="create_flashcards",
        description="Create or format spaced repetition flashcards for study review.",
        parameters={
            "type": "object",
            "properties": {
                "deck_name": {"type": "string"},
                "cards": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "front": {"type": "string"},
                            "back": {"type": "string"},
                        },
                        "required": ["front", "back"],
                    },
                },
            },
            "required": ["deck_name", "cards"],
        },
        handler=tool_create_flashcards,
        permission_level="read",
        timeout_seconds=4.0,
        category="academic",
    )

    # 15. search_knowledge_graph
    tool_registry.register(
        name="search_knowledge_graph",
        description="Search academic concept graph for prerequisite chains and related topics.",
        parameters={
            "type": "object",
            "properties": {
                "concept": {"type": "string", "description": "Concept name or keyword."},
            },
            "required": ["concept"],
        },
        handler=tool_search_knowledge_graph,
        permission_level="read",
        timeout_seconds=5.0,
        category="academic",
    )


# Automatically initialize builtins on load
register_all_builtin_tools()
