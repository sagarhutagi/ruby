from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.database.session import get_db
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["Health & Status"])


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Probe",
    description="Returns server status, database connectivity, and filesystem accessibility.",
)
async def check_health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    db_connected = False
    try:
        result = await db.execute(text("SELECT 1;"))
        if result.scalar() == 1:
            db_connected = True
    except Exception:
        db_connected = False

    storage_ok = settings.data_dir.exists() and os_can_write(settings.data_dir)

    overall_status = "healthy" if (db_connected and storage_ok) else "degraded"

    return HealthResponse(
        status=overall_status,
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        database_connected=db_connected,
        storage_accessible=storage_ok,
        data_directory=str(settings.data_dir.resolve()),
        timestamp=datetime.now(timezone.utc),
    )


def os_can_write(path) -> bool:
    try:
        test_file = path / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True
    except Exception:
        return False
