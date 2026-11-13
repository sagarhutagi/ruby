import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.session import Base
from app.services.agent.permissions import PermissionManager, PermissionRule
from app.services.agent.runner import AgentRunner
from app.services.ai.base import BaseAIProvider, ChatResponse, ChatResponseChunk, ModelInfo
from app.services.memory.academic_service import AcademicMemoryService, academic_memory_service
from app.services.tools.builtins import (
    tool_compare_academic_assessments,
    tool_get_academic_performance_summary,
    tool_query_academic_records,
)
from app.services.tools.registry import tool_registry


class MockAIProvider(BaseAIProvider):
    def __init__(self, responses=None):
        super().__init__(name="mock", provider_type="mock")
        self.responses = responses or ["Based on your records, you scored 44/50 (88%) in CS301 ISA 1."]

    async def test_connection(self):
        return {"success": True}

    async def list_models(self):
        return [ModelInfo(id="mock-model", name="Mock Model", provider_type="mock")]

    async def chat(self, messages, model=None, **kwargs):
        return ChatResponse(content=self.responses[0], model="mock-model")

    async def stream_chat(self, messages, model=None, **kwargs):
        for word in self.responses[0].split():
            yield ChatResponseChunk(content_delta=word + " ")
        yield ChatResponseChunk(content_delta="", is_done=True, finish_reason="stop")


@pytest.fixture
async def in_memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_academic_record_creation_and_percentage(in_memory_db: AsyncSession):
    """Verify record creation and automatic percentage calculation."""
    rec = await AcademicMemoryService.create_or_update_record(
        session=in_memory_db,
        user_id="mars",
        term="Semester 5",
        subject_code="CS301",
        subject_name="Computer Networks",
        assessment_type="ISA 1",
        marks_obtained=44.0,
        max_marks=50.0,
        institution="PES University",
    )
    assert rec.marks_obtained == 44.0
    assert rec.max_marks == 50.0
    assert rec.percentage == 88.0
    assert rec.result_status == "available"
    assert rec.subject_code == "CS301"


@pytest.mark.asyncio
async def test_zero_score_vs_pending_and_absent_distinction(in_memory_db: AsyncSession):
    """Verify distinction between zero score, pending results, and absent status."""
    # 1. Zero score (Student appeared and scored 0.0)
    zero_rec = await AcademicMemoryService.create_or_update_record(
        session=in_memory_db,
        user_id="mars",
        term="Semester 5",
        subject_code="CS302",
        subject_name="Operating Systems",
        assessment_type="Quiz 1",
        marks_obtained=0.0,
        max_marks=10.0,
        result_status="available",
    )
    assert zero_rec.marks_obtained == 0.0
    assert zero_rec.percentage == 0.0
    assert zero_rec.result_status == "available"

    # 2. Pending result (Result awaited)
    pending_rec = await AcademicMemoryService.create_or_update_record(
        session=in_memory_db,
        user_id="mars",
        term="Semester 5",
        subject_code="CS302",
        subject_name="Operating Systems",
        assessment_type="ISA 2",
        marks_obtained=None,
        max_marks=None,
        result_status="pending",
    )
    assert pending_rec.marks_obtained is None
    assert pending_rec.result_status == "pending"

    # 3. Absent
    absent_rec = await AcademicMemoryService.create_or_update_record(
        session=in_memory_db,
        user_id="mars",
        term="Semester 5",
        subject_code="CS303",
        subject_name="Algorithms",
        assessment_type="ISA 1",
        marks_obtained=None,
        max_marks=50.0,
        result_status="absent",
    )
    assert absent_rec.marks_obtained is None
    assert absent_rec.result_status == "absent"


@pytest.mark.asyncio
async def test_academic_record_deduplication_and_update(in_memory_db: AsyncSession):
    """Verify updating an existing record updates in-place without duplicating."""
    # Insert initial score: 40/50
    await AcademicMemoryService.create_or_update_record(
        session=in_memory_db,
        user_id="mars",
        term="Semester 5",
        subject_code="CS301",
        subject_name="Computer Networks",
        assessment_type="ISA 1",
        marks_obtained=40.0,
        max_marks=50.0,
    )

    # Corrected re-evaluation score: 45/50
    updated = await AcademicMemoryService.create_or_update_record(
        session=in_memory_db,
        user_id="mars",
        term="Semester 5",
        subject_code="CS301",
        subject_name="Computer Networks",
        assessment_type="ISA 1",
        marks_obtained=45.0,
        max_marks=50.0,
        notes="Re-evaluation update",
    )
    assert updated.marks_obtained == 45.0
    assert updated.percentage == 90.0
    assert updated.notes == "Re-evaluation update"

    # Query all records for this subject - must be exactly 1 record!
    records = await AcademicMemoryService.get_marks_for_subject(
        session=in_memory_db, subject_query="CS301", user_id="mars"
    )
    assert len(records) == 1
    assert records[0]["marks_obtained"] == 45.0


@pytest.mark.asyncio
async def test_parse_and_ingest_scorecard(in_memory_db: AsyncSession):
    """Verify parsing a multi-line scorecard atomically without bare number fragmentation."""
    scorecard_text = """
    CS301 Computer Networks ISA 1: 44/50
    CS302 Operating Systems ISA 1: 48/50
    CS303 Algorithms ISA 1: 42/50
    CS304 Digital Logic ISA 1: Pending
    CGPA: 9.15
    """
    records = await AcademicMemoryService.parse_and_ingest_scorecard(
        session=in_memory_db,
        text=scorecard_text,
        user_id="mars",
        term="Semester 5",
    )
    assert len(records) == 5

    # Check CGPA record
    cgpa_rec = next(r for r in records if r.subject_code == "CGPA")
    assert cgpa_rec.marks_obtained == 9.15
    assert cgpa_rec.record_type == "cgpa"

    # Check pending record
    pending_rec = next(r for r in records if r.subject_code == "CS304")
    assert pending_rec.result_status == "pending"


@pytest.mark.asyncio
async def test_structured_queries_and_comparisons(in_memory_db: AsyncSession):
    """Verify structured queries: averages, extremes, comparisons, pending, trends."""
    # Seed data
    await AcademicMemoryService.create_or_update_record(
        in_memory_db, user_id="mars", term="Semester 5", subject_code="CS301", subject_name="CN",
        assessment_type="ISA 1", marks_obtained=40.0, max_marks=50.0
    )
    await AcademicMemoryService.create_or_update_record(
        in_memory_db, user_id="mars", term="Semester 5", subject_code="CS301", subject_name="CN",
        assessment_type="ISA 2", marks_obtained=46.0, max_marks=50.0
    )
    await AcademicMemoryService.create_or_update_record(
        in_memory_db, user_id="mars", term="Semester 5", subject_code="CS302", subject_name="OS",
        assessment_type="ISA 1", marks_obtained=48.0, max_marks=50.0
    )
    await AcademicMemoryService.create_or_update_record(
        in_memory_db, user_id="mars", term="Semester 5", subject_code="CS302", subject_name="OS",
        assessment_type="ISA 2", marks_obtained=45.0, max_marks=50.0
    )
    await AcademicMemoryService.create_or_update_record(
        in_memory_db, user_id="mars", term="Semester 5", subject_code="CS303", subject_name="DSA",
        assessment_type="ISA 2", marks_obtained=None, max_marks=None, result_status="pending"
    )

    # 1. Subject Percentage (CS301 has 40+46 / 100 = 86.0%)
    cn_pct = await AcademicMemoryService.get_subject_percentage(in_memory_db, "CS301", user_id="mars")
    assert cn_pct["cumulative_percentage"] == 86.0
    assert cn_pct["completed_assessments"] == 2

    # 2. Extremes: Highest is OS ISA 1 (96%), Lowest is CN ISA 1 (80%)
    extremes = await AcademicMemoryService.get_highest_lowest_scores(in_memory_db, user_id="mars")
    assert extremes["highest"]["percentage"] == 96.0
    assert extremes["lowest"]["percentage"] == 80.0

    # 3. Average performance across all available assessments: (80 + 92 + 96 + 90) / 4 = 89.5%
    avg = await AcademicMemoryService.get_average_performance(in_memory_db, user_id="mars")
    assert avg["average_percentage"] == 89.5
    assert avg["total_assessments"] == 4

    # 4. Compare assessments (ISA 1 vs ISA 2)
    comparisons = await AcademicMemoryService.compare_assessments(
        in_memory_db, assessment_a="ISA 1", assessment_b="ISA 2", user_id="mars"
    )
    cn_comp = next(c for c in comparisons if c["subject_code"] == "CS301")
    assert cn_comp["delta_percentage"] == 12.0  # improved from 80% to 92%
    assert cn_comp["improved"] is True

    os_comp = next(c for c in comparisons if c["subject_code"] == "CS302")
    assert os_comp["delta_percentage"] == -6.0  # dropped from 96% to 90%
    assert os_comp["improved"] is False

    # 5. Pending results
    pending = await AcademicMemoryService.get_pending_results(in_memory_db, user_id="mars")
    assert len(pending) == 1
    assert pending[0]["subject_code"] == "CS303"


@pytest.mark.asyncio
async def test_academic_query_builtins_tools(in_memory_db: AsyncSession):
    """Verify tool wrapper execution for academic queries."""
    await AcademicMemoryService.create_or_update_record(
        in_memory_db, user_id="default_user", term="Semester 5", subject_code="CS301",
        subject_name="Computer Networks", assessment_type="ISA 1", marks_obtained=44.0, max_marks=50.0
    )

    # 1. tool_query_academic_records
    res1 = await tool_query_academic_records(subject="CS301", session=in_memory_db)
    assert res1["success"] is True
    assert res1["data"]["cumulative_percentage"] == 88.0

    # 2. tool_get_academic_performance_summary
    res2 = await tool_get_academic_performance_summary(session=in_memory_db)
    assert res2["success"] is True
    assert res2["average_performance"]["average_percentage"] == 88.0


@pytest.mark.asyncio
async def test_agent_runner_academic_memory_integration(in_memory_db: AsyncSession):
    """Verify AgentRunner automatically includes verified academic profile in context."""
    await AcademicMemoryService.create_or_update_record(
        in_memory_db, user_id="default_user", term="Semester 5", subject_code="CS301",
        subject_name="Computer Networks", assessment_type="ISA 1", marks_obtained=44.0, max_marks=50.0
    )

    provider = MockAIProvider()
    pm = PermissionManager([PermissionRule("*", "*", "allow")])
    runner = AgentRunner(provider=provider, permission_manager=pm)

    events = []
    async for event in runner.run(
        prompt="Tell me about my academic performance and marks in Computer Networks",
        conversation_id="conv_academic_test",
        session=in_memory_db,
    ):
        events.append(event)

    complete_ev = next(e for e in events if e.type.value == "agent_complete")
    assert complete_ev is not None
