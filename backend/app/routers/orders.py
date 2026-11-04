import io
import csv
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.schema import Order, OrderItem, Customer, Product, ProductVariant
from app.routers.auth import get_current_admin

router = APIRouter(prefix="/orders", tags=["Orders Management"])

class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_variant_id: Optional[int] = None
    quantity: int
    unit_price: float
    line_total: float
    product_title: Optional[str] = None
    variant_sku: Optional[str] = None

class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    customer_name: str
    customer_phone: Optional[str] = None
    thread_id: Optional[int] = None
    status: str
    payment_method: str = "COD"
    total_amount: float
    delivery_fee: float
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []

class OrderUpdateRequest(BaseModel):
    status: Optional[str] = None
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    payment_method: Optional[str] = None
    delivery_fee: Optional[float] = None

@router.get("", response_model=List[OrderResponse])
async def list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(Order).options(
        selectinload(Order.customer),
        selectinload(Order.items).selectinload(OrderItem.product),
        selectinload(Order.items).selectinload(OrderItem.variant)
    ).order_by(Order.id.desc())

    if status_filter:
        stmt = stmt.where(Order.status == status_filter.strip().lower())

    if search:
        search_term = f"%{search.strip()}%"
        stmt = stmt.join(Customer).where(
            or_(
                Customer.name.ilike(search_term),
                Customer.phone.ilike(search_term),
                Order.delivery_address.ilike(search_term),
                Order.id == int(search.strip()) if search.strip().isdigit() else False
            )
        )

    res = await db.execute(stmt)
    orders = res.scalars().all()

    output = []
    for o in orders:
        items_data = [
            OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_variant_id=item.product_variant_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
                product_title=item.product.title if item.product else None,
                variant_sku=item.variant.sku if item.variant else None
            )
            for item in o.items
        ]
        output.append(
            OrderResponse(
                id=o.id,
                customer_id=o.customer.id,
                customer_name=o.customer.name,
                customer_phone=o.customer.phone,
                thread_id=o.thread_id,
                status=o.status,
                payment_method=getattr(o, "payment_method", "COD") or "COD",
                total_amount=o.total_amount,
                delivery_fee=o.delivery_fee,
                delivery_address=o.delivery_address,
                notes=o.notes,
                created_at=o.created_at,
                updated_at=o.updated_at,
                items=items_data
            )
        )
    return output

@router.get("/export/csv")
async def export_orders_csv(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Exports all store orders formatted as CSV."""
    stmt = select(Order).options(
        selectinload(Order.customer),
        selectinload(Order.items).selectinload(OrderItem.variant),
        selectinload(Order.items).selectinload(OrderItem.product)
    ).order_by(Order.id.desc())

    res = await db.execute(stmt)
    orders = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Order ID", "Customer Name", "Customer Phone", "Delivery Address",
        "Payment Method", "Status", "Items Ordered", "Delivery Fee (BDT)", "Total Amount (BDT)", "Created At"
    ])

    for o in orders:
        items_summary = "; ".join([
            f"{i.product.title if i.product else 'Item'} ({i.variant.sku if i.variant else ''}) x{i.quantity}"
            for i in o.items
        ])
        writer.writerow([
            o.id,
            o.customer.name,
            o.customer.phone or "N/A",
            o.delivery_address or "N/A",
            getattr(o, "payment_method", "COD") or "COD",
            o.status,
            items_summary,
            o.delivery_fee,
            o.total_amount,
            o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else ""
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders_export.csv"}
    )

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_detail(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(Order).options(
        selectinload(Order.customer),
        selectinload(Order.items).selectinload(OrderItem.product),
        selectinload(Order.items).selectinload(OrderItem.variant)
    ).where(Order.id == order_id)
    res = await db.execute(stmt)
    o = res.scalars().first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")

    items_data = [
        OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_variant_id=item.product_variant_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.line_total,
            product_title=item.product.title if item.product else None,
            variant_sku=item.variant.sku if item.variant else None
        )
        for item in o.items
    ]

    return OrderResponse(
        id=o.id,
        customer_id=o.customer.id,
        customer_name=o.customer.name,
        customer_phone=o.customer.phone,
        thread_id=o.thread_id,
        status=o.status,
        payment_method=getattr(o, "payment_method", "COD") or "COD",
        total_amount=o.total_amount,
        delivery_fee=o.delivery_fee,
        delivery_address=o.delivery_address,
        notes=o.notes,
        created_at=o.created_at,
        updated_at=o.updated_at,
        items=items_data
    )

@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    data: OrderUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(Order).options(
        selectinload(Order.customer),
        selectinload(Order.items).selectinload(OrderItem.product),
        selectinload(Order.items).selectinload(OrderItem.variant)
    ).where(Order.id == order_id)
    res = await db.execute(stmt)
    o = res.scalars().first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")

    if data.status is not None:
        valid_statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
        st = data.status.strip().lower()
        if st not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        o.status = st

    if data.delivery_address is not None:
        o.delivery_address = data.delivery_address.strip()
    if data.notes is not None:
        o.notes = data.notes.strip()
    if data.payment_method is not None:
        o.payment_method = data.payment_method.strip()
    if data.delivery_fee is not None:
        # recalculate total
        subtotal = sum(i.line_total for i in o.items)
        o.delivery_fee = data.delivery_fee
        o.total_amount = subtotal + o.delivery_fee

    await db.commit()
    await db.refresh(o)

    items_data = [
        OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_variant_id=item.product_variant_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.line_total,
            product_title=item.product.title if item.product else None,
            variant_sku=item.variant.sku if item.variant else None
        )
        for item in o.items
    ]

    return OrderResponse(
        id=o.id,
        customer_id=o.customer.id,
        customer_name=o.customer.name,
        customer_phone=o.customer.phone,
        thread_id=o.thread_id,
        status=o.status,
        payment_method=getattr(o, "payment_method", "COD") or "COD",
        total_amount=o.total_amount,
        delivery_fee=o.delivery_fee,
        delivery_address=o.delivery_address,
        notes=o.notes,
        created_at=o.created_at,
        updated_at=o.updated_at,
        items=items_data
    )
