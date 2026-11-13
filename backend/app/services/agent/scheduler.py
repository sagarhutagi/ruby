from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.agent.cancellation import CancellationToken
from app.services.agent.dag import TaskDAG, TaskNode, TaskStatus
from app.services.agent.events import AgentEvent, EventType
from app.services.agent.permissions import PermissionManager, permission_manager as default_pm
from app.services.tools.registry import ToolRegistry, tool_registry as default_tr

logger = logging.getLogger("ruby.agent.scheduler")


class DAGScheduler:
    """
    Hierarchical Task DAG Scheduler & Parallel Executor.
    Executes independent tasks concurrently up to AGENT_PARALLELISM_LIMIT,
    evaluates intermediate outcomes, handles retries with backoff,
    supports dynamic replanning, pause/resume, and cooperative cancellation.
    """

    def __init__(
        self,
        dag: TaskDAG,
        tool_registry: Optional[ToolRegistry] = None,
        permission_manager: Optional[PermissionManager] = None,
        parallelism_limit: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.dag = dag
        self.tool_registry = tool_registry or default_tr
        self.permission_manager = permission_manager or default_pm
        self.parallelism_limit = parallelism_limit or settings.agent_parallelism_limit
        self.max_retries = max_retries or settings.agent_retry_limit
        self._semaphore = asyncio.Semaphore(self.parallelism_limit)
        self._is_paused = False

    def pause(self) -> None:
        self._is_paused = True
        logger.info("DAGScheduler paused for conversation %s", self.dag.conversation_id)

    def resume(self) -> None:
        self._is_paused = False
        logger.info("DAGScheduler resumed for conversation %s", self.dag.conversation_id)

    async def execute(
        self,
        session: Optional[AsyncSession] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Executes the DAG, yielding AgentEvents for each state transition,
        tool execution, dynamic replanning event, or failure.
        """
        token = cancellation_token or CancellationToken()

        # Initial persistence
        if session:
            await self.dag.persist(session)

        while not self.dag.is_complete():
            token.check_cancelled()

            if self._is_paused:
                logger.info("Scheduler is paused; yielding execution control.")
                break

            ready_tasks = self.dag.get_ready_tasks()
            if not ready_tasks:
                # Check if there are any remaining running or blocked tasks
                uncompleted = [
                    n for n in self.dag.nodes.values()
                    if n.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
                ]
                if not uncompleted:
                    break
                # Deadlock or waiting for external approval
                await asyncio.sleep(0.1)
                continue

            # Execute batch of ready tasks bounded by parallelism
            tasks_to_run = ready_tasks[:self.parallelism_limit]
            for node in tasks_to_run:
                node.status = TaskStatus.RUNNING

            # Run batch concurrently using bounded semaphore
            coroutines = [
                self._execute_single_task(node, session, token)
                for node in tasks_to_run
            ]

            # We process task results as they complete
            for coro in asyncio.as_completed(coroutines):
                token.check_cancelled()
                events = await coro
                for ev in events:
                    yield ev

                if session:
                    await self.dag.persist(session)

        # Emit completion summary event
        yield AgentEvent(
            type=EventType.TASK_STATE_CHANGE,
            conversation_id=self.dag.conversation_id,
            payload={
                "status": "complete" if not self.dag.has_failures() else "failed_with_errors",
                "total_tasks": len(self.dag.nodes),
                "completed_tasks": sum(1 for n in self.dag.nodes.values() if n.status == TaskStatus.COMPLETED),
                "failed_tasks": sum(1 for n in self.dag.nodes.values() if n.status == TaskStatus.FAILED),
            },
        )

    async def _execute_single_task(
        self,
        node: TaskNode,
        session: Optional[AsyncSession],
        token: CancellationToken,
    ) -> List[AgentEvent]:
        """Executes a single TaskNode with permission gates, retries, and dynamic replanning."""
        events: List[AgentEvent] = []
        async with self._semaphore:
            token.check_cancelled()

            # Mark running
            node.status = TaskStatus.RUNNING
            events.append(AgentEvent(
                type=EventType.TASK_STATE_CHANGE,
                conversation_id=self.dag.conversation_id,
                task_id=node.id,
                payload={"task_id": node.id, "title": node.title, "status": "running"},
            ))

            t_start = time.perf_counter()

            # If node has no tool, treat as a coordination / milestone task
            if not node.tool_name:
                node.status = TaskStatus.COMPLETED
                node.execution_time_ms = round((time.perf_counter() - t_start) * 1000, 2)
                node.result = {"message": f"Milestone '{node.title}' reached."}
                events.append(AgentEvent(
                    type=EventType.TASK_STATE_CHANGE,
                    conversation_id=self.dag.conversation_id,
                    task_id=node.id,
                    payload={"task_id": node.id, "title": node.title, "status": "completed"},
                ))
                return events

            # Permission Gate
            effect = self.permission_manager.evaluate(node.tool_name)
            req_id = f"perm_task_{uuid.uuid4().hex[:8]}"

            if effect == "ask":
                node.status = TaskStatus.WAITING_APPROVAL
                events.append(AgentEvent(
                    type=EventType.PERMISSION_REQUEST,
                    conversation_id=self.dag.conversation_id,
                    task_id=node.id,
                    payload={
                        "request_id": req_id,
                        "tool_name": node.tool_name,
                        "arguments": node.tool_arguments,
                        "task_id": node.id,
                        "message": f"Subtask '{node.title}' requires approval to run {node.tool_name}.",
                    },
                ))

            is_allowed = await self.permission_manager.check_or_request_approval(
                tool_name=node.tool_name,
                arguments=node.tool_arguments,
                request_id=req_id,
            )

            if not is_allowed:
                node.status = TaskStatus.FAILED
                node.error = "Subtask rejected by user or denied by permission policy."
                events.append(AgentEvent(
                    type=EventType.TASK_STATE_CHANGE,
                    conversation_id=self.dag.conversation_id,
                    task_id=node.id,
                    payload={"task_id": node.id, "status": "failed", "error": node.error},
                ))
                return events

            # Execute tool
            exec_res = await self.tool_registry.execute(
                name=node.tool_name,
                arguments=node.tool_arguments,
                session=session,
            )
            node.execution_time_ms = round((time.perf_counter() - t_start) * 1000, 2)

            events.append(AgentEvent(
                type=EventType.OBSERVATION_TOOL_RESULT,
                conversation_id=self.dag.conversation_id,
                task_id=node.id,
                payload={
                    "tool_name": node.tool_name,
                    "success": exec_res.success,
                    "data": exec_res.data,
                    "error": exec_res.error,
                    "execution_time_ms": node.execution_time_ms,
                },
            ))

            # Result Evaluation & Retry Logic
            if exec_res.success:
                node.status = TaskStatus.COMPLETED
                node.result = {"data": exec_res.data}

                # Check Dynamic Replanning Hook: Did this task spawn subtasks?
                if isinstance(exec_res.data, dict) and "spawn_subtasks" in exec_res.data:
                    new_subtasks = exec_res.data.get("spawn_subtasks", [])
                    for sub in new_subtasks:
                        st_title = sub.get("title", "Dynamic Subtask")
                        st_tool = sub.get("tool_name")
                        st_args = sub.get("tool_arguments", {})
                        new_node = self.dag.add_task(
                            title=st_title,
                            tool_name=st_tool,
                            tool_arguments=st_args,
                            parent_task_id=node.id,
                            depends_on=[node.id],
                        )
                        events.append(AgentEvent(
                            type=EventType.TASK_STATE_CHANGE,
                            conversation_id=self.dag.conversation_id,
                            task_id=new_node.id,
                            payload={
                                "task_id": new_node.id,
                                "title": st_title,
                                "status": "pending",
                                "parent_task_id": node.id,
                            },
                        ))

                events.append(AgentEvent(
                    type=EventType.TASK_STATE_CHANGE,
                    conversation_id=self.dag.conversation_id,
                    task_id=node.id,
                    payload={"task_id": node.id, "status": "completed"},
                ))
            else:
                # Failure & Retry evaluation
                if node.retry_count < node.max_retries:
                    node.retry_count += 1
                    backoff_delay = 0.1 * (2 ** node.retry_count)
                    logger.warning(
                        "Task '%s' failed (attempt %d/%d). Retrying in %.2fs: %s",
                        node.title, node.retry_count, node.max_retries, backoff_delay, exec_res.error
                    )
                    await asyncio.sleep(backoff_delay)
                    node.status = TaskStatus.READY  # Put back in queue
                    events.append(AgentEvent(
                        type=EventType.TASK_STATE_CHANGE,
                        conversation_id=self.dag.conversation_id,
                        task_id=node.id,
                        payload={
                            "task_id": node.id,
                            "status": "ready",
                            "retry_count": node.retry_count,
                            "error": exec_res.error,
                        },
                    ))
                else:
                    node.status = TaskStatus.FAILED
                    node.error = exec_res.error or "Task failed after exhausting retry attempts."
                    events.append(AgentEvent(
                        type=EventType.TASK_STATE_CHANGE,
                        conversation_id=self.dag.conversation_id,
                        task_id=node.id,
                        payload={"task_id": node.id, "status": "failed", "error": node.error},
                    ))

            return events
