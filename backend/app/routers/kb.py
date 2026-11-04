from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schema import KBDocument
from app.routers.auth import get_current_admin
from app.ai.rag import reindex_all_knowledge

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])

class KBDocCreate(BaseModel):
    doc_type: str  # faq, policy, general
    title: str
    content: str
    is_active: bool = True

class KBDocUpdate(BaseModel):
    doc_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None

class KBDocResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_type: str
    title: str
    content: str
    is_active: bool

@router.get("", response_model=List[KBDocResponse])
async def list_kb_documents(
    doc_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(KBDocument).order_by(KBDocument.id.desc())
    if doc_type:
        stmt = stmt.where(KBDocument.doc_type == doc_type.strip())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("", response_model=KBDocResponse, status_code=status.HTTP_201_CREATED)
async def create_kb_document(
    data: KBDocCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    doc = KBDocument(
        doc_type=data.doc_type.strip().lower(),
        title=data.title.strip(),
        content=data.content.strip(),
        is_active=data.is_active
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc

@router.put("/{doc_id}", response_model=KBDocResponse)
async def update_kb_document(
    doc_id: int,
    data: KBDocUpdate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(KBDocument).where(KBDocument.id == doc_id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(doc, field, val)

    await db.commit()
    await db.refresh(doc)
    return doc

@router.delete("/{doc_id}")
async def delete_kb_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(KBDocument).where(KBDocument.id == doc_id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.delete(doc)
    await db.commit()
    return {"status": "success", "message": f"Document #{doc_id} deleted"}

@router.post("/reindex")
async def trigger_reindex(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Chunks all active catalog products and knowledge base documents,
    generates embeddings, and stores them in pgvector chunks table.
    """
    result = await reindex_all_knowledge(db)
    return result
