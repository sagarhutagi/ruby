from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AgentTask, AgentTaskDependency

logger = logging.getLogger("ruby.agent.dag")


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskNode:
    id: str
    title: str
    description: Optional[str] = None
    mode: str = "auto"
    tool_name: Optional[str] = None
    tool_arguments: Dict[str, Any] = field(default_factory=dict)
    parent_task_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    depends_on: Set[str] = field(default_factory=set)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "mode": self.mode,
            "tool_name": self.tool_name,
            "tool_arguments": self.tool_arguments,
            "parent_task_id": self.parent_task_id,
            "status": self.status.value if isinstance(self.status, Enum) else str(self.status),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "depends_on": list(self.depends_on),
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


class TaskDAG:
    """
    Directed Acyclic Graph (DAG) for Hierarchical Task Planning and Execution.
    Supports topological sorting, cycle detection, parallel dispatch resolution,
    dynamic replanning, and persistent SQLite synchronization.
    """

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.nodes: Dict[str, TaskNode] = {}

    def add_task(
        self,
        title: str,
        tool_name: Optional[str] = None,
        tool_arguments: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        task_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        mode: str = "auto",
        depends_on: Optional[List[str]] = None,
        max_retries: int = 3,
    ) -> TaskNode:
        t_id = task_id or str(uuid.uuid4())
        deps = set(depends_on) if depends_on else set()

        node = TaskNode(
            id=t_id,
            title=title,
            description=description,
            mode=mode,
            tool_name=tool_name,
            tool_arguments=tool_arguments or {},
            parent_task_id=parent_task_id,
            status=TaskStatus.READY if not deps else TaskStatus.PENDING,
            max_retries=max_retries,
            depends_on=deps,
        )
        self.nodes[t_id] = node
        self.validate_no_cycles()
        return node

    def add_dependency(self, task_id: str, depends_on_task_id: str) -> None:
        if task_id not in self.nodes:
            raise KeyError(f"Task '{task_id}' does not exist in DAG.")
        if depends_on_task_id not in self.nodes:
            raise KeyError(f"Prerequisite task '{depends_on_task_id}' does not exist in DAG.")

        self.nodes[task_id].depends_on.add(depends_on_task_id)
        # If it was ready but now has dependencies, re-evaluate status
        if not self._all_dependencies_completed(task_id):
            if self.nodes[task_id].status == TaskStatus.READY:
                self.nodes[task_id].status = TaskStatus.PENDING

        self.validate_no_cycles()

    def _all_dependencies_completed(self, task_id: str) -> bool:
        deps = self.nodes[task_id].depends_on
        return all(
            dep_id in self.nodes and self.nodes[dep_id].status == TaskStatus.COMPLETED
            for dep_id in deps
        )

    def get_ready_tasks(self) -> List[TaskNode]:
        """Returns tasks whose dependencies are fully completed and are ready to execute."""
        ready: List[TaskNode] = []
        for t_id, node in self.nodes.items():
            if node.status in (TaskStatus.PENDING, TaskStatus.READY):
                if self._all_dependencies_completed(t_id):
                    node.status = TaskStatus.READY
                    ready.append(node)
        return ready

    def is_complete(self) -> bool:
        """True if all tasks in the DAG are finished (completed, failed, or cancelled)."""
        return all(
            n.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
            for n in self.nodes.values()
        )

    def has_failures(self) -> bool:
        return any(n.status == TaskStatus.FAILED for n in self.nodes.values())

    def validate_no_cycles(self) -> None:
        """Detects circular dependencies in the DAG using Depth-First Search."""
        visited: Dict[str, int] = {}  # 0 = unvisited, 1 = visiting, 2 = visited

        def dfs(node_id: str) -> None:
            visited[node_id] = 1
            node = self.nodes.get(node_id)
            if node:
                for dep in node.depends_on:
                    if dep not in self.nodes:
                        continue
                    if visited.get(dep, 0) == 1:
                        raise ValueError(f"Cycle detected in Task DAG involving '{node_id}' and '{dep}'")
                    if visited.get(dep, 0) == 0:
                        dfs(dep)
            visited[node_id] = 2

        for n_id in self.nodes:
            if visited.get(n_id, 0) == 0:
                dfs(n_id)

    def topological_sort(self) -> List[TaskNode]:
        """Returns nodes in topologically sorted execution order."""
        self.validate_no_cycles()
        in_degree = {n_id: len(node.depends_on) for n_id, node in self.nodes.items()}
        queue = [n_id for n_id, deg in in_degree.items() if deg == 0]
        order: List[TaskNode] = []

        while queue:
            curr_id = queue.pop(0)
            order.append(self.nodes[curr_id])

            for node in self.nodes.values():
                if curr_id in node.depends_on:
                    in_degree[node.id] -= 1
                    if in_degree[node.id] == 0:
                        queue.append(node.id)

        return order

    async def persist(self, session: AsyncSession) -> None:
        """Persists the full DAG state and dependency edges to SQLite."""
        for node in self.nodes.values():
            db_task = await session.get(AgentTask, node.id)
            if not db_task:
                db_task = AgentTask(
                    id=node.id,
                    conversation_id=self.conversation_id,
                    parent_task_id=node.parent_task_id,
                    title=node.title,
                    description=node.description,
                    mode=node.mode,
                    status=node.status.value,
                    retry_count=node.retry_count,
                    max_retries=node.max_retries,
                    tool_name=node.tool_name,
                    tool_arguments=node.tool_arguments,
                    result=node.result,
                    error=node.error,
                    execution_time_ms=node.execution_time_ms,
                )
                session.add(db_task)
            else:
                db_task.status = node.status.value
                db_task.retry_count = node.retry_count
                db_task.result = node.result
                db_task.error = node.error
                db_task.execution_time_ms = node.execution_time_ms

            # Sync dependencies
            for dep_id in node.depends_on:
                stmt = select(AgentTaskDependency).where(
                    AgentTaskDependency.task_id == node.id,
                    AgentTaskDependency.depends_on_task_id == dep_id,
                )
                res = await session.execute(stmt)
                if not res.scalar_one_or_none():
                    session.add(AgentTaskDependency(
                        task_id=node.id,
                        depends_on_task_id=dep_id,
                    ))

        await session.commit()

    @classmethod
    async def load_from_db(
        cls,
        session: AsyncSession,
        conversation_id: str,
        parent_task_id: Optional[str] = None,
    ) -> TaskDAG:
        """Reconstructs a TaskDAG from persistent SQLite records."""
        dag = cls(conversation_id=conversation_id)
        stmt = select(AgentTask).where(AgentTask.conversation_id == conversation_id)
        if parent_task_id:
            stmt = stmt.where(AgentTask.parent_task_id == parent_task_id)

        res = await session.execute(stmt)
        tasks = res.scalars().all()

        for t in tasks:
            node = TaskNode(
                id=t.id,
                title=t.title,
                description=t.description,
                mode=t.mode,
                tool_name=t.tool_name,
                tool_arguments=t.tool_arguments or {},
                parent_task_id=t.parent_task_id,
                status=TaskStatus(t.status),
                retry_count=t.retry_count,
                max_retries=t.max_retries,
                result=t.result,
                error=t.error,
                execution_time_ms=t.execution_time_ms,
            )
            dag.nodes[t.id] = node

        # Load dependency edges
        dep_stmt = select(AgentTaskDependency).where(
            AgentTaskDependency.task_id.in_([t.id for t in tasks])
        )
        dep_res = await session.execute(dep_stmt)
        deps = dep_res.scalars().all()
        for d in deps:
            if d.task_id in dag.nodes and d.depends_on_task_id in dag.nodes:
                dag.nodes[d.task_id].depends_on.add(d.depends_on_task_id)

        return dag
