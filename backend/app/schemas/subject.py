from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    subject_id: Optional[str] = None
    name: str = Field(..., max_length=100)
    description: Optional[str] = None


class CollectionUpdate(BaseModel):
    subject_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None


class CollectionResponse(BaseModel):
    id: str
    subject_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


class SubjectCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    color: str = Field(default="#6366f1")
    icon: Optional[str] = Field(default="book")


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class SubjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    color: str
    icon: Optional[str] = None
    collection_count: int = 0
    document_count: int = 0
    created_at: datetime
    updated_at: datetime
