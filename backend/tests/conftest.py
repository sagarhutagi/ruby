import pytest_asyncio
from app.core.config import settings
from app.database.session import init_db, async_session_factory
from app.database.fts import init_fts
from app.database.seed import seed_default_subjects


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Ensure data directories, database tables, FTS5 virtual tables, and default seed data are initialized."""
    settings.ensure_directories()
    await init_db()
    async with async_session_factory() as session:
        await init_fts(session)
        await seed_default_subjects(session)
    yield
