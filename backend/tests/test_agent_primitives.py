import asyncio
import os
import signal
import sys
import time
from typing import AsyncGenerator, List, Optional
import pytest

from app.services.agent.cancellation import CancellationToken, ProcessGroupManager
from app.services.agent.events import AgentEvent, EventType
from app.services.agent.permissions import PermissionManager, PermissionRule
from app.services.agent.runner import AgentRunner
from app.services.ai.base import (
    BaseAIProvider,
    ChatMessage,
    ChatResponse,
    ChatResponseChunk,
    ModelInfo,
)
from app.services.tools.registry import ToolRegistry


# Mock AI Provider for testing
class MockAIProvider(BaseAIProvider):
    def __init__(self, responses: Optional[List[str]] = None):
        super().__init__(name="mock", provider_type="mock")
        self.responses = responses or ["Mocked assistant explanation."]

    async def test_connection(self):
        return {"success": True, "message": "Mock connection OK"}

    async def list_models(self):
        return [ModelInfo(id="mock-model", name="Mock Model", provider_type="mock")]

    async def chat(self, messages, model=None, **kwargs):
        return ChatResponse(content=self.responses[0], model="mock-model")

    async def stream_chat(self, messages, model=None, **kwargs) -> AsyncGenerator[ChatResponseChunk, None]:
        text = self.responses[0]
        words = text.split(" ")
        for w in words:
            yield ChatResponseChunk(content_delta=w + " ")
            await asyncio.sleep(0.005)
        yield ChatResponseChunk(content_delta="", is_done=True, finish_reason="stop")


@pytest.mark.asyncio
async def test_agent_event_serialization():
    """Verify AgentEvent serialization to dict and SSE formatting."""
    event = AgentEvent(
        type=EventType.STEP_START,
        conversation_id="conv_123",
        step_id="step_1",
        payload={"label": "Planning", "status": "running"},
    )
    d = event.to_dict()
    assert d["type"] == "step_start"
    assert d["conversation_id"] == "conv_123"
    assert d["step_id"] == "step_1"
    assert d["payload"]["label"] == "Planning"

    sse = event.to_sse()
    assert sse.startswith("data: {")
    assert sse.endswith("}\n\n")
    assert '"step_start"' in sse


@pytest.mark.asyncio
async def test_cancellation_token_callbacks_and_state():
    """Verify CancellationToken states and callbacks execution."""
    token = CancellationToken(grace_period_seconds=0.5)
    assert not token.is_cancelled

    callback_called = False
    async_callback_called = False

    def sync_cb():
        nonlocal callback_called
        callback_called = True

    async def async_cb():
        nonlocal async_callback_called
        async_callback_called = True

    token.register_callback(sync_cb)
    token.register_callback(async_cb)

    await token.cancel()
    assert token.is_cancelled
    assert callback_called
    assert async_callback_called

    with pytest.raises(asyncio.CancelledError):
        token.check_cancelled()


@pytest.mark.asyncio
async def test_process_group_manager_termination():
    """Verify ProcessGroupManager kills running child process cleanly."""
    # Spawn a sleeping child process in a new process group
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        "import time; time.sleep(30)",
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
    )
    pid = proc.pid

    # Register and terminate with 0.5s grace period
    ProcessGroupManager.register_pid(pid)
    success = await ProcessGroupManager.terminate_process_group(pid, grace_period=0.5)
    assert success

    # Verify process has exited
    await proc.wait()
    assert proc.returncode is not None


@pytest.mark.asyncio
async def test_permission_manager_rules_and_evaluation():
    """Verify wildcard permission evaluation and rule priority."""
    pm = PermissionManager()

    # Default rules
    assert pm.evaluate("read", "any_file.txt") == "allow"
    assert pm.evaluate("web_search") == "allow"
    assert pm.evaluate("math_solve") == "allow"
    assert pm.evaluate("execute_python_code") == "ask"
    assert pm.evaluate("shell_command") == "deny"

    # Add overriding custom rule
    pm.add_rule(PermissionRule("execute_python_code", "*.py", "allow"))
    assert pm.evaluate("execute_python_code", "test.py") == "allow"
    assert pm.evaluate("execute_python_code", "test.sh") == "ask"


@pytest.mark.asyncio
async def test_permission_approval_async_deferred():
    """Verify async approval resolution for 'ask' permissions."""
    pm = PermissionManager()
    req_id = "test_perm_001"

    # Launch check_or_request_approval in background task
    approval_task = asyncio.create_task(
        pm.check_or_request_approval(
            tool_name="execute_python_code",
            arguments={"code": "print(1)"},
            request_id=req_id,
            timeout_seconds=5.0,
        )
    )

    # Allow task to initialize and create pending future
    await asyncio.sleep(0.05)
    pending = pm.get_pending_requests()
    assert len(pending) == 1
    assert pending[0].request_id == req_id

    # Resolve approval from simulated UI
    resolved = pm.resolve_approval(req_id, approved=True, remember=True)
    assert resolved

    is_allowed = await approval_task
    assert is_allowed is True

    # Check remembered rule
    assert pm.evaluate("execute_python_code") == "allow"


@pytest.mark.asyncio
async def test_agent_runner_execution_and_events():
    """Verify AgentRunner streams all events and executes tools properly."""
    provider = MockAIProvider(["Calculated solution: 42"])
    custom_tr = ToolRegistry()

    async def mock_math_handler(equation: str = "", **kwargs):
        return f"Evaluated: {equation} = 42"

    async def mock_doc_handler(query: str = "", **kwargs):
        return {"chunks": []}

    custom_tr.register(
        name="solve_equation",
        description="Math solver",
        parameters={"type": "object", "properties": {"equation": {"type": "string"}}},
        handler=mock_math_handler,
    )
    custom_tr.register(
        name="document_search",
        description="Doc search",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        handler=mock_doc_handler,
    )

    pm = PermissionManager()
    runner = AgentRunner(provider=provider, tool_registry=custom_tr, permission_manager=pm)

    events: List[AgentEvent] = []
    async for event in runner.run(
        prompt="Solve 2*x + 4 = 10 for x",
        conversation_id="conv_test_1",
        mode="auto",
    ):
        events.append(event)

    event_types = [e.type for e in events]
    assert EventType.STEP_START in event_types
    assert EventType.STEP_COMPLETE in event_types
    assert EventType.ACTION_TOOL_CALL in event_types
    assert EventType.OBSERVATION_TOOL_RESULT in event_types
    assert EventType.TOKEN_DELTA in event_types
    assert EventType.AGENT_COMPLETE in event_types

    # Verify math tool was called and succeeded
    math_obs = next(
        e for e in events
        if e.type == EventType.OBSERVATION_TOOL_RESULT and e.payload["tool_name"] == "solve_equation"
    )
    assert math_obs.payload["success"] is True

    # Verify complete event
    complete_event = next(e for e in events if e.type == EventType.AGENT_COMPLETE)
    assert complete_event.payload["effective_mode"] in ("study", "resource-grounded")
    assert "Calculated solution" in complete_event.payload["final_answer"]
