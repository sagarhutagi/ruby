from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentToolCall(TypedDict, total=False):
    name: str
    arguments: Dict[str, Any]
    reasoning: Optional[str]


class AgentToolResult(TypedDict, total=False):
    tool_name: str
    success: bool
    data: Any
    error: Optional[str]
    execution_time_ms: float


class AgentState(TypedDict, total=False):
    """
    Structured state representation for LangGraph Agent Orchestration.
    Persisted via LangGraph checkpointer across conversation turns.
    """
    prompt: str
    conversation_id: str
    mode: str  # auto, resource-grounded (study), research, coding, general, web-search
    effective_mode: str
    mode_explanation: str
    objective: str
    selected_tools: List[AgentToolCall]
    tool_results: List[AgentToolResult]
    retrieved_chunks: List[Dict[str, Any]]
    web_sources: List[Dict[str, Any]]
    recalled_memories: List[Dict[str, Any]]
    new_memories: List[Dict[str, Any]]
    iteration: int
    max_iterations: int
    is_complete: bool
    final_answer: str
    steps: List[Dict[str, Any]]
    errors: List[str]
    metadata: Dict[str, Any]
