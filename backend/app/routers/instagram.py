import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.crypto import encrypt_token, decrypt_token
from app.core.config import settings
from app.models.schema import InstagramConnection, FacebookConnection
from app.routers.auth import get_current_admin

router = APIRouter(prefix="/instagram", tags=["Instagram Professional Connection"])

class InstagramStatusResponse(BaseModel):
    is_connected: bool
    ig_user_id: Optional[str] = None
    username: Optional[str] = None
    page_id: Optional[str] = None
    auto_send: bool = False
    connected_at: Optional[datetime] = None
    verify_token: str
    webhook_callback_url: str

class InstagramConnectRequest(BaseModel):
    ig_user_id: str
    username: Optional[str] = None
    page_id: Optional[str] = None
    access_token: str
    auto_send: bool = False

class InstagramSettingsUpdateRequest(BaseModel):
    auto_send: bool

@router.get("/status", response_model=InstagramStatusResponse)
async def get_instagram_status(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Returns current Instagram Professional account connection status and webhook config.
    """
    res = await db.execute(select(InstagramConnection).where(InstagramConnection.is_active == True))
    conn = res.scalars().first()

    webhook_url = f"{settings.BACKEND_CORS_ORIGINS[0] if settings.CORS_ORIGINS else 'http://localhost:8000'}/api/webhooks/meta"

    if not conn:
        return InstagramStatusResponse(
            is_connected=False,
            verify_token=settings.META_VERIFY_TOKEN,
            webhook_callback_url=webhook_url
        )

    return InstagramStatusResponse(
        is_connected=True,
        ig_user_id=conn.ig_user_id,
        username=conn.username,
        page_id=conn.page_id,
        auto_send=conn.auto_send,
        connected_at=conn.connected_at,
        verify_token=settings.META_VERIFY_TOKEN,
        webhook_callback_url=webhook_url
    )

@router.post("/connect", response_model=InstagramStatusResponse)
async def connect_instagram(
    payload: InstagramConnectRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Connects or reconnects an Instagram Professional account with encrypted access token.
    """
    if not payload.ig_user_id.strip() or not payload.access_token.strip():
        raise HTTPException(status_code=400, detail="Instagram User ID and Access Token are required")

    encrypted_token = encrypt_token(payload.access_token.strip())

    res = await db.execute(
        select(InstagramConnection).where(InstagramConnection.ig_user_id == payload.ig_user_id.strip())
    )
    conn = res.scalars().first()

    now_utc = datetime.now(timezone.utc)
    if conn:
        conn.username = payload.username
        conn.page_id = payload.page_id
        conn.encrypted_access_token = encrypted_token
        conn.is_active = True
        conn.auto_send = payload.auto_send
        conn.updated_at = now_utc
    else:
        conn = InstagramConnection(
            ig_user_id=payload.ig_user_id.strip(),
            username=payload.username or f"ig_account_{payload.ig_user_id[-4:]}",
            page_id=payload.page_id,
            encrypted_access_token=encrypted_token,
            is_active=True,
            auto_send=payload.auto_send,
            connected_at=now_utc,
            updated_at=now_utc
        )
        db.add(conn)

    await db.commit()
    await db.refresh(conn)

    webhook_url = f"{settings.BACKEND_CORS_ORIGINS[0] if settings.CORS_ORIGINS else 'http://localhost:8000'}/api/webhooks/meta"
    return InstagramStatusResponse(
        is_connected=True,
        ig_user_id=conn.ig_user_id,
        username=conn.username,
        page_id=conn.page_id,
        auto_send=conn.auto_send,
        connected_at=conn.connected_at,
        verify_token=settings.META_VERIFY_TOKEN,
        webhook_callback_url=webhook_url
    )

@router.post("/discover-from-page")
async def discover_instagram_from_page(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Queries Meta Graph API using the connected Facebook Page Access Token to automatically discover
    any linked Instagram Professional / Business Account.
    Endpoint: GET /{page_id}?fields=instagram_business_account{id,username,name,profile_picture_url}
    """
    fb_res = await db.execute(select(FacebookConnection).where(FacebookConnection.is_active == True))
    fb_conn = fb_res.scalars().first()
    if not fb_conn:
        raise HTTPException(
            status_code=400,
            detail="No Facebook Page connected yet. Connect your Facebook Page first to auto-discover your linked Instagram Professional account."
        )

    token = decrypt_token(fb_conn.encrypted_access_token)
    if not token or token.startswith("mock_") or token == "test":
        # Mock discovery for testing/sandbox
        mock_ig_id = f"17841400{fb_conn.page_id[-4:]}"
        mock_username = f"{fb_conn.page_name.lower().replace(' ', '_')}_official"
        return {
            "found": True,
            "ig_user_id": mock_ig_id,
            "username": mock_username,
            "page_id": fb_conn.page_id,
            "page_name": fb_conn.page_name,
            "mock": True
        }

    url = f"https://graph.facebook.com/{settings.META_GRAPH_VERSION}/{fb_conn.page_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            url,
            params={
                "fields": "instagram_business_account{id,username,name,profile_picture_url}",
                "access_token": token
            }
        )
        data = resp.json()
        if resp.status_code != 200:
            err = data.get("error", {}).get("message", "Graph API query failed")
            raise HTTPException(status_code=400, detail=f"Meta Graph API error: {err}")

        ig_account = data.get("instagram_business_account")
        if not ig_account:
            return {
                "found": False,
                "message": "No Instagram Business account is linked to this Facebook Page. Please link your Instagram Professional account in Facebook Page Settings > Linked Accounts."
            }

        return {
            "found": True,
            "ig_user_id": ig_account.get("id"),
            "username": ig_account.get("username"),
            "name": ig_account.get("name"),
            "page_id": fb_conn.page_id
        }

@router.post("/disconnect")
async def disconnect_instagram(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Disconnects the active Instagram Professional connection."""
    res = await db.execute(select(InstagramConnection).where(InstagramConnection.is_active == True))
    conn = res.scalars().first()
    if conn:
        conn.is_active = False
        await db.commit()
    return {"status": "disconnected"}

@router.put("/settings")
async def update_instagram_settings(
    payload: InstagramSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Updates auto-send settings for Instagram."""
    res = await db.execute(select(InstagramConnection).where(InstagramConnection.is_active == True))
    conn = res.scalars().first()
    if not conn:
        raise HTTPException(status_code=404, detail="No active Instagram connection found")

    conn.auto_send = payload.auto_send
    await db.commit()
    return {"status": "updated", "auto_send": conn.auto_send}
