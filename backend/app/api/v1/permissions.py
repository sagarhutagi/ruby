import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.agent.permissions import permission_manager

logger = logging.getLogger("ruby.api.permissions")

router = APIRouter(prefix="/permissions", tags=["permissions"])


class PermissionReplyRequest(BaseModel):
    request_id: str
    approved: bool
    remember: bool = False


@router.get("/pending", summary="Get Pending Permission Requests")
async def get_pending_permissions():
    requests = permission_manager.get_pending_requests()
    return [req.to_dict() for req in requests]


@router.post("/reply", summary="Reply to Permission Request")
async def reply_permission(body: PermissionReplyRequest):
    success = permission_manager.resolve_approval(
        request_id=body.request_id,
        approved=body.approved,
        remember=body.remember,
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Permission request '{body.request_id}' not found or already resolved.",
        )
    logger.info(
        "Resolved permission request %s -> approved=%s (remember=%s)",
        body.request_id,
        body.approved,
        body.remember,
    )
    return {"success": True, "request_id": body.request_id, "approved": body.approved}
