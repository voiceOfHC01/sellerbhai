import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.crypto import encrypt_token, decrypt_token
from app.core.config import settings
from app.models.schema import (
    WhatsAppConnection, WhatsAppTemplate, WhatsAppUsageLog, Thread, Customer, Message, Setting
)
from app.routers.auth import get_current_admin
from app.services.whatsapp_client import WhatsAppClient, WhatsAppCustomerServiceWindowError

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Cloud API"])

# --- Pydantic Schemas ---

class WhatsAppStatusResponse(BaseModel):
    is_connected: bool
    phone_number_id: Optional[str] = None
    waba_id: Optional[str] = None
    phone_number: Optional[str] = None
    is_test_number: bool = True
    auto_send: bool = False
    connected_at: Optional[datetime] = None
    verify_token: str
    webhook_callback_url: str

class WhatsAppConnectRequest(BaseModel):
    phone_number_id: str
    waba_id: Optional[str] = None
    phone_number: Optional[str] = None
    access_token: str
    is_test_number: bool = True
    auto_send: bool = False

class WhatsAppSettingsUpdateRequest(BaseModel):
    auto_send: bool

class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    waba_id: Optional[str] = None
    name: str
    category: str
    language: str
    status: str
    header_text: Optional[str] = None
    body_text: str
    footer_text: Optional[str] = None
    buttons_json: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

class TemplateCreateRequest(BaseModel):
    name: str
    category: str  # MARKETING, UTILITY, AUTHENTICATION, SERVICE
    language: str = "bn"
    header_text: Optional[str] = None
    body_text: str
    footer_text: Optional[str] = None
    buttons_json: Optional[Any] = None

class TemplateSendRequest(BaseModel):
    template_name: str
    recipient_phone: str
    language_code: str = "bn"
    body_parameters: Optional[List[str]] = None
    customer_opted_in: bool = True

class UsageRatesUpdateRequest(BaseModel):
    rate_marketing: float
    rate_utility: float
    rate_service: float
    rate_authentication: float
    currency: str = "BDT"

class UsageStatsResponse(BaseModel):
    period: str
    total_messages: int
    service_count: int
    utility_count: int
    marketing_count: int
    authentication_count: int
    rates: Dict[str, float]
    currency: str
    estimated_cost: float
    breakdown_cost: Dict[str, float]

# --- Helper Functions ---

async def get_whatsapp_rates(db: AsyncSession) -> Dict[str, Any]:
    res = await db.execute(select(Setting))
    settings_rows = res.scalars().all()
    s_map = {s.key: s.value for s in settings_rows}

    return {
        "rate_marketing": float(s_map.get("whatsapp_rate_marketing", "5.50")),
        "rate_utility": float(s_map.get("whatsapp_rate_utility", "1.80")),
        "rate_service": float(s_map.get("whatsapp_rate_service", "0.00")),
        "rate_authentication": float(s_map.get("whatsapp_rate_authentication", "1.50")),
        "currency": s_map.get("whatsapp_currency", "BDT")
    }

# --- Connection Endpoints ---

@router.get("/status", response_model=WhatsAppStatusResponse)
async def get_whatsapp_status(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Returns active WhatsApp Cloud API connection status and webhook config."""
    res = await db.execute(select(WhatsAppConnection).where(WhatsAppConnection.is_active == True))
    conn = res.scalars().first()

    webhook_url = f"{settings.BACKEND_CORS_ORIGINS[0] if settings.CORS_ORIGINS else 'http://localhost:8000'}/api/webhooks/meta"

    if not conn:
        return WhatsAppStatusResponse(
            is_connected=False,
            is_test_number=True,
            verify_token=settings.META_VERIFY_TOKEN,
            webhook_callback_url=webhook_url
        )

    return WhatsAppStatusResponse(
        is_connected=True,
        phone_number_id=conn.phone_number_id,
        waba_id=conn.waba_id,
        phone_number=conn.phone_number,
        is_test_number=conn.is_test_number,
        auto_send=conn.auto_send,
        connected_at=conn.connected_at,
        verify_token=settings.META_VERIFY_TOKEN,
        webhook_callback_url=webhook_url
    )

@router.post("/connect", response_model=WhatsAppStatusResponse)
async def connect_whatsapp(
    payload: WhatsAppConnectRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Connects WhatsApp Cloud API using Meta's test phone number or real registered business number.
    Encrypts access token securely with Fernet.
    """
    if not payload.phone_number_id.strip() or not payload.access_token.strip():
        raise HTTPException(status_code=400, detail="Phone Number ID and Access Token are required")

    encrypted_token = encrypt_token(payload.access_token.strip())

    res = await db.execute(
        select(WhatsAppConnection).where(WhatsAppConnection.phone_number_id == payload.phone_number_id.strip())
    )
    conn = res.scalars().first()
    now_utc = datetime.now(timezone.utc)

    if conn:
        conn.waba_id = payload.waba_id
        conn.phone_number = payload.phone_number
        conn.encrypted_access_token = encrypted_token
        conn.is_test_number = payload.is_test_number
        conn.is_active = True
        conn.auto_send = payload.auto_send
        conn.updated_at = now_utc
    else:
        conn = WhatsAppConnection(
            phone_number_id=payload.phone_number_id.strip(),
            waba_id=payload.waba_id,
            phone_number=payload.phone_number,
            encrypted_access_token=encrypted_token,
            is_test_number=payload.is_test_number,
            is_active=True,
            auto_send=payload.auto_send,
            created_at=now_utc,
            updated_at=now_utc
        )
        db.add(conn)

    await db.commit()
    await db.refresh(conn)

    webhook_url = f"{settings.BACKEND_CORS_ORIGINS[0] if settings.CORS_ORIGINS else 'http://localhost:8000'}/api/webhooks/meta"
    return WhatsAppStatusResponse(
        is_connected=True,
        phone_number_id=conn.phone_number_id,
        waba_id=conn.waba_id,
        phone_number=conn.phone_number,
        is_test_number=conn.is_test_number,
        auto_send=conn.auto_send,
        connected_at=conn.connected_at,
        verify_token=settings.META_VERIFY_TOKEN,
        webhook_callback_url=webhook_url
    )

@router.post("/disconnect")
async def disconnect_whatsapp(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Disconnects WhatsApp Cloud API connection."""
    res = await db.execute(select(WhatsAppConnection).where(WhatsAppConnection.is_active == True))
    conn = res.scalars().first()
    if conn:
        conn.is_active = False
        await db.commit()
    return {"status": "disconnected"}

@router.put("/settings")
async def update_whatsapp_settings(
    payload: WhatsAppSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Updates auto-send setting for WhatsApp."""
    res = await db.execute(select(WhatsAppConnection).where(WhatsAppConnection.is_active == True))
    conn = res.scalars().first()
    if not conn:
        raise HTTPException(status_code=404, detail="No active WhatsApp connection found")

    conn.auto_send = payload.auto_send
    await db.commit()
    return {"status": "updated", "auto_send": conn.auto_send}

# --- Template Management Endpoints ---

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Lists pre-approved and merchant-defined WhatsApp Message Templates."""
    res = await db.execute(select(WhatsAppTemplate).order_by(WhatsAppTemplate.id.desc()))
    return res.scalars().all()

@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    payload: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Creates a new WhatsApp message template in local catalog."""
    normalized_name = payload.name.strip().lower().replace(" ", "_")
    valid_categories = ["MARKETING", "UTILITY", "AUTHENTICATION", "SERVICE"]
    cat = payload.category.strip().upper()
    if cat not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Category must be one of: {valid_categories}")

    now_utc = datetime.now(timezone.utc)
    tpl = WhatsAppTemplate(
        name=normalized_name,
        category=cat,
        language=payload.language.strip(),
        status="APPROVED",  # Marked ready for test/staging sends
        header_text=payload.header_text,
        body_text=payload.body_text,
        footer_text=payload.footer_text,
        buttons_json=payload.buttons_json,
        created_at=now_utc,
        updated_at=now_utc
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl

@router.post("/templates/send")
async def send_template(
    payload: TemplateSendRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Sends an approved WhatsApp Template to an opted-in customer.
    Permitted BOTH inside and outside the 24-hour Customer Service Window.
    Logs usage cost category (utility / marketing / authentication).
    """
    if not payload.customer_opted_in:
        raise HTTPException(
            status_code=400,
            detail="Opt-in Requirement: Meta policies strictly require verifiable customer opt-in before sending business-initiated templates."
        )

    # Check template in DB
    t_res = await db.execute(
        select(WhatsAppTemplate).where(WhatsAppTemplate.name == payload.template_name)
    )
    template = t_res.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{payload.template_name}' not found.")

    # Get connection & token
    conn_res = await db.execute(select(WhatsAppConnection).where(WhatsAppConnection.is_active == True))
    wa_conn = conn_res.scalars().first()
    if not wa_conn:
        raise HTTPException(status_code=400, detail="No active WhatsApp connection found. Connect WhatsApp first.")

    token = decrypt_token(wa_conn.encrypted_access_token)
    wa_client = WhatsAppClient(phone_number_id=wa_conn.phone_number_id, access_token=token)

    try:
        res = await wa_client.send_template_message(
            recipient_phone=payload.recipient_phone,
            template_name=template.name,
            language_code=payload.language_code,
            body_parameters=payload.body_parameters,
            customer_opted_in=payload.customer_opted_in
        )
        msg_id = res.get("messages", [{}])[0].get("id")

        # Find or create customer and thread for inbox visibility
        norm_phone = payload.recipient_phone.replace("+", "").replace("-", "").replace(" ", "")
        c_res = await db.execute(
            select(Customer).where(Customer.channel == "whatsapp", Customer.channel_id == norm_phone)
        )
        customer = c_res.scalars().first()
        if not customer:
            customer = Customer(
                name=f"WhatsApp User (+{norm_phone[-4:]})",
                phone=norm_phone,
                channel="whatsapp",
                channel_id=norm_phone
            )
            db.add(customer)
            await db.flush()

        t_res = await db.execute(
            select(Thread).where(Thread.customer_id == customer.id, Thread.channel == "whatsapp")
        )
        thread = t_res.scalars().first()
        if not thread:
            thread = Thread(
                customer_id=customer.id,
                channel="whatsapp",
                status="active",
                ai_enabled=True,
                last_activity_at=datetime.now(timezone.utc)
            )
            db.add(thread)
            await db.flush()

        # Render populated template preview text
        body_preview = template.body_text
        if payload.body_parameters:
            for idx, p in enumerate(payload.body_parameters, start=1):
                body_preview = body_preview.replace(f"{{{{{idx}}}}}", str(p))

        # Save to thread messages
        db.add(Message(
            thread_id=thread.id,
            sender_type="bot",
            content=f"[Template: {template.name}] {body_preview}",
            platform_message_id=msg_id,
            is_draft=False,
            delivery_status="sent"
        ))

        # Log Cost Awareness
        db.add(WhatsAppUsageLog(
            message_id=msg_id,
            thread_id=thread.id,
            customer_id=customer.id,
            recipient_phone=norm_phone,
            category=template.category.lower(),
            direction="outbound",
            template_name=template.name,
            status="sent"
        ))

        await db.commit()
        return {
            "status": "sent",
            "message_id": msg_id,
            "template": template.name,
            "category": template.category,
            "recipient": norm_phone
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to send template: {str(e)}")

# --- Usage & Cost Awareness Endpoints ---

@router.get("/usage/rates")
async def get_rates(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Returns currently configured WhatsApp conversation rates."""
    return await get_whatsapp_rates(db)

@router.put("/usage/rates")
async def update_rates(
    payload: UsageRatesUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Updates WhatsApp message rates based on Meta's current regional pricing page.
    Prevents hardcoded prices by letting merchants configure dynamic rates.
    """
    updates = {
        "whatsapp_rate_marketing": str(payload.rate_marketing),
        "whatsapp_rate_utility": str(payload.rate_utility),
        "whatsapp_rate_service": str(payload.rate_service),
        "whatsapp_rate_authentication": str(payload.rate_authentication),
        "whatsapp_currency": payload.currency.strip().upper()
    }
    for k, v in updates.items():
        res = await db.execute(select(Setting).where(Setting.key == k))
        row = res.scalars().first()
        if row:
            row.value = v
        else:
            db.add(Setting(key=k, value=v, description=f"WhatsApp rate setting {k}"))

    await db.commit()
    return await get_whatsapp_rates(db)

@router.get("/usage/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Calculates current monthly WhatsApp usage count across message categories,
    applying merchant-configured rates to provide an estimated monthly bill.
    """
    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # Query usage logs for this month
    stmt = select(
        WhatsAppUsageLog.category,
        func.count(WhatsAppUsageLog.id)
    ).where(
        WhatsAppUsageLog.timestamp >= start_of_month
    ).group_by(WhatsAppUsageLog.category)

    res = await db.execute(stmt)
    rows = res.all()

    counts = {"service": 0, "utility": 0, "marketing": 0, "authentication": 0}
    for cat, count in rows:
        cat_key = (cat or "").lower()
        if cat_key in counts:
            counts[cat_key] = count

    rates_info = await get_whatsapp_rates(db)
    r_service = rates_info["rate_service"]
    r_utility = rates_info["rate_utility"]
    r_marketing = rates_info["rate_marketing"]
    r_auth = rates_info["rate_authentication"]
    currency = rates_info["currency"]

    cost_service = counts["service"] * r_service
    cost_utility = counts["utility"] * r_utility
    cost_marketing = counts["marketing"] * r_marketing
    cost_auth = counts["authentication"] * r_auth
    total_cost = cost_service + cost_utility + cost_marketing + cost_auth
    total_msgs = sum(counts.values())

    return UsageStatsResponse(
        period=now.strftime("%B %Y"),
        total_messages=total_msgs,
        service_count=counts["service"],
        utility_count=counts["utility"],
        marketing_count=counts["marketing"],
        authentication_count=counts["authentication"],
        rates={
            "service": r_service,
            "utility": r_utility,
            "marketing": r_marketing,
            "authentication": r_auth
        },
        currency=currency,
        estimated_cost=round(total_cost, 2),
        breakdown_cost={
            "service": round(cost_service, 2),
            "utility": round(cost_utility, 2),
            "marketing": round(cost_marketing, 2),
            "authentication": round(cost_auth, 2)
        }
    )
