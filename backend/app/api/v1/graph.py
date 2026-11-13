import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services.graph.service import knowledge_graph_service
from app.services.obsidian.exporter import obsidian_exporter

logger = logging.getLogger("ruby.api.graph")

router = APIRouter(prefix="/graph", tags=["graph"])


class NodeCreateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    node_type: str = Field(default="concept", description="subject, topic, concept, document, formula")
    description: Optional[str] = None
    subject_id: Optional[str] = None
    document_id: Optional[str] = None
    position_x: float = Field(default=0.0)
    position_y: float = Field(default=0.0)
    is_verified: bool = Field(default=True)


class NodeUpdateRequest(BaseModel):
    label: Optional[str] = None
    node_type: Optional[str] = None
    description: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    is_verified: Optional[bool] = None


class EdgeCreateRequest(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str = Field(
        default="RELATED_TO",
        description="PREREQUISITE_OF, RELATED_TO, EXPLAINED_IN, PART_OF, CONTRADICTS",
    )
    is_verified: bool = Field(default=True)


class ObsidianExportRequest(BaseModel):
    vault_path: str = Field(default="./data/obsidian_vault")
    subject_id: Optional[str] = None
    allow_overwrite: bool = Field(default=False)


@router.get("", summary="Get Knowledge Graph (Nodes and Edges)")
async def get_graph(
    subject_id: Optional[str] = None,
    node_type: Optional[str] = None,
    verified_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await knowledge_graph_service.get_graph(
        session=db,
        subject_id=subject_id,
        node_type=node_type,
        verified_only=verified_only,
    )


@router.post("/nodes", status_code=status.HTTP_201_CREATED, summary="Create Concept Node")
async def create_node(req: NodeCreateRequest, db: AsyncSession = Depends(get_db)):
    node = await knowledge_graph_service.create_node(
        session=db,
        label=req.label,
        node_type=req.node_type,
        description=req.description,
        subject_id=req.subject_id,
        document_id=req.document_id,
        position_x=req.position_x,
        position_y=req.position_y,
        is_verified=req.is_verified,
    )
    return {
        "id": node.id,
        "label": node.label,
        "node_type": node.node_type,
        "description": node.description,
        "subject_id": node.subject_id,
        "document_id": node.document_id,
        "position_x": node.position_x,
        "position_y": node.position_y,
        "is_verified": node.is_verified,
    }


@router.patch("/nodes/{node_id}", summary="Update Concept Node")
async def update_node(node_id: str, req: NodeUpdateRequest, db: AsyncSession = Depends(get_db)):
    updated = await knowledge_graph_service.update_node(
        session=db,
        node_id=node_id,
        label=req.label,
        node_type=req.node_type,
        description=req.description,
        position_x=req.position_x,
        position_y=req.position_y,
        is_verified=req.is_verified,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Node not found.")
    return {
        "id": updated.id,
        "label": updated.label,
        "node_type": updated.node_type,
        "description": updated.description,
        "position_x": updated.position_x,
        "position_y": updated.position_y,
        "is_verified": updated.is_verified,
    }


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Concept Node")
async def delete_node(node_id: str, db: AsyncSession = Depends(get_db)):
    success = await knowledge_graph_service.delete_node(session=db, node_id=node_id)
    if not success:
        raise HTTPException(status_code=404, detail="Node not found.")
    return None


@router.post("/edges", status_code=status.HTTP_201_CREATED, summary="Create Relationship Edge")
async def create_edge(req: EdgeCreateRequest, db: AsyncSession = Depends(get_db)):
    edge = await knowledge_graph_service.create_edge(
        session=db,
        source_id=req.source_id,
        target_id=req.target_id,
        relationship_type=req.relationship_type,
        is_verified=req.is_verified,
    )
    if not edge:
        raise HTTPException(
            status_code=400,
            detail="Cannot create edge. Ensure source and target nodes exist and are distinct.",
        )
    return {
        "id": edge.id,
        "source_id": edge.source_id,
        "target_id": edge.target_id,
        "relationship_type": edge.relationship_type,
        "is_verified": edge.is_verified,
    }


@router.delete("/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Edge")
async def delete_edge(edge_id: str, db: AsyncSession = Depends(get_db)):
    success = await knowledge_graph_service.delete_edge(session=db, edge_id=edge_id)
    if not success:
        raise HTTPException(status_code=404, detail="Edge not found.")
    return None


@router.get("/prerequisites/{node_id}", summary="Get Prerequisite Dependency Chain")
async def get_prerequisites(node_id: str, db: AsyncSession = Depends(get_db)):
    chain = await knowledge_graph_service.get_prerequisite_chain(session=db, target_node_id=node_id)
    if "error" in chain:
        raise HTTPException(status_code=404, detail=chain["error"])
    return chain


@router.post("/extract-from-document/{document_id}", summary="Extract Concepts and Relations from Document")
async def extract_from_document(document_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return await knowledge_graph_service.extract_concepts_from_document(
            session=db,
            document_id=document_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== OBSIDIAN EXPORT ENDPOINTS ====================

@router.post("/obsidian/preview", summary="Preview Obsidian Vault Export and Conflicts")
async def preview_obsidian_export(req: ObsidianExportRequest, db: AsyncSession = Depends(get_db)):
    return await obsidian_exporter.preview_export(
        session=db,
        vault_path=req.vault_path,
        subject_id=req.subject_id,
    )


@router.post("/obsidian/export", summary="Export Knowledge Graph to Obsidian Vault Folder")
async def export_to_obsidian_vault(req: ObsidianExportRequest, db: AsyncSession = Depends(get_db)):
    return await obsidian_exporter.export_to_vault(
        session=db,
        vault_path=req.vault_path,
        subject_id=req.subject_id,
        allow_overwrite=req.allow_overwrite,
    )


@router.get("/obsidian/export-zip", summary="Download Knowledge Graph as Obsidian Vault ZIP Archive")
async def export_obsidian_zip(subject_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    zip_buffer = await obsidian_exporter.create_vault_zip(session=db, subject_id=subject_id)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="ruby_obsidian_vault.zip"'},
    )
