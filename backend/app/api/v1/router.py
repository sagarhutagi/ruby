from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.providers import router as providers_router
from app.api.v1.system import router as system_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(providers_router)
api_v1_router.include_router(system_router)
