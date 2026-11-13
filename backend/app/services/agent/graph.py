import logging
import time
from typing import Any, Dict, List, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.services.agent.state import AgentState, AgentToolCall, AgentToolResult
from app.services.agent.planner import AgentPlanner
from app.services.tools.registry import tool_registry

logger = logging.getLogger("ruby.agent.graph")


async def plan_node(state: AgentState) -> Dict[str, Any]:
    """Analyze user prompt, determine effective mode, and decide required tools."""
    prompt = state.get("prompt", "")
    mode = state.get("mode", "auto")
    provider = state.get("metadata", {}).get("provider")

    plan = await AgentPlanner.plan_intent_and_tools(
        provider=provider,
        prompt=prompt,
        mode=mode,
    )

    steps = list(state.get("steps", []))
    steps.append({
        "id": "intent",
        "label": f"Mode Routed: {plan['effective_mode'].replace('-', ' ').title()}",
        "status": "completed",
        "description": plan["mode_explanation"],
    })

    return {
        "effective_mode": plan["effective_mode"],
        "mode_explanation": plan["mode_explanation"],
        "selected_tools": plan["selected_tools"],
        "objective": plan["objective"],
        "steps": steps,
        "iteration": state.get("iteration", 0) + 1,
    }


async def execute_tools_node(state: AgentState) -> Dict[str, Any]:
    """Execute all selected tools with timeout containment and structured result capture."""
    tools_to_run = state.get("selected_tools", [])
    session = state.get("metadata", {}).get("session")
    tool_results: List[AgentToolResult] = list(state.get("tool_results", []))
    web_sources: List[Dict[str, Any]] = list(state.get("web_sources", []))
    retrieved_chunks: List[Dict[str, Any]] = list(state.get("retrieved_chunks", []))
    steps = list(state.get("steps", []))

    for tool_call in tools_to_run:
        t_name = tool_call["name"]
        t_args = tool_call.get("arguments", {})

        # Record step
        step_id = f"tool_{t_name}_{len(steps)}"
        steps.append({
            "id": step_id,
            "label": f"Executing Tool: {t_name}",
            "status": "running",
            "description": f"Calling {t_name} with arguments: {str(t_args)[:80]}...",
        })

        exec_res = await tool_registry.execute(
            name=t_name,
            arguments=t_args,
            session=session,
        )

        tool_results.append({
            "tool_name": t_name,
            "success": exec_res.success,
            "data": exec_res.data,
            "error": exec_res.error,
            "execution_time_ms": exec_res.execution_time_ms,
        })

        # Update step
        for s in steps:
            if s["id"] == step_id:
                s["status"] = "completed" if exec_res.success else "failed"
                s["description"] = f"Finished {t_name} in {round(exec_res.execution_time_ms)}ms"

        # Capture tool output domain objects
        if exec_res.success and exec_res.data:
            if t_name == "web_search" and isinstance(exec_res.data, dict):
                results = exec_res.data.get("results", [])
                web_sources.extend(results)
            elif t_name == "document_search" and isinstance(exec_res.data, dict):
                chunks = exec_res.data.get("chunks", [])
                retrieved_chunks.extend(chunks)

    return {
        "tool_results": tool_results,
        "web_sources": web_sources,
        "retrieved_chunks": retrieved_chunks,
        "steps": steps,
        "selected_tools": [],  # Clear executed tools
    }


def evaluate_node(state: AgentState) -> Dict[str, Any]:
    """Evaluate whether the agent's objective has been satisfied or additional tools are needed."""
    iteration = state.get("iteration", 1)
    max_iter = state.get("max_iterations", 3)
    remaining_tools = state.get("selected_tools", [])

    is_complete = (len(remaining_tools) == 0) or (iteration >= max_iter)
    return {
        "is_complete": is_complete,
    }


def should_execute_tools(state: AgentState) -> str:
    """Conditional routing based on whether tools are queued."""
    if state.get("selected_tools"):
        return "execute_tools"
    return END


def should_continue(state: AgentState) -> str:
    """Check if additional iterations are required."""
    if state.get("is_complete", False):
        return END
    if state.get("selected_tools"):
        return "execute_tools"
    return END


def create_agent_graph():
    """Builds and compiles the LangGraph Agent Workflow with working memory checkpoints."""
    workflow = StateGraph(AgentState)

    workflow.add_node("plan", plan_node)
    workflow.add_node("execute_tools", execute_tools_node)
    workflow.add_node("evaluate", evaluate_node)

    workflow.add_edge(START, "plan")
    workflow.add_conditional_edges(
        "plan",
        should_execute_tools,
        {
            "execute_tools": "execute_tools",
            END: END,
        },
    )
    workflow.add_edge("execute_tools", "evaluate")
    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "execute_tools": "execute_tools",
            END: END,
        },
    )

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


ruby_agent_graph = create_agent_graph()
