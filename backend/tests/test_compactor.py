import pytest
from app.services.agent.compactor import ContextCompactor, CompactionCheckpoint, KNOWN_MODEL_CONTEXT_WINDOWS
from app.services.agent.dag import TaskDAG, TaskStatus
from app.services.agent.events import EventType
from app.services.ai.base import ChatMessage


def test_token_estimation():
    """Verify tokenizer estimates non-zero tokens accurately."""
    compactor = ContextCompactor()
    text = "Ruby is an academic intelligence system with DAG task planning."
    tokens = compactor.estimate_tokens(text)
    assert tokens > 5
    assert compactor.estimate_tokens("") == 0


def test_model_aware_context_window_resolution():
    """Verify provider and model specific context window lookup."""
    compactor = ContextCompactor()

    # Gemini 3.8 Flash High -> 1,000,000 tokens
    assert compactor.resolve_model_context_limit("gemini-3.8-flash-high") == 1_000_000

    # Claude Sonnet 4.6 -> 200,000 tokens
    assert compactor.resolve_model_context_limit("claude-sonnet-4-6") == 200_000

    # Qwen 2.5 7B -> 32,768 tokens
    assert compactor.resolve_model_context_limit("qwen2.5:7b") == 32_768

    # LLaMA 3.2 -> 8,192 tokens
    assert compactor.resolve_model_context_limit("llama3.2:latest") == 8_192

    # Provider heuristic fallback
    assert compactor.resolve_model_context_limit(model_name="unknown", provider_type="gemini") == 1_000_000
    assert compactor.resolve_model_context_limit(model_name="unknown", provider_type="anthropic") == 200_000

    # Explicit override
    assert compactor.resolve_model_context_limit(explicit_limit=16384) == 16384


def test_effective_limit_with_headroom_and_budget():
    """Verify calculation respects both headroom and token budget."""
    # Headroom 0.15 on 8,192 is 6,963; token budget 4,096 caps it
    compactor = ContextCompactor(headroom=0.15, token_budget=4096)
    limit = compactor.calculate_effective_limit(model_name="llama3.2:latest")
    assert limit == 4096

    # With high token budget, headroom determines ceiling
    compactor_high = ContextCompactor(headroom=0.20, token_budget=10000)
    limit_high = compactor_high.calculate_effective_limit(model_name="llama3.2:latest")
    assert limit_high == int(8192 * 0.80)


def test_context_breakdown_analysis():
    """Verify context breakdown across all components."""
    compactor = ContextCompactor()
    system_inst = "System instruction"
    messages = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi there"),
    ]
    tool_results = [{"tool_name": "math_solve", "data": 42}]
    docs = [{"content": "Page content from notes", "subject_code": "CS301"}]

    dag = TaskDAG(conversation_id="conv_analysis")
    dag.add_task(title="Analyze Notes")

    breakdown = compactor.analyze_context(system_inst, messages, tool_results, docs, dag)
    assert breakdown.system_tokens > 0
    assert breakdown.history_tokens > 0
    assert breakdown.tools_tokens > 0
    assert breakdown.retrieval_tokens > 0
    assert breakdown.task_state_tokens > 0
    assert breakdown.total_tokens == (
        breakdown.system_tokens + breakdown.history_tokens + breakdown.tools_tokens +
        breakdown.retrieval_tokens + breakdown.task_state_tokens
    )


def test_incremental_compaction_and_event_emission():
    """Verify compaction triggers when exceeding limit, emits event, and condenses older turns."""
    # Set low token budget of 60 tokens to force compaction of ~115 token context
    compactor = ContextCompactor(headroom=0.10, token_budget=60, recent_turns_to_keep=1)

    system_inst = "You are Ruby assistant."
    messages = [
        ChatMessage(role="user", content="Round 1: Explain the Bellman-Ford algorithm in detail with mathematical notation and relaxation steps."),
        ChatMessage(role="assistant", content="Round 1: Bellman-Ford relaxes edges |V|-1 times with formula dist[v] = min(dist[v], dist[u] + weight)."),
        ChatMessage(role="user", content="Round 2: What about Dijkstra? In CS301 ISA 1 I got 44/50."),
        ChatMessage(role="assistant", content="Round 2: Dijkstra uses a min-priority queue with non-negative edge weights."),
        ChatMessage(role="user", content="Round 3: Current question: Compare their complexities."),
    ]

    dag = TaskDAG(conversation_id="conv_compact")
    dag.add_task(title="Unfinished Network Simulation", task_id="task_active")

    compacted_msgs, event = compactor.compact(
        system_instruction=system_inst,
        messages=messages,
        dag=dag,
        model_name="llama3.2:latest",
        conversation_id="conv_compact",
    )

    # Event must be generated
    assert event is not None
    assert event.type == EventType.CONTEXT_COMPACTED
    assert event.payload["tokens_freed"] > 0
    assert event.payload["original_tokens"] > event.payload["compacted_tokens"]

    # Preserved recent messages
    assert any("Round 3" in m.content for m in compacted_msgs)

    # Active DAG task preserved in system compaction block
    system_text = " ".join(m.content for m in compacted_msgs if m.role == "system")
    assert "Unfinished Network Simulation" in system_text
    assert "CS301" in system_text or "44/50" in system_text or "Bellman-Ford" in system_text


def test_compaction_checkpoint_recovery():
    """Verify compaction checkpoint can be serialized and recovered across restarts."""
    cp = CompactionCheckpoint(
        version=1,
        summarized_rounds=4,
        running_summary="Prior discussion on Computer Networks routing protocols.",
        preserved_facts=["CS301 ISA 1: 44/50", "Formula: d[v] <= d[u] + w"],
    )
    d = cp.to_dict()
    restored = CompactionCheckpoint.from_dict(d)

    assert restored.version == 1
    assert restored.summarized_rounds == 4
    assert "Computer Networks" in restored.running_summary
    assert "CS301 ISA 1: 44/50" in restored.preserved_facts
