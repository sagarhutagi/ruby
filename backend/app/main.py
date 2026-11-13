import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.database.session import init_db, engine, async_session_factory
from app.database.fts import init_fts
from app.database.seed import seed_default_subjects
from app.api.v1.router import api_v1_router

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ruby")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting %s v%s...", settings.app_name, settings.version)
    settings.ensure_directories()
    await init_db()

    async with async_session_factory() as session:
        await init_fts(session)
        await seed_default_subjects(session)

    logger.info("Ruby backend initialized successfully on %s:%d", settings.host, settings.port)
    yield
    # Shutdown
    logger.info("Shutting down Ruby backend...")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Personal Academic Intelligence & Knowledge Management System",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enforce localhost CORS restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Root
@app.get("/api")
@app.get("/api/v1")
async def api_root():
    return {
        "app": "Ruby",
        "status": "online",
        "version": settings.version,
        "docs": "/docs",
        "health": "/api/v1/health",
    }

# Mount API routes
app.include_router(api_v1_router)

# Mount frontend production build if available
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="static-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "app": "Ruby",
            "status": "online",
            "docs": "/docs",
            "api_v1": "/api/v1",
        }
