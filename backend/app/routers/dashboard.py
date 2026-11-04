from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schema import Message, Thread, Order, AIRun, Customer, WhatsAppUsageLog
from app.routers.auth import get_current_admin

router = APIRouter(prefix="/dashboard", tags=["Executive Dashboard Analytics"])

class DashboardStatsResponse(BaseModel):
    period: str
    total_replies_sent: int
    ai_replies_count: int
    manual_replies_count: int
    ai_share_percentage: float
    manual_share_percentage: float
    total_chats: int
    total_orders: int
    conversion_rate_percentage: float
    total_sales_bdt: float
    avg_response_time_ms: float
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    estimated_token_cost_usd: float
    estimated_token_cost_bdt: float
    channel_breakdown: Dict[str, int]
    recent_activity: List[Dict[str, Any]]

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    period: str = Query("30d", pattern="^(today|7d|30d|all)$"),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Computes key performance indicators:
    - Replies sent
    - AI vs Manual share
    - Chats -> Orders conversion rate
    - Average AI response time
    - AI token consumption & estimated cost
    """
    now = datetime.now(timezone.utc)
    since_date = None
    if period == "today":
        since_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "7d":
        since_date = now - timedelta(days=7)
    elif period == "30d":
        since_date = now - timedelta(days=30)

    # 1. Replies sent (AI vs Manual)
    msg_stmt = select(Message.sender_type, func.count(Message.id)).where(
        and_(
            Message.sender_type.in_(["bot", "admin"]),
            Message.is_draft == False
        )
    )
    if since_date:
        msg_stmt = msg_stmt.where(Message.created_at >= since_date)
    msg_stmt = msg_stmt.group_by(Message.sender_type)
    msg_res = await db.execute(msg_stmt)
    msg_counts = dict(msg_res.all())

    ai_count = msg_counts.get("bot", 0)
    manual_count = msg_counts.get("admin", 0)
    total_replies = ai_count + manual_count

    ai_share = round((ai_count / total_replies * 100), 1) if total_replies > 0 else 0.0
    manual_share = round((manual_count / total_replies * 100), 1) if total_replies > 0 else 0.0

    # 2. Chats -> Orders Conversion
    thread_stmt = select(func.count(Thread.id))
    if since_date:
        thread_stmt = thread_stmt.where(Thread.last_activity_at >= since_date)
    t_res = await db.execute(thread_stmt)
    total_chats = t_res.scalar_one() or 0

    order_stmt = select(func.count(Order.id), func.coalesce(func.sum(Order.total_amount), 0.0)).where(
        Order.status != "cancelled"
    )
    if since_date:
        order_stmt = order_stmt.where(Order.created_at >= since_date)
    o_res = await db.execute(order_stmt)
    order_row = o_res.first()
    total_orders = order_row[0] if order_row else 0
    total_sales = float(order_row[1]) if order_row else 0.0

    conversion_rate = round((total_orders / total_chats * 100), 1) if total_chats > 0 else 0.0

    # 3. Average Response Time & AI Token Costs
    ai_run_stmt = select(
        func.count(AIRun.id),
        func.coalesce(func.avg(AIRun.latency_ms), 0.0),
        func.coalesce(func.sum(AIRun.prompt_tokens), 0),
        func.coalesce(func.sum(AIRun.completion_tokens), 0)
    )
    if since_date:
        ai_run_stmt = ai_run_stmt.where(AIRun.created_at >= since_date)
    run_res = await db.execute(ai_run_stmt)
    run_row = run_res.first()

    avg_latency = round(float(run_row[1]), 1) if run_row else 0.0
    prompt_tokens = int(run_row[2]) if run_row else 0
    comp_tokens = int(run_row[3]) if run_row else 0
    total_tokens = prompt_tokens + comp_tokens

    # Standard token pricing benchmark (e.g. Gemini 1.5 Flash / GPT-4o-mini blended rate)
    cost_usd = round((prompt_tokens * 0.00000015) + (comp_tokens * 0.0000006), 4)
    cost_bdt = round(cost_usd * 122.0, 2)  # USD/BDT conversion rate

    # 4. Channel Breakdown
    ch_stmt = select(Thread.channel, func.count(Thread.id)).group_by(Thread.channel)
    if since_date:
        ch_stmt = ch_stmt.where(Thread.last_activity_at >= since_date)
    ch_res = await db.execute(ch_stmt)
    channel_breakdown = dict(ch_res.all())

    # 5. Recent Activity
    recent_orders_stmt = select(Order).options(selectinload(Order.customer)).order_by(Order.created_at.desc()).limit(5)
    ro_res = await db.execute(recent_orders_stmt)
    recent_orders = ro_res.scalars().all()

    activity = [
        {
            "id": o.id,
            "type": "order_confirmed",
            "title": f"Order #{o.id} - ৳{int(o.total_amount)}",
            "customer_name": o.customer.name if o.customer else "Customer",
            "status": o.status,
            "timestamp": o.created_at.isoformat()
        }
        for o in recent_orders
    ]

    return DashboardStatsResponse(
        period=period,
        total_replies_sent=total_replies,
        ai_replies_count=ai_count,
        manual_replies_count=manual_count,
        ai_share_percentage=ai_share,
        manual_share_percentage=manual_share,
        total_chats=total_chats,
        total_orders=total_orders,
        conversion_rate_percentage=conversion_rate,
        total_sales_bdt=total_sales,
        avg_response_time_ms=avg_latency,
        total_prompt_tokens=prompt_tokens,
        total_completion_tokens=comp_tokens,
        total_tokens=total_tokens,
        estimated_token_cost_usd=cost_usd,
        estimated_token_cost_bdt=cost_bdt,
        channel_breakdown=channel_breakdown,
        recent_activity=activity
    )
