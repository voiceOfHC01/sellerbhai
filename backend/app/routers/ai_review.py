from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schema import AIRun, KBDocument, Thread, Message
from app.routers.auth import get_current_admin
from app.ai.rag import reindex_all_knowledge

router = APIRouter(prefix="/ai-review", tags=["AI Quality Review & Knowledge Corrections"])

class AIRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: Optional[int] = None
    message_id: Optional[int] = None
    user_message: Optional[str] = None
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    retrieved_chunks: Optional[Any] = None
    tool_calls: Optional[Any] = None
    raw_response: Optional[str] = None
    detected_language: Optional[str] = None
    model_name: Optional[str] = "gemini-1.5-flash"
    token_cost_usd: float = 0.0
    is_blocked: bool = False
    blocked_reason: Optional[str] = None
    prompt_version: str = "v1.1"
    corrected_reply: Optional[str] = None
    is_flagged_wrong: bool = False
    correction_notes: Optional[str] = None
    corrected_kb_doc_id: Optional[int] = None
    created_at: datetime

class MarkWrongRequest(BaseModel):
    correction_title: str
    correction_content: str
    doc_type: str = "faq"  # "faq" or "policy"
    notes: Optional[str] = None
    corrected_reply: Optional[str] = None

@router.get("/runs", response_model=List[AIRunResponse])
async def list_ai_runs(
    flagged_only: bool = Query(False),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Lists AI runs with customer prompt, retrieved knowledge sources, and tool calls."""
    stmt = select(AIRun).order_by(AIRun.created_at.desc()).limit(limit)
    if flagged_only:
        stmt = stmt.where(AIRun.is_flagged_wrong == True)

    res = await db.execute(stmt)
    runs = res.scalars().all()

    # Backfill user_message from Message if missing
    for r in runs:
        if not r.user_message and r.thread_id:
            m_res = await db.execute(
                select(Message.content)
                .where(Message.thread_id == r.thread_id, Message.sender_type == "customer")
                .order_by(Message.id.desc())
            )
            r.user_message = m_res.scalar_one_or_none()

    return runs

@router.post("/runs/{run_id}/mark-wrong", response_model=AIRunResponse)
async def mark_run_wrong_and_correct_kb(
    run_id: int,
    req: MarkWrongRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Marks an AI run as wrong and creates a new grounded knowledge base document.
    Immediately reindexes the vector embeddings into pgvector / chunks so the AI
    answers accurately in all subsequent conversations.
    """
    res = await db.execute(select(AIRun).where(AIRun.id == run_id))
    run = res.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="AI Run not found")

    # 1. Create correction document in Knowledge Base
    kb_doc = KBDocument(
        doc_type=req.doc_type,
        title=req.correction_title,
        content=req.correction_content,
        is_active=True
    )
    db.add(kb_doc)
    await db.flush()

    # 2. Flag the AI run
    run.is_flagged_wrong = True
    run.correction_notes = req.notes or f"Corrected via AI Review: '{req.correction_title}'"
    run.corrected_kb_doc_id = kb_doc.id
    if req.corrected_reply:
        run.corrected_reply = req.corrected_reply

        # Auto-append to regression eval set
        try:
            import os
            import json
            evals_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "evals")
            os.makedirs(evals_dir, exist_ok=True)
            reg_path = os.path.join(evals_dir, "regression_cases.json")
            reg_cases = []
            if os.path.exists(reg_path):
                with open(reg_path, "r", encoding="utf-8") as f:
                    reg_cases = json.load(f)
            reg_cases.append({
                "id": f"reg_{run.id}",
                "category": "merchant_review_correction",
                "customer_message": run.user_message or req.correction_title,
                "expected_reply": req.corrected_reply,
                "created_at": datetime.utcnow().isoformat()
            })
            with open(reg_path, "w", encoding="utf-8") as f:
                json.dump(reg_cases, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    await db.commit()

    # 3. Automatically Reindex Knowledge Base into pgvector / KBChunks
    await reindex_all_knowledge(db)
    await db.refresh(run)

    return run
