import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schema import Comment, Setting, FacebookConnection, InstagramConnection
from app.routers.auth import get_current_admin
from app.services.meta_client import MetaClient
from app.core.crypto import decrypt_token
from app.services.comment_engine import get_comment_settings

router = APIRouter(prefix="/comments", tags=["Comments Automation"])

class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    platform_comment_id: str
    post_id: Optional[str] = None
    author_id: str
    author_name: Optional[str] = None
    message: str
    status: str
    actions_taken: List[str] = []
    public_reply_text: Optional[str] = None
    private_reply_text: Optional[str] = None
    is_hidden: bool
    is_private_reply_sent: bool
    created_at: datetime
    updated_at: datetime

class ManualReplyRequest(BaseModel):
    reply_type: str  # "public" or "private"
    message: str

class CommentSettingsUpdateRequest(BaseModel):
    comment_auto_reply_enabled: bool
    spam_filter_enabled: bool
    spam_hide_links: bool
    spam_hide_phones: bool
    abusive_words: List[str]
    comment_rules: List[Dict[str, Any]]
    comment_fallback_ai: bool

@router.get("", response_model=List[CommentResponse])
async def list_comments(
    platform: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Lists received comments across Facebook Page posts and Instagram posts.
    """
    stmt = select(Comment).order_by(Comment.id.desc())

    if platform and platform != "all":
        stmt = stmt.where(Comment.platform == platform.strip().lower())

    if status_filter and status_filter != "all":
        stmt = stmt.where(Comment.status == status_filter.strip().lower())

    if search:
        search_term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Comment.message.ilike(search_term),
                Comment.author_name.ilike(search_term),
                Comment.post_id.ilike(search_term),
                Comment.platform_comment_id.ilike(search_term)
            )
        )

    res = await db.execute(stmt)
    comments = res.scalars().all()
    return comments

@router.get("/settings")
async def get_comments_config(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Retrieves current comment automation and spam filter configuration."""
    return await get_comment_settings(db)

@router.put("/settings")
async def update_comments_config(
    payload: CommentSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Updates comment automation rules, spam filters, and abusive words."""
    updates = {
        "comment_auto_reply_enabled": str(payload.comment_auto_reply_enabled).lower(),
        "spam_filter_enabled": str(payload.spam_filter_enabled).lower(),
        "spam_hide_links": str(payload.spam_hide_links).lower(),
        "spam_hide_phones": str(payload.spam_hide_phones).lower(),
        "abusive_words": json.dumps(payload.abusive_words),
        "comment_rules": json.dumps(payload.comment_rules),
        "comment_fallback_ai": str(payload.comment_fallback_ai).lower(),
    }

    for k, v in updates.items():
        res = await db.execute(select(Setting).where(Setting.key == k))
        row = res.scalars().first()
        if row:
            row.value = v
        else:
            db.add(Setting(key=k, value=v, description=f"Comment setting {k}"))

    await db.commit()
    return await get_comment_settings(db)

@router.post("/{comment_id}/reply", response_model=CommentResponse)
async def reply_to_comment_manually(
    comment_id: int,
    payload: ManualReplyRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Manually dispatches a public reply or private DM reply to a specific comment.
    Enforces Meta platform limit on private replies (once per comment).
    """
    res = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = res.scalars().first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Get token
    access_token = None
    if comment.platform == "facebook":
        fb_res = await db.execute(select(FacebookConnection).where(FacebookConnection.is_active == True))
        fb = fb_res.scalars().first()
        if fb:
            access_token = decrypt_token(fb.encrypted_access_token)
    else:
        ig_res = await db.execute(select(InstagramConnection).where(InstagramConnection.is_active == True))
        ig = ig_res.scalars().first()
        if ig:
            access_token = decrypt_token(ig.encrypted_access_token)

    meta_client = MetaClient(page_access_token=access_token)
    actions = list(comment.actions_taken or [])

    if payload.reply_type == "public":
        try:
            await meta_client.post_public_comment_reply(
                comment_id=comment.platform_comment_id,
                message_text=payload.message,
                platform=comment.platform
            )
            comment.public_reply_text = payload.message
            actions.append("manual_public_reply_sent")
            comment.status = "replied"
        except Exception as e:
            actions.append(f"manual_public_reply_failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to post public reply: {str(e)}")

    elif payload.reply_type == "private":
        if comment.is_private_reply_sent:
            raise HTTPException(
                status_code=400,
                detail="Meta Platform Limit: A private reply can only be sent ONCE per comment. A private reply has already been delivered for this comment."
            )
        try:
            await meta_client.send_private_reply_to_comment(
                comment_id=comment.platform_comment_id,
                message_text=payload.message,
                platform=comment.platform
            )
            comment.is_private_reply_sent = True
            comment.private_reply_text = payload.message
            actions.append("manual_private_reply_sent")
            comment.status = "replied"
        except Exception as e:
            actions.append(f"manual_private_reply_failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to send private reply: {str(e)}")

    comment.actions_taken = actions
    await db.commit()
    await db.refresh(comment)
    return comment

@router.post("/{comment_id}/hide", response_model=CommentResponse)
async def hide_comment_manually(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Manually hides an offensive or spam comment."""
    res = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = res.scalars().first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    access_token = None
    if comment.platform == "facebook":
        fb_res = await db.execute(select(FacebookConnection).where(FacebookConnection.is_active == True))
        fb = fb_res.scalars().first()
        if fb:
            access_token = decrypt_token(fb.encrypted_access_token)
    else:
        ig_res = await db.execute(select(InstagramConnection).where(InstagramConnection.is_active == True))
        ig = ig_res.scalars().first()
        if ig:
            access_token = decrypt_token(ig.encrypted_access_token)

    meta_client = MetaClient(page_access_token=access_token)
    try:
        await meta_client.hide_comment(comment.platform_comment_id)
        comment.is_hidden = True
        comment.status = "hidden_spam"
        actions = list(comment.actions_taken or [])
        actions.append("manually_hidden")
        comment.actions_taken = actions
        await db.commit()
        await db.refresh(comment)
        return comment
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to hide comment: {str(e)}")
