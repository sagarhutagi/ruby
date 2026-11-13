from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.session import get_db
from app.models.entities import Subject, Collection, Document
from app.schemas.subject import SubjectCreate, SubjectUpdate, SubjectResponse

router = APIRouter(prefix="/subjects", tags=["Academic Subjects"])


@router.get("", response_model=List[SubjectResponse], summary="List All Subjects")
async def list_subjects(db: AsyncSession = Depends(get_db)):
    stmt = select(Subject).order_by(Subject.name)
    result = await db.execute(stmt)
    subjects = result.scalars().all()

    responses = []
    for s in subjects:
        col_count = await db.scalar(select(func.count(Collection.id)).where(Collection.subject_id == s.id)) or 0
        doc_count = await db.scalar(select(func.count(Document.id)).where(Document.subject_id == s.id)) or 0
        responses.append(
            SubjectResponse(
                id=s.id,
                name=s.name,
                description=s.description,
                color=s.color,
                icon=s.icon,
                collection_count=col_count,
                document_count=doc_count,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
        )
    return responses


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED, summary="Create Subject")
async def create_subject(payload: SubjectCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(Subject).where(Subject.name == payload.name))
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Subject '{payload.name}' already exists.")

    subject = Subject(
        name=payload.name,
        description=payload.description,
        color=payload.color,
        icon=payload.icon,
    )
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return SubjectResponse(
        id=subject.id,
        name=subject.name,
        description=subject.description,
        color=subject.color,
        icon=subject.icon,
        collection_count=0,
        document_count=0,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
    )


@router.get("/{subject_id}", response_model=SubjectResponse, summary="Get Subject Details")
async def get_subject(subject_id: str, db: AsyncSession = Depends(get_db)):
    subject = await db.scalar(select(Subject).where(Subject.id == subject_id))
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    col_count = await db.scalar(select(func.count(Collection.id)).where(Collection.subject_id == subject_id)) or 0
    doc_count = await db.scalar(select(func.count(Document.id)).where(Document.subject_id == subject_id)) or 0
    return SubjectResponse(
        id=subject.id,
        name=subject.name,
        description=subject.description,
        color=subject.color,
        icon=subject.icon,
        collection_count=col_count,
        document_count=doc_count,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
    )


@router.put("/{subject_id}", response_model=SubjectResponse, summary="Update Subject")
async def update_subject(subject_id: str, payload: SubjectUpdate, db: AsyncSession = Depends(get_db)):
    subject = await db.scalar(select(Subject).where(Subject.id == subject_id))
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(subject, field, val)

    await db.commit()
    await db.refresh(subject)
    col_count = await db.scalar(select(func.count(Collection.id)).where(Collection.subject_id == subject_id)) or 0
    doc_count = await db.scalar(select(func.count(Document.id)).where(Document.subject_id == subject_id)) or 0
    return SubjectResponse(
        id=subject.id,
        name=subject.name,
        description=subject.description,
        color=subject.color,
        icon=subject.icon,
        collection_count=col_count,
        document_count=doc_count,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
    )


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Subject")
async def delete_subject(subject_id: str, db: AsyncSession = Depends(get_db)):
    subject = await db.scalar(select(Subject).where(Subject.id == subject_id))
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")
    await db.delete(subject)
    await db.commit()
    return None
