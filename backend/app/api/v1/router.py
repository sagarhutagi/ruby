from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.providers import router as providers_router
from app.api.v1.system import router as system_router
from app.api.v1.subjects import router as subjects_router
from app.api.v1.collections import router as collections_router
from app.api.v1.documents import router as documents_router
from app.api.v1.retrieval import router as retrieval_router
from app.api.v1.chat import router as chat_router
from app.api.v1.memories import router as memories_router, memory_alias_router
from app.api.v1.academic import router as academic_router
from app.api.v1.graph import router as graph_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.permissions import router as permissions_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(providers_router)
api_v1_router.include_router(system_router)
api_v1_router.include_router(subjects_router)
api_v1_router.include_router(collections_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(retrieval_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(memories_router)
api_v1_router.include_router(memory_alias_router)
api_v1_router.include_router(academic_router)
api_v1_router.include_router(graph_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(permissions_router)




