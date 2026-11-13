import asyncio
import time
from typing import List
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.session import Base
from app.services.agent.cancellation import CancellationToken
from app.services.agent.dag import TaskDAG, TaskNode, TaskStatus
from app.services.agent.events import AgentEvent, EventType
from app.services.agent.permissions import PermissionManager, PermissionRule
from app.services.agent.scheduler import DAGScheduler
from app.services.tools.registry import ToolRegistry


@pytest.fixture
async def in_memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def test_dag_topological_sort_and_dependencies():
    """Verify DAG topological sorting order."""
    dag = TaskDAG(conversation_id="conv_1")
    t1 = dag.add_task(title="Fetch Document", task_id="t1")
    t2 = dag.add_task(title="Analyze Content", task_id="t2", depends_on=["t1"])
    t3 = dag.add_task(title="Generate Summary", task_id="t3", depends_on=["t2"])

    order = dag.topological_sort()
    order_ids = [n.id for n in order]
    assert order_ids == ["t1", "t2", "t3"]


def test_dag_cycle_detection():
    """Verify circular dependencies are rejected with ValueError."""
    dag = TaskDAG(conversation_id="conv_1")
    dag.add_task(title="Task A", task_id="A")
    dag.add_task(title="Task B", task_id="B", depends_on=["A"])

    with pytest.raises(ValueError, match="Cycle detected"):
        dag.add_dependency("A", "B")


@pytest.mark.asyncio
async def test_dag_parallel_execution_of_independent_tasks():
    """Verify independent tasks execute concurrently."""
    dag = TaskDAG(conversation_id="conv_parallel")
    t1 = dag.add_task(title="Independent Task 1", tool_name="sleep_task", tool_arguments={"duration": 0.05})
    t2 = dag.add_task(title="Independent Task 2", tool_name="sleep_task", tool_arguments={"duration": 0.05})
    t3 = dag.add_task(title="Dependent Task", tool_name="summary_task", depends_on=[t1.id, t2.id])

    custom_tr = ToolRegistry()

    async def sleep_handler(duration: float = 0.05, **kwargs):
        await asyncio.sleep(duration)
        return {"status": "slept"}

    async def summary_handler(**kwargs):
        return {"summary": "all done"}

    custom_tr.register(name="sleep_task", description="", parameters={}, handler=sleep_handler)
    custom_tr.register(name="summary_task", description="", parameters={}, handler=summary_handler)

    pm = PermissionManager([PermissionRule("*", "*", "allow")])
    scheduler = DAGScheduler(dag=dag, tool_registry=custom_tr, permission_manager=pm, parallelism_limit=4)

    start = time.perf_counter()
    events: List[AgentEvent] = []
    async for event in scheduler.execute():
        events.append(event)
    duration = time.perf_counter() - start

    assert dag.is_complete()
    assert not dag.has_failures()
    assert t1.status == TaskStatus.COMPLETED
    assert t2.status == TaskStatus.COMPLETED
    assert t3.status == TaskStatus.COMPLETED

    # Since t1 and t2 ran concurrently (0.05s each), total time should be well under 0.15s
    assert duration < 0.25


@pytest.mark.asyncio
async def test_dag_persistence_and_reload(in_memory_db: AsyncSession):
    """Verify SQLite persistence and round-trip reloading of tasks and edges."""
    dag = TaskDAG(conversation_id="conv_persist")
    t1 = dag.add_task(title="Task 1", tool_name="tool_1", task_id="t1")
    t2 = dag.add_task(title="Task 2", tool_name="tool_2", task_id="t2", depends_on=["t1"])

    await dag.persist(in_memory_db)

    # Reload from database
    loaded_dag = await TaskDAG.load_from_db(in_memory_db, conversation_id="conv_persist")
    assert len(loaded_dag.nodes) == 2
    assert "t1" in loaded_dag.nodes
    assert "t2" in loaded_dag.nodes
    assert "t1" in loaded_dag.nodes["t2"].depends_on


@pytest.mark.asyncio
async def test_dag_retry_on_failure():
    """Verify failed tasks are retried up to max_retries with backoff."""
    dag = TaskDAG(conversation_id="conv_retry")
    attempts = 0

    custom_tr = ToolRegistry()

    async def flaky_handler(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise RuntimeError("Transient connection error")
        return {"result": "success on retry"}

    custom_tr.register(name="flaky_tool", description="", parameters={}, handler=flaky_handler)
    dag.add_task(title="Flaky Task", tool_name="flaky_tool", max_retries=3)

    pm = PermissionManager([PermissionRule("*", "*", "allow")])
    scheduler = DAGScheduler(dag=dag, tool_registry=custom_tr, permission_manager=pm)

    async for _ in scheduler.execute():
        pass

    assert attempts == 2
    assert dag.is_complete()
    assert not dag.has_failures()


@pytest.mark.asyncio
async def test_dag_dynamic_replanning():
    """Verify a task can dynamically spawn subtasks during execution."""
    dag = TaskDAG(conversation_id="conv_replan")

    custom_tr = ToolRegistry()

    async def parent_handler(**kwargs):
        return {
            "analysis": "requires deeper subtasks",
            "spawn_subtasks": [
                {"title": "Spawned Child 1", "tool_name": "child_tool", "tool_arguments": {"x": 1}},
                {"title": "Spawned Child 2", "tool_name": "child_tool", "tool_arguments": {"x": 2}},
            ],
        }

    async def child_handler(x: int = 0, **kwargs):
        return {"processed": x * 10}

    custom_tr.register(name="parent_tool", description="", parameters={}, handler=parent_handler)
    custom_tr.register(name="child_tool", description="", parameters={}, handler=child_handler)

    dag.add_task(title="Parent Planning Task", tool_name="parent_tool")

    pm = PermissionManager([PermissionRule("*", "*", "allow")])
    scheduler = DAGScheduler(dag=dag, tool_registry=custom_tr, permission_manager=pm)

    async for _ in scheduler.execute():
        pass

    assert len(dag.nodes) == 3
    assert all(n.status == TaskStatus.COMPLETED for n in dag.nodes.values())
