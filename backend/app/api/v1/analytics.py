import logging
import json
from fastapi import APIRouter, Depends, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services.analytics.service import analytics_service

logger = logging.getLogger("ruby.api.analytics")

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", summary="Composite System Analytics Overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    docs = await analytics_service.get_document_analytics(db)
    study = await analytics_service.get_study_analytics(db)
    tokens = await analytics_service.get_token_and_cost_analytics(db)
    return {
        "documents": docs,
        "study": study,
        "tokens": tokens,
    }


@router.get("/documents", summary="Document & Storage Analytics")
async def get_document_analytics(db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_document_analytics(db)


@router.get("/study", summary="Academic & Spaced Repetition Study Analytics")
async def get_study_analytics(db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_study_analytics(db)


@router.get("/tokens", summary="AI Token Usage & Cost Estimates")
async def get_token_analytics(db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_token_and_cost_analytics(db)


@router.get("/diagnostics", summary="Sanitized System Diagnostic Report")
async def get_diagnostic_report(db: AsyncSession = Depends(get_db)):
    return await analytics_service.generate_sanitized_diagnostic_report(db)


@router.get("/diagnostics/export", summary="Export Sanitized Diagnostics JSON")
async def export_diagnostic_report(db: AsyncSession = Depends(get_db)):
    report = await analytics_service.generate_sanitized_diagnostic_report(db)
    content = json.dumps(report, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="ruby_sanitized_diagnostics.json"'},
    )
