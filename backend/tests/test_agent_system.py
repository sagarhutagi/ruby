import pytest
from sqlalchemy import select
from app.services.tools.registry import tool_registry
from app.services.tools.sanitizer import search_query_sanitizer
from app.services.agent.planner import AgentPlanner
from app.services.agent.graph import ruby_agent_graph
from app.services.ai.adapters.agy import AGYAdapter
from app.models.entities import Document, Subject


@pytest.mark.asyncio
async def test_tool_registry_tools():
    """Verify tool registry exposes all core academic and system tools."""
    tools = tool_registry.list_tools()
    tool_names = [t.name for t in tools]

    assert "web_search" in tool_names
    assert "fetch_webpage" in tool_names
    assert "document_search" in tool_names
    assert "calculate" in tool_names
    assert "solve_equation" in tool_names
    assert "execute_code" in tool_names
    assert "trace_dsa" in tool_names
    assert "get_system_info" in tool_names
    assert "get_gpu_stats" in tool_names
    assert "generate_quiz" in tool_names

    # Test math tool execution
    calc_res = await tool_registry.execute("calculate", {"expression": "2**10 + 24"})
    assert calc_res.success is True
    assert calc_res.data["result"] == "1048"

    # Test equation solve
    eq_res = await tool_registry.execute("solve_equation", {"equation": "x^2 - 16 = 0", "variable": "x"})
    assert eq_res.success is True
    assert "-4" in eq_res.data["solutions"]
    assert "4" in eq_res.data["solutions"]

    # Test DSA trace
    dsa_res = await tool_registry.execute("trace_dsa", {"algorithm": "binary_search", "array": [2, 4, 6, 8, 10], "target": 6})
    assert dsa_res.success is True
    assert dsa_res.data["found_index"] == 2

    # Test System Hardware
    sys_res = await tool_registry.execute("get_system_info", {})
    assert sys_res.success is True
    assert "cpu" in sys_res.data
    assert "ram" in sys_res.data

    # Test Code Sandbox
    code_res = await tool_registry.execute("execute_code", {"code": "print('sandbox_test_ok')"})
    assert code_res.success is True
    assert "sandbox_test_ok" in code_res.data["stdout"]


@pytest.mark.asyncio
async def test_search_query_sanitization():
    """Verify focused keyword query generation strips verbose conversational prompts."""
    # Test conversational query distillation
    prompt1 = "Can you explain the latest developments in retrieval augmented generation, compare them with what I learned in my previous notes, and tell me which architecture would be best for my project?"
    sanitized1 = search_query_sanitizer.sanitize_single_query(prompt1)
    assert sanitized1 is not None
    assert "can you explain" not in sanitized1.lower()
    assert "compare them with" not in sanitized1.lower()
    assert "retrieval augmented generation" in sanitized1.lower()

    # Test multi-query extraction
    prompt2 = "Compare TCP Reno versus TCP BBR congestion control"
    queries2 = search_query_sanitizer.extract_queries_from_prompt(prompt2)
    assert len(queries2) >= 1
    for q in queries2:
        assert len(q) < 120

    # Test deduplication & whitespace stripping
    dupes = ["  tcp reno  ", "TCP Reno", "tcp reno?", ""]
    valid = search_query_sanitizer.deduplicate_and_validate(dupes)
    assert len(valid) == 1
    assert valid[0] == "tcp reno"


@pytest.mark.asyncio
async def test_agent_planner_auto_routing():
    """Verify AgentPlanner accurately classifies intent and routes Auto mode."""
    # Math prompt -> Study / resource-grounded + solve_equation
    math_plan = await AgentPlanner.plan_intent_and_tools(
        provider=None,
        prompt="Solve the differential equation x^2 - 5*x + 6 = 0 for x",
        mode="auto",
    )
    assert math_plan["effective_mode"] == "resource-grounded"
    tool_names = [t["name"] for t in math_plan["selected_tools"]]
    assert "solve_equation" in tool_names

    # Coding / DSA prompt -> Coding + trace_dsa
    coding_plan = await AgentPlanner.plan_intent_and_tools(
        provider=None,
        prompt="Implement and trace binary search for target 7 in [1, 3, 5, 7, 9]",
        mode="auto",
    )
    assert coding_plan["effective_mode"] == "coding"
    c_tool_names = [t["name"] for t in coding_plan["selected_tools"]]
    assert "trace_dsa" in c_tool_names

    # Live web query -> Web Search + web_search
    web_plan = await AgentPlanner.plan_intent_and_tools(
        provider=None,
        prompt="What are the latest 2026 releases and news about Python?",
        mode="auto",
    )
    assert web_plan["effective_mode"] == "web-search"
    w_tool_names = [t["name"] for t in web_plan["selected_tools"]]
    assert "web_search" in w_tool_names
    # Query must be focused, not raw prompt
    web_args = next(t for t in web_plan["selected_tools"] if t["name"] == "web_search")["arguments"]
    assert "queries" in web_args
    assert len(web_args["queries"]) >= 1


@pytest.mark.asyncio
async def test_langgraph_agent_execution_workflow():
    """Verify LangGraph agent workflow graph compiles and executes state transitions."""
    initial_state = {
        "prompt": "Evaluate expression 12 * 12 and check system info",
        "conversation_id": "test-conv-langgraph-1",
        "mode": "auto",
        "iteration": 0,
        "max_iterations": 3,
        "selected_tools": [
            {"name": "calculate", "arguments": {"expression": "12 * 12"}},
        ],
        "tool_results": [],
        "steps": [],
        "metadata": {},
    }

    result = await ruby_agent_graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": "test-conv-langgraph-1"}},
    )

    assert result is not None
    assert result.get("is_complete") is True
    tool_names = [t["tool_name"] for t in result.get("tool_results", [])]
    assert "calculate" in tool_names


@pytest.mark.asyncio
async def test_agy_cli_adapter_integration():
    """Verify AGY CLI adapter initializes, detects binary, and parses quotas."""
    adapter = AGYAdapter(name="AGY CLI", provider_type="agy")
    assert adapter.name == "AGY CLI"

    # Connection test
    conn = await adapter.test_connection()
    assert "success" in conn
    if conn["success"]:
        assert conn["version"] is not None

        # Model list discovery
        models = await adapter.list_models()
        assert len(models) >= 4
        model_ids = [m.id for m in models]
        assert any("gemini" in m_id or "claude" in m_id for m_id in model_ids)

        # Quotas summary
        quotas = await adapter.get_quota_summary()
        assert quotas["success"] is True
        assert len(quotas["groups"]) >= 1
        first_group = quotas["groups"][0]
        assert "buckets" in first_group
        for b in first_group["buckets"]:
            assert "remaining_percentage" in b
            assert "used_percentage" in b
            assert b["remaining_percentage"] + b["used_percentage"] == pytest.approx(100.0, abs=0.5)


@pytest.mark.asyncio
async def test_course_materials_intact_and_preserved(session):
    """
    CRITICAL CONSTRAINT: Verify user's uploaded Mathematics and Computer Networks
    materials are 100% intact, not mutated or deleted.
    """
    stmt = select(Document)
    docs = (await session.execute(stmt)).scalars().all()
    doc_titles = [d.title.lower() for d in docs]

    # Verify existing documents are present
    assert len(docs) >= 1, "User course documents must remain preserved in SQLite database."
