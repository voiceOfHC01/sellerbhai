from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schema import FacebookConnection
from app.routers.auth import get_current_admin
from app.core.crypto import encrypt_token, decrypt_token
from app.core.config import settings

router = APIRouter(prefix="/facebook", tags=["Facebook Page Integration"])

class ConnectPageRequest(BaseModel):
    page_id: str
    page_name: str
    page_access_token: str
    auto_send: bool = False

class UpdatePageSettingsRequest(BaseModel):
    auto_send: bool

class FacebookConnectionResponse(BaseModel):
    is_connected: bool
    page_id: Optional[str] = None
    page_name: Optional[str] = None
    auto_send: bool = False
    connected_at: Optional[datetime] = None
    verify_token: str = settings.META_VERIFY_TOKEN
    webhook_callback_url: str = "/api/webhooks/meta"

@router.get("/status", response_model=FacebookConnectionResponse)
async def get_connection_status(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(FacebookConnection).where(FacebookConnection.is_active == True))
    conn = res.scalars().first()

    if not conn:
        return {
            "is_connected": False,
            "verify_token": settings.META_VERIFY_TOKEN,
            "webhook_callback_url": "/api/webhooks/meta"
        }

    return {
        "is_connected": True,
        "page_id": conn.page_id,
        "page_name": conn.page_name,
        "auto_send": conn.auto_send,
        "connected_at": conn.connected_at,
        "verify_token": settings.META_VERIFY_TOKEN,
        "webhook_callback_url": "/api/webhooks/meta"
    }

@router.post("/connect", response_model=FacebookConnectionResponse)
async def connect_page(
    data: ConnectPageRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    # Encrypt Page Access Token
    encrypted_token = encrypt_token(data.page_access_token.strip())

    res = await db.execute(select(FacebookConnection).where(FacebookConnection.page_id == data.page_id.strip()))
    conn = res.scalars().first()

    if conn:
        conn.page_name = data.page_name.strip()
        conn.encrypted_access_token = encrypted_token
        conn.auto_send = data.auto_send
        conn.is_active = True
        conn.updated_at = datetime.now(timezone.utc)
    else:
        conn = FacebookConnection(
            page_id=data.page_id.strip(),
            page_name=data.page_name.strip(),
            encrypted_access_token=encrypted_token,
            auto_send=data.auto_send,
            is_active=True
        )
        db.add(conn)

    await db.commit()
    await db.refresh(conn)

    return {
        "is_connected": True,
        "page_id": conn.page_id,
        "page_name": conn.page_name,
        "auto_send": conn.auto_send,
        "connected_at": conn.connected_at,
        "verify_token": settings.META_VERIFY_TOKEN,
        "webhook_callback_url": "/api/webhooks/meta"
    }

@router.post("/disconnect")
async def disconnect_page(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(FacebookConnection).where(FacebookConnection.is_active == True))
    conn = res.scalars().first()
    if conn:
        conn.is_active = False
        await db.commit()
    return {"status": "success", "message": "Facebook Page disconnected successfully"}

@router.put("/settings")
async def update_page_settings(
    data: UpdatePageSettingsRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    res = await db.execute(select(FacebookConnection).where(FacebookConnection.is_active == True))
    conn = res.scalars().first()
    if not conn:
        raise HTTPException(status_code=404, detail="No active Facebook Page connected")

    conn.auto_send = data.auto_send
    await db.commit()
    return {"status": "success", "auto_send": conn.auto_send}
