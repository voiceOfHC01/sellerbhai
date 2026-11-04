from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.schema import Thread, Message, Customer, FacebookConnection, InstagramConnection, WhatsAppConnection, WhatsAppUsageLog
from app.routers.auth import get_current_admin
from app.services.window_guard import check_messaging_window, validate_send_allowed, MessagingWindowExpiredError
from app.services.meta_client import MetaClient
from app.services.whatsapp_client import WhatsAppClient
from app.core.crypto import decrypt_token

router = APIRouter(prefix="/inbox", tags=["Unified Inbox"])

class ManualReplyRequest(BaseModel):
    message: str

class ThreadSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: str
    status: str
    ai_enabled: bool
    handover_reason: Optional[str] = None
    last_activity_at: datetime
    last_customer_message_at: Optional[datetime] = None
    customer_id: int
    customer_name: str
    customer_phone: Optional[str] = None
    last_message_text: Optional[str] = None
    has_pending_draft: bool = False
    is_window_active: bool = True
    window_hours_remaining: float = 24.0

class MessageDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: int
    sender_type: str
    content: str
    language: Optional[str] = None
    platform_message_id: Optional[str] = None
    is_draft: bool = False
    delivery_status: str = "sent"
    audio_url: Optional[str] = None
    voice_transcript: Optional[str] = None
    voice_confidence: Optional[float] = None
    is_voice_message: bool = False
    metadata_json: Optional[Any] = None
    created_at: datetime

@router.get("/threads", response_model=List[ThreadSummaryResponse])
async def list_threads(
    channel: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(Thread).options(
        selectinload(Thread.customer),
        selectinload(Thread.messages)
    ).order_by(Thread.last_activity_at.desc())

    if channel:
        stmt = stmt.where(Thread.channel == channel)
    if status_filter:
        stmt = stmt.where(Thread.status == status_filter)

    res = await db.execute(stmt)
    threads = res.scalars().all()

    output = []
    for t in threads:
        # Determine last message and draft presence
        last_msg = None
        has_draft = False
        if t.messages:
            sorted_msgs = sorted(t.messages, key=lambda m: m.id)
            last_msg = sorted_msgs[-1].content
            has_draft = any(m.is_draft for m in t.messages)

        # 24h window calculation
        is_allowed, hours_rem, _ = check_messaging_window(t.last_customer_message_at)

        output.append({
            "id": t.id,
            "channel": t.channel,
            "status": t.status,
            "ai_enabled": t.ai_enabled,
            "handover_reason": t.handover_reason,
            "last_activity_at": t.last_activity_at,
            "last_customer_message_at": t.last_customer_message_at,
            "customer_id": t.customer.id if t.customer else 0,
            "customer_name": t.customer.name if t.customer else "Guest",
            "customer_phone": t.customer.phone if t.customer else None,
            "last_message_text": last_msg,
            "has_pending_draft": has_draft,
            "is_window_active": is_allowed,
            "window_hours_remaining": hours_rem
        })

    return output

@router.get("/threads/{thread_id}/messages", response_model=List[MessageDetailResponse])
async def get_thread_messages(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(
        select(Message).where(Message.thread_id == thread_id).order_by(Message.id.asc())
    )
    return res.scalars().all()

@router.post("/threads/{thread_id}/reply")
async def send_manual_reply(
    thread_id: int,
    data: ManualReplyRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Sends an agent manual reply to the customer.
    Enforces the 24-hour Standard Messaging Window policy.
    """
    res = await db.execute(
        select(Thread).options(selectinload(Thread.customer)).where(Thread.id == thread_id)
    )
    thread = res.scalars().first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    text = data.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Reply cannot be empty")

    # 1. Enforce 24-Hour Messaging Window Guard
    try:
        validate_send_allowed(thread.last_customer_message_at)
    except MessagingWindowExpiredError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err.message
        )

    # 2. Dispatch to platform
    platform_mid = None
    if thread.channel == "facebook" and thread.customer.channel_id:
        conn_res = await db.execute(select(FacebookConnection).where(FacebookConnection.is_active == True))
        fb_conn = conn_res.scalars().first()
        token = decrypt_token(fb_conn.encrypted_access_token) if fb_conn else None

        client = MetaClient(page_access_token=token)
        try:
            send_res = await client.send_text_message(
                recipient_psid=thread.customer.channel_id,
                message_text=text,
                last_customer_message_at=thread.last_customer_message_at
            )
            platform_mid = send_res.get("message_id")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Meta Send API failed: {str(e)}")

    elif thread.channel == "instagram" and thread.customer.channel_id:
        conn_res = await db.execute(select(InstagramConnection).where(InstagramConnection.is_active == True))
        ig_conn = conn_res.scalars().first()
        token = decrypt_token(ig_conn.encrypted_access_token) if ig_conn else None

        client = MetaClient(page_access_token=token)
        try:
            send_res = await client.send_instagram_message(
                recipient_igsid=thread.customer.channel_id,
                message_text=text,
                last_customer_message_at=thread.last_customer_message_at,
                ig_user_id=ig_conn.ig_user_id if ig_conn else None
            )
            platform_mid = send_res.get("message_id")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Instagram Send API failed: {str(e)}")

    elif thread.channel == "whatsapp" and thread.customer.channel_id:
        conn_res = await db.execute(select(WhatsAppConnection).where(WhatsAppConnection.is_active == True))
        wa_conn = conn_res.scalars().first()
        token = decrypt_token(wa_conn.encrypted_access_token) if wa_conn else None

        wa_client = WhatsAppClient(
            phone_number_id=wa_conn.phone_number_id if wa_conn else None,
            access_token=token
        )
        try:
            send_res = await wa_client.send_text_message(
                recipient_phone=thread.customer.channel_id,
                message_text=text,
                last_customer_message_at=thread.last_customer_message_at
            )
            platform_mid = send_res.get("messages", [{}])[0].get("id")
            # Log usage for WhatsApp
            db.add(WhatsAppUsageLog(
                message_id=platform_mid,
                thread_id=thread.id,
                customer_id=thread.customer_id,
                recipient_phone=thread.customer.channel_id,
                category="service",
                direction="outbound",
                status="sent"
            ))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"WhatsApp Send API failed: {str(e)}")

    # 3. Store message in DB
    now_utc = datetime.now(timezone.utc)
    msg = Message(
        thread_id=thread.id,
        sender_type="admin",
        content=text,
        platform_message_id=platform_mid,
        is_draft=False,
        delivery_status="sent"
    )
    db.add(msg)
    thread.last_activity_at = now_utc
    await db.commit()
    await db.refresh(msg)

    return {
        "status": "sent",
        "message_id": msg.id,
        "platform_message_id": platform_mid,
        "created_at": msg.created_at
    }

@router.post("/threads/{thread_id}/toggle-ai")
async def toggle_ai(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = res.scalars().first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread.ai_enabled = not thread.ai_enabled
    await db.commit()
    return {"status": "success", "ai_enabled": thread.ai_enabled}

@router.post("/threads/{thread_id}/takeover")
async def take_over_thread(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = res.scalars().first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread.status = "human_takeover"
    thread.ai_enabled = False
    thread.handover_reason = "Manual takeover by merchant in Unified Inbox"
    await db.commit()
    return {"status": "success", "thread_status": thread.status, "ai_enabled": False}

@router.post("/threads/{thread_id}/resume-ai")
async def resume_ai_thread(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = res.scalars().first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread.status = "active"
    thread.ai_enabled = True
    thread.handover_reason = None
    await db.commit()
    return {"status": "success", "thread_status": thread.status, "ai_enabled": True}

@router.post("/drafts/{draft_id}/approve")
async def approve_draft_reply(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Approves an AI-generated draft reply and sends it out to the customer.
    Enforces the 24-hour Messaging Window Guard.
    """
    res = await db.execute(
        select(Message).options(
            selectinload(Message.thread).selectinload(Thread.customer)
        ).where(Message.id == draft_id)
    )
    draft = res.scalars().first()
    if not draft or not draft.is_draft:
        raise HTTPException(status_code=404, detail="Draft message not found")

    thread = draft.thread
    # 1. Enforce 24-Hour Window Guard
    try:
        validate_send_allowed(thread.last_customer_message_at)
    except MessagingWindowExpiredError as err:
        draft.delivery_status = "blocked_outside_window"
        await db.commit()
        raise HTTPException(status_code=400, detail=err.message)

    # 2. Dispatch via client based on channel
    platform_mid = None
    if thread.channel == "facebook" and thread.customer.channel_id:
        conn_res = await db.execute(select(FacebookConnection).where(FacebookConnection.is_active == True))
        fb_conn = conn_res.scalars().first()
        token = decrypt_token(fb_conn.encrypted_access_token) if fb_conn else None

        client = MetaClient(page_access_token=token)
        try:
            send_res = await client.send_text_message(
                recipient_psid=thread.customer.channel_id,
                message_text=draft.content,
                last_customer_message_at=thread.last_customer_message_at
            )
            platform_mid = send_res.get("message_id")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Meta Send API error: {str(e)}")

    elif thread.channel == "instagram" and thread.customer.channel_id:
        conn_res = await db.execute(select(InstagramConnection).where(InstagramConnection.is_active == True))
        ig_conn = conn_res.scalars().first()
        token = decrypt_token(ig_conn.encrypted_access_token) if ig_conn else None

        client = MetaClient(page_access_token=token)
        try:
            send_res = await client.send_instagram_message(
                recipient_igsid=thread.customer.channel_id,
                message_text=draft.content,
                last_customer_message_at=thread.last_customer_message_at,
                ig_user_id=ig_conn.ig_user_id if ig_conn else None
            )
            platform_mid = send_res.get("message_id")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Instagram Send API error: {str(e)}")

    elif thread.channel == "whatsapp" and thread.customer.channel_id:
        conn_res = await db.execute(select(WhatsAppConnection).where(WhatsAppConnection.is_active == True))
        wa_conn = conn_res.scalars().first()
        token = decrypt_token(wa_conn.encrypted_access_token) if wa_conn else None

        wa_client = WhatsAppClient(
            phone_number_id=wa_conn.phone_number_id if wa_conn else None,
            access_token=token
        )
        try:
            send_res = await wa_client.send_text_message(
                recipient_phone=thread.customer.channel_id,
                message_text=draft.content,
                last_customer_message_at=thread.last_customer_message_at
            )
            platform_mid = send_res.get("messages", [{}])[0].get("id")
            # Log usage for WhatsApp
            db.add(WhatsAppUsageLog(
                message_id=platform_mid,
                thread_id=thread.id,
                customer_id=thread.customer_id,
                recipient_phone=thread.customer.channel_id,
                category="service",
                direction="outbound",
                status="sent"
            ))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"WhatsApp Send API error: {str(e)}")

    # 3. Update draft to sent
    draft.is_draft = False
    draft.delivery_status = "sent"
    draft.platform_message_id = platform_mid
    thread.last_activity_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "approved_and_sent", "message_id": draft.id, "platform_message_id": platform_mid}

@router.delete("/drafts/{draft_id}")
async def discard_draft_reply(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(Message).where(Message.id == draft_id))
    draft = res.scalars().first()
    if not draft or not draft.is_draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    await db.delete(draft)
    await db.commit()
    return {"status": "discarded"}

@router.delete("/customers/{customer_id}")
async def delete_customer_data(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Per-Customer Data Delete Button endpoint (GDPR / Meta Compliance).
    Permanently deletes a customer's profile, conversation history, and personal identifiers.
    """
    c_res = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = c_res.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Delete threads and messages
    t_res = await db.execute(select(Thread).where(Thread.customer_id == customer_id))
    threads = t_res.scalars().all()
    for t in threads:
        await db.execute(delete(Message).where(Message.thread_id == t.id))
        await db.delete(t)

    # Delete customer orders and items
    from app.models.schema import Order
    o_res = await db.execute(select(Order).where(Order.customer_id == customer_id))
    orders = o_res.scalars().all()
    for o in orders:
        await db.delete(o)

    await db.delete(customer)
    await db.commit()

    return {
        "status": "deleted",
        "customer_id": customer_id,
        "message": "Customer profile, conversations, and personal data permanently deleted."
    }
