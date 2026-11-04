import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.crypto import decrypt_token
from app.models.schema import (
    WhatsAppBroadcast, WhatsAppTemplate, Customer, WhatsAppConnection, WhatsAppUsageLog
)
from app.routers.auth import get_current_admin
from app.routers.whatsapp import get_whatsapp_rates
from app.services.whatsapp_client import WhatsAppClient

router = APIRouter(prefix="/broadcasts", tags=["WhatsApp Template Broadcasts"])

# --- Schemas ---

class BroadcastAudienceResponse(BaseModel):
    opted_in_count: int
    rates: Dict[str, float]
    currency: str
    marketing_rate_per_recipient: float
    utility_rate_per_recipient: float
    estimated_marketing_cost: float
    estimated_utility_cost: float
    policy_warning: str

class BroadcastCreateRequest(BaseModel):
    template_id: int
    body_parameters: Optional[List[str]] = None
    recipient_filter: str = "all_opted_in"  # "all_opted_in" or list of phone numbers
    specific_phones: Optional[List[str]] = None

class BroadcastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    template_name: str
    status: str
    total_recipients: int
    successful_sends: int
    failed_sends: int
    estimated_cost: float
    actual_cost: float
    currency: str
    parameters_json: Optional[Any] = None
    error_summary: Optional[str] = None
    created_at: datetime

# --- Endpoints ---

@router.get("/audience", response_model=BroadcastAudienceResponse)
async def get_broadcast_audience(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Returns the count of opted-in customers and computes live cost estimates for WhatsApp Broadcasts.
    Highlights Meta WhatsApp Cloud API policies and cost warnings.
    """
    # Count customers opted-in for WhatsApp notifications
    stmt = select(func.count(Customer.id)).where(
        and_(
            Customer.is_opted_in == True,
            Customer.phone.is_not(None)
        )
    )
    res = await db.execute(stmt)
    opted_in = res.scalar_one() or 0

    rates_info = await get_whatsapp_rates(db)
    rates = rates_info.get("rates", {})
    currency = rates_info.get("currency", "BDT")

    m_rate = rates.get("marketing", 5.50)
    u_rate = rates.get("utility", 1.80)

    est_marketing = round(opted_in * m_rate, 2)
    est_utility = round(opted_in * u_rate, 2)

    warning = (
        "POLICY NOTICE: WhatsApp is a private 1-to-1 conversation platform, NOT a social posting feed. "
        "Broadcasts send paid individual template messages to opted-in customers. Meta charges per delivered conversation "
        f"({m_rate} {currency} for Marketing, {u_rate} {currency} for Utility). Charges are billed to your Meta Business Manager."
    )

    return BroadcastAudienceResponse(
        opted_in_count=opted_in,
        rates=rates,
        currency=currency,
        marketing_rate_per_recipient=m_rate,
        utility_rate_per_recipient=u_rate,
        estimated_marketing_cost=est_marketing,
        estimated_utility_cost=est_utility,
        policy_warning=warning
    )

@router.get("", response_model=List[BroadcastResponse])
async def list_broadcasts(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Lists past WhatsApp Template Broadcast campaigns."""
    stmt = select(WhatsAppBroadcast).order_by(WhatsAppBroadcast.created_at.desc())
    res = await db.execute(stmt)
    broadcasts = res.scalars().all()
    return broadcasts

@router.post("", response_model=BroadcastResponse, status_code=status.HTTP_201_CREATED)
async def trigger_broadcast(
    req: BroadcastCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Executes an opt-in WhatsApp Template Broadcast.
    Strictly verifies template is APPROVED, verifies customer opt-in status,
    and logs usage costs to WhatsAppUsageLog.
    """
    # 1. Fetch template
    tpl_res = await db.execute(select(WhatsAppTemplate).where(WhatsAppTemplate.id == req.template_id))
    template = tpl_res.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="WhatsApp Template not found")

    if template.status != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail=f"Template '{template.name}' cannot be broadcasted because its Meta approval status is '{template.status}'."
        )

    # 2. Fetch active WhatsApp connection
    wa_conn_res = await db.execute(select(WhatsAppConnection).where(WhatsAppConnection.is_active == True))
    wa_conn = wa_conn_res.scalars().first()
    if not wa_conn:
        raise HTTPException(
            status_code=400,
            detail="No active WhatsApp Cloud API connection found. Please connect WhatsApp first."
        )

    token = decrypt_token(wa_conn.encrypted_access_token)
    wa_client = WhatsAppClient(phone_number_id=wa_conn.phone_number_id, access_token=token)

    # 3. Target Recipients (Only customers who opted in)
    if req.specific_phones and len(req.specific_phones) > 0:
        c_res = await db.execute(
            select(Customer).where(
                and_(
                    Customer.phone.in_(req.specific_phones),
                    Customer.is_opted_in == True
                )
            )
        )
        recipients = c_res.scalars().all()
    else:
        c_res = await db.execute(
            select(Customer).where(
                and_(
                    Customer.is_opted_in == True,
                    Customer.phone.is_not(None)
                )
            )
        )
        recipients = c_res.scalars().all()

    total_recipients = len(recipients)
    if total_recipients == 0:
        raise HTTPException(
            status_code=400,
            detail="No opted-in customers found matching the broadcast criteria."
        )

    # 4. Calculate Rate & Estimates
    rates_info = await get_whatsapp_rates(db)
    rates = rates_info.get("rates", {})
    currency = rates_info.get("currency", "BDT")
    cat_lower = template.category.lower()
    rate_per_msg = rates.get(cat_lower, 5.50 if cat_lower == "marketing" else 1.80)
    est_cost = round(total_recipients * rate_per_msg, 2)

    # 5. Dispatch Template Messages
    successful = 0
    failed = 0
    error_samples = []

    for cust in recipients:
        try:
            send_res = await wa_client.send_template_message(
                recipient_phone=cust.phone,
                template_name=template.name,
                language_code=template.language,
                body_parameters=req.body_parameters,
                customer_opted_in=cust.is_opted_in
            )
            msg_id = send_res.get("messages", [{}])[0].get("id")

            # Log to WhatsAppUsageLog for cost awareness
            db.add(WhatsAppUsageLog(
                message_id=msg_id,
                customer_id=cust.id,
                recipient_phone=cust.phone,
                category=cat_lower,
                direction="outbound",
                template_name=template.name,
                status="sent"
            ))
            successful += 1
        except Exception as e:
            failed += 1
            if len(error_samples) < 3:
                error_samples.append(f"{cust.phone}: {str(e)}")

    actual_cost = round(successful * rate_per_msg, 2)
    err_summary = " | ".join(error_samples) if error_samples else None

    # 6. Record Broadcast Campaign
    broadcast = WhatsAppBroadcast(
        template_id=template.id,
        template_name=template.name,
        status="completed" if failed == 0 else ("partial" if successful > 0 else "failed"),
        total_recipients=total_recipients,
        successful_sends=successful,
        failed_sends=failed,
        estimated_cost=est_cost,
        actual_cost=actual_cost,
        currency=currency,
        parameters_json=req.body_parameters,
        error_summary=err_summary
    )
    db.add(broadcast)
    await db.commit()
    await db.refresh(broadcast)

    return broadcast
