from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import Subject


DEFAULT_SUBJECTS = [
    {
        "name": "Mathematics",
        "description": "Calculus, Linear Algebra, Discrete Math, Probability & Statistics",
        "color": "#3b82f6",
        "icon": "calculator",
    },
    {
        "name": "Data Structures & Algorithms",
        "description": "Arrays, Trees, Graphs, Dynamic Programming, Complexity Analysis",
        "color": "#10b981",
        "icon": "binary",
    },
    {
        "name": "Computer Networks",
        "description": "OSI/TCP-IP models, Routing, Congestion Control, Protocols",
        "color": "#f59e0b",
        "icon": "network",
    },
    {
        "name": "Digital Logic & Computer Design",
        "description": "Boolean Algebra, Logic Gates, K-Maps, Sequential Circuits",
        "color": "#8b5cf6",
        "icon": "cpu",
    },
    {
        "name": "Operating Systems",
        "description": "Processes, Threads, Scheduling, Virtual Memory, File Systems",
        "color": "#ec4899",
        "icon": "terminal",
    },
]


async def seed_default_subjects(session: AsyncSession) -> None:
    """Seed initial academic subjects if the database is fresh."""
    result = await session.execute(select(Subject).limit(1))
    if result.scalars().first() is None:
        for subj_data in DEFAULT_SUBJECTS:
            subject = Subject(**subj_data)
            session.add(subject)
        await session.commit()
