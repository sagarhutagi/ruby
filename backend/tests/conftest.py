import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.core.config import settings
from app.database.session import init_db, async_session_factory
from app.database.fts import init_fts
from app.database.seed import seed_default_subjects
from app.main import app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Ensure data directories, database tables, FTS5 virtual tables, and default seed data are initialized."""
    settings.ensure_directories()
    await init_db()
    async with async_session_factory() as session:
        await init_fts(session)
        await seed_default_subjects(session)
    yield


@pytest_asyncio.fixture
async def session():
    """Provides an isolated async database session for testing."""
    async with async_session_factory() as sess:
        yield sess


@pytest_asyncio.fixture
async def client():
    """Provides an AsyncClient for testing HTTP endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

