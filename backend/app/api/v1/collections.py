from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.session import get_db
from app.models.entities import Collection, Document
from app.schemas.subject import CollectionCreate, CollectionUpdate, CollectionResponse

router = APIRouter(prefix="/collections", tags=["Document Collections"])


@router.get("", response_model=List[CollectionResponse], summary="List Collections")
async def list_collections(
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Collection)
    if subject_id:
        stmt = stmt.where(Collection.subject_id == subject_id)
    stmt = stmt.order_by(Collection.name)
    result = await db.execute(stmt)
    collections = result.scalars().all()

    responses = []
    for c in collections:
        doc_count = await db.scalar(select(func.count(Document.id)).where(Document.collection_id == c.id)) or 0
        responses.append(
            CollectionResponse(
                id=c.id,
                subject_id=c.subject_id,
                name=c.name,
                description=c.description,
                document_count=doc_count,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return responses


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED, summary="Create Collection")
async def create_collection(payload: CollectionCreate, db: AsyncSession = Depends(get_db)):
    collection = Collection(
        subject_id=payload.subject_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    return CollectionResponse(
        id=collection.id,
        subject_id=collection.subject_id,
        name=collection.name,
        description=collection.description,
        document_count=0,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


@router.put("/{collection_id}", response_model=CollectionResponse, summary="Update Collection")
async def update_collection(collection_id: str, payload: CollectionUpdate, db: AsyncSession = Depends(get_db)):
    collection = await db.scalar(select(Collection).where(Collection.id == collection_id))
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(collection, field, val)

    await db.commit()
    await db.refresh(collection)
    doc_count = await db.scalar(select(func.count(Document.id)).where(Document.collection_id == collection_id)) or 0
    return CollectionResponse(
        id=collection.id,
        subject_id=collection.subject_id,
        name=collection.name,
        description=collection.description,
        document_count=doc_count,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Collection")
async def delete_collection(collection_id: str, db: AsyncSession = Depends(get_db)):
    collection = await db.scalar(select(Collection).where(Collection.id == collection_id))
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")
    await db.delete(collection)
    await db.commit()
    return None
