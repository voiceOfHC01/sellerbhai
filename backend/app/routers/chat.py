from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.schema import Thread, Message
from app.ai.engine import process_chat_message
from app.routers.auth import get_current_admin

router = APIRouter(prefix="/chat", tags=["Test Chat & AI Engine"])

class TestChatRequest(BaseModel):
    message: str
    thread_id: Optional[int] = None
    customer_name: Optional[str] = "Customer"
    customer_phone: Optional[str] = "01711000000"

class TestChatResponse(BaseModel):
    reply: str
    detected_language: str
    retrieved_sources: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    handover_triggered: bool
    thread_status: str
    thread_id: int
    latency_ms: Optional[float] = None

class MessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_type: str
    content: str
    language: Optional[str]
    created_at: Any

@router.post("/test", response_model=TestChatResponse)
async def test_chat(
    data: TestChatRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Simulates customer incoming chat message.
    Executes language detection, semantic pgvector retrieval,
    tool calling (search, stock, policy, order drafting, human handover),
    and system grounding rules.
    """
    if not data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = await process_chat_message(
        db=db,
        customer_message=data.message.strip(),
        thread_id=data.thread_id,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone
    )
    return result

@router.get("/threads/{thread_id}/messages", response_model=List[MessageItem])
async def get_thread_messages(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(
        select(Message).where(Message.thread_id == thread_id).order_by(Message.id.asc())
    )
    return res.scalars().all()

@router.post("/threads/{thread_id}/reset")
async def reset_thread_status(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = res.scalars().first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread.status = "active"
    thread.handover_reason = None
    await db.commit()
    return {"status": "success", "message": f"Thread #{thread_id} reset to active status"}
