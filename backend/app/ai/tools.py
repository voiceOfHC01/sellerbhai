import json
from typing import Dict, Any, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.schema import Product, ProductVariant, KBDocument, Order, OrderItem, Customer, Thread

# Tool Schemas for LLM function calling
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search active catalog products and their available variants and prices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords like product name, category, or color"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": "Check current live stock inventory for a product or SKU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id_or_sku": {
                        "type": "string",
                        "description": "The SKU code or product title/id to check stock for"
                    }
                },
                "required": ["product_id_or_sku"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_policy",
            "description": "Retrieve store policies regarding delivery fees, delivery time, returns, refunds, and Cash on Delivery (COD).",
            "parameters": {
                "type": "object",
                "properties": {
                    "policy_type": {
                        "type": "string",
                        "enum": ["delivery", "return", "payment", "general"],
                        "description": "The type of store policy requested"
                    }
                },
                "required": ["policy_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_order_draft",
            "description": "Create a new Cash-on-Delivery draft order when customer provides name, phone, address, and items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Full name of the customer"},
                    "phone": {"type": "string", "description": "Bangladeshi phone number (e.g. 017xxxxxxxx)"},
                    "address": {"type": "string", "description": "Delivery address (Street, Thana, District)"},
                    "items": {
                        "type": "array",
                        "description": "List of items to order with sku or product_id and quantity",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sku": {"type": "string"},
                                "product_id": {"type": "integer"},
                                "quantity": {"type": "integer", "default": 1}
                            }
                        }
                    }
                },
                "required": ["customer_name", "phone", "address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_order",
            "description": "Confirm an existing draft order and reserve inventory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer", "description": "The draft order ID to confirm"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handover_to_human",
            "description": "Transfer the conversation to a human manager/support agent when user complains, negotiates discounts, or asks something outside the knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Detailed explanation of why the thread is handed over to human"
                    }
                },
                "required": ["reason"]
            }
        }
    }
]

# Tool Executors
async def execute_search_products(db: AsyncSession, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    import re
    stmt = select(Product).options(selectinload(Product.variants)).where(Product.is_active == True)
    
    if query:
        stopwords = {
            "bhai", "vai", "koto", "price", "dam", "দাম", "কত", "এর", "কি", "ache", "hobe", "bolben", 
            "what", "is", "the", "of", "your", "ta", "ti", "টা", "টি", "te", "তে", "er",
            "eita", "eitar", "oita", "oitar", "etar", "eta", "ota", "ঐটার", "এটার", "ওটা", "এটা", "ঐটা", "same"
        }
        tokens = [w for w in re.findall(r'[\w\u0980-\u09FF]+', query.lower()) if len(w) >= 2 and w not in stopwords]
        
        if tokens:
            token_conditions = []
            for t in tokens:
                token_conditions.extend([
                    Product.title.ilike(f"%{t}%"),
                    Product.description.ilike(f"%{t}%"),
                    Product.category.ilike(f"%{t}%"),
                    Product.aliases.ilike(f"%{t}%")
                ])
            stmt = stmt.where(or_(*token_conditions))
        else:
            search_term = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Product.title.ilike(search_term),
                    Product.description.ilike(search_term),
                    Product.category.ilike(search_term),
                    Product.aliases.ilike(search_term)
                )
            )
    if category:
        stmt = stmt.where(Product.category.ilike(f"%{category.strip()}%"))

    result = await db.execute(stmt)
    products = result.scalars().all()

    output = []
    for p in products:
        variants_list = [
            {
                "sku": v.sku,
                "title": v.title,
                "price": v.price,
                "stock": v.stock,
                "color": v.color,
                "size": v.size,
                "is_active": v.is_active
            }
            for v in p.variants if v.is_active
        ]
        output.append({
            "id": p.id,
            "title": p.title,
            "category": p.category,
            "base_price": p.base_price,
            "description": p.description,
            "image_url": p.image_url,
            "variants": variants_list
        })
    return output

async def execute_check_stock(db: AsyncSession, product_id_or_sku: str) -> Dict[str, Any]:
    query_str = product_id_or_sku.strip()

    # Try lookup by SKU first
    var_res = await db.execute(
        select(ProductVariant).options(selectinload(ProductVariant.product)).where(ProductVariant.sku.ilike(query_str))
    )
    variant = var_res.scalars().first()
    if variant:
        in_stock = variant.stock > 0
        alternatives = []
        if not in_stock:
            # Look for other variants of same product that have stock > 0
            alt_res = await db.execute(
                select(ProductVariant).where(
                    ProductVariant.product_id == variant.product_id,
                    ProductVariant.id != variant.id,
                    ProductVariant.stock > 0,
                    ProductVariant.is_active == True
                )
            )
            alternatives = [
                {"title": v.title, "sku": v.sku, "price": v.price, "stock": v.stock, "size": v.size, "color": v.color}
                for v in alt_res.scalars().all()
            ]
            if not alternatives and variant.product and variant.product.category:
                cat_res = await db.execute(
                    select(Product).options(selectinload(Product.variants)).where(
                        Product.category == variant.product.category,
                        Product.id != variant.product_id,
                        Product.is_active == True
                    ).limit(3)
                )
                for cp in cat_res.scalars().all():
                    for cv in cp.variants:
                        if cv.stock > 0 and cv.is_active:
                            alternatives.append({"title": f"{cp.title} ({cv.title})", "sku": cv.sku, "price": cv.price, "stock": cv.stock})

        return {
            "found": True,
            "type": "variant",
            "sku": variant.sku,
            "title": variant.title,
            "price": variant.price,
            "stock": variant.stock,
            "in_stock": in_stock,
            "alternatives": alternatives
        }

    # Try lookup by product title
    prod_res = await db.execute(
        select(Product).options(selectinload(Product.variants)).where(
            or_(
                Product.title.ilike(f"%{query_str}%"),
                Product.id == int(query_str) if query_str.isdigit() else False
            )
        )
    )
    product = prod_res.scalars().first()
    if product:
        total_stock = sum(v.stock for v in product.variants if v.is_active)
        in_stock = total_stock > 0
        alternatives = []
        if not in_stock and product.category:
            cat_res = await db.execute(
                select(Product).options(selectinload(Product.variants)).where(
                    Product.category == product.category,
                    Product.id != product.id,
                    Product.is_active == True
                ).limit(3)
            )
            for cp in cat_res.scalars().all():
                for cv in cp.variants:
                    if cv.stock > 0 and cv.is_active:
                        alternatives.append({"title": f"{cp.title} ({cv.title})", "sku": cv.sku, "price": cv.price, "stock": cv.stock})

        return {
            "found": True,
            "type": "product",
            "product_id": product.id,
            "title": product.title,
            "price": product.base_price,
            "total_stock": total_stock,
            "in_stock": in_stock,
            "variants": [{"sku": v.sku, "title": v.title, "stock": v.stock, "price": v.price} for v in product.variants],
            "alternatives": alternatives
        }

    return {"found": False, "message": f"Product or SKU '{product_id_or_sku}' not found."}

async def execute_get_policy(db: AsyncSession, policy_type: str) -> Dict[str, Any]:
    stmt = select(KBDocument).where(
        KBDocument.is_active == True,
        or_(
            KBDocument.doc_type == "policy",
            KBDocument.doc_type == "faq"
        ),
        or_(
            KBDocument.title.ilike(f"%{policy_type}%"),
            KBDocument.content.ilike(f"%{policy_type}%")
        )
    )
    res = await db.execute(stmt)
    docs = res.scalars().all()

    if docs:
        return {
            "policy_type": policy_type,
            "matched_policies": [{"title": d.title, "content": d.content} for d in docs]
        }

    # Fallback to standard delivery/payment policy
    return {
        "policy_type": policy_type,
        "content": "ঢাকার ভেতরে ডেলিভারি চার্জ ৮০ টাকা (১-২ কার্যদিবস), ঢাকার বাইরে ১৫০ টাকা (২-৪ কার্যদিবস)। পণ্য হাতে পেয়ে মূল্য পরিশোধ (Cash on Delivery) করতে পারবেন।"
    }

async def execute_create_order_draft(
    db: AsyncSession,
    customer_name: str,
    phone: str,
    address: str,
    items: Optional[List[Dict[str, Any]]] = None,
    payment_method: str = "COD",
    status: str = "pending",
    thread_id: Optional[int] = None
) -> Dict[str, Any]:
    # 1. Stock check on all items before creating order
    if items:
        for item in items:
            sku = item.get("sku")
            p_id = item.get("product_id")
            qty = max(1, int(item.get("quantity", 1)))

            var_obj = None
            if sku:
                vres = await db.execute(
                    select(ProductVariant).options(selectinload(ProductVariant.product)).where(ProductVariant.sku.ilike(sku.strip()))
                )
                var_obj = vres.scalars().first()

            if var_obj and var_obj.stock < qty:
                # Find in-stock alternatives
                alt_res = await db.execute(
                    select(ProductVariant).where(
                        ProductVariant.product_id == var_obj.product_id,
                        ProductVariant.id != var_obj.id,
                        ProductVariant.stock > 0,
                        ProductVariant.is_active == True
                    )
                )
                alternatives = [
                    {"title": v.title, "sku": v.sku, "price": v.price, "stock": v.stock, "size": v.size, "color": v.color}
                    for v in alt_res.scalars().all()
                ]
                return {
                    "success": False,
                    "out_of_stock": True,
                    "message": f"Sorry, '{var_obj.title}' is currently out of stock (available: {var_obj.stock}).",
                    "alternatives": alternatives
                }

    # Find or create customer
    clean_phone = phone.strip()
    res = await db.execute(select(Customer).where(Customer.phone == clean_phone))
    customer = res.scalars().first()
    if not customer:
        customer = Customer(name=customer_name.strip(), phone=clean_phone, address=address.strip())
        db.add(customer)
        await db.flush()
    else:
        customer.name = customer_name.strip()
        customer.address = address.strip()

    # Determine delivery fee based on address
    is_dhaka = "dhaka" in address.lower() or "ঢাকা" in address
    delivery_fee = 80.0 if is_dhaka else 150.0

    # Create Order
    order = Order(
        customer_id=customer.id,
        thread_id=thread_id,
        status=status,
        payment_method=payment_method,
        delivery_address=address.strip(),
        delivery_fee=delivery_fee,
        total_amount=delivery_fee,
        notes=f"Order created by AI assistant ({payment_method})"
    )
    db.add(order)
    await db.flush()

    total_items_amount = 0.0
    order_items_details = []

    # If items provided, add order items and deduct stock
    if items:
        for item in items:
            sku = item.get("sku")
            p_id = item.get("product_id")
            qty = max(1, int(item.get("quantity", 1)))

            var_obj = None
            if sku:
                vres = await db.execute(select(ProductVariant).where(ProductVariant.sku.ilike(sku.strip())))
                var_obj = vres.scalars().first()

            if var_obj:
                unit_price = var_obj.price
                line_total = unit_price * qty
                total_items_amount += line_total
                var_obj.stock = max(0, var_obj.stock - qty)  # reserve stock
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=var_obj.product_id,
                    product_variant_id=var_obj.id,
                    quantity=qty,
                    unit_price=unit_price,
                    line_total=line_total
                )
                db.add(order_item)
                order_items_details.append({
                    "title": var_obj.title,
                    "sku": var_obj.sku,
                    "quantity": qty,
                    "price": unit_price,
                    "line_total": line_total
                })
            elif p_id:
                pres = await db.execute(select(Product).where(Product.id == int(p_id)))
                prod_obj = pres.scalars().first()
                if prod_obj:
                    unit_price = prod_obj.base_price
                    line_total = unit_price * qty
                    total_items_amount += line_total
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=prod_obj.id,
                        product_variant_id=None,
                        quantity=qty,
                        unit_price=unit_price,
                        line_total=line_total
                    )
                    db.add(order_item)
                    order_items_details.append({
                        "title": prod_obj.title,
                        "quantity": qty,
                        "price": unit_price,
                        "line_total": line_total
                    })

    order.total_amount = total_items_amount + delivery_fee
    await db.commit()

    return {
        "success": True,
        "order_id": order.id,
        "status": order.status,
        "customer_name": customer.name,
        "phone": customer.phone,
        "delivery_address": order.delivery_address,
        "payment_method": order.payment_method,
        "items": order_items_details,
        "subtotal": total_items_amount,
        "delivery_fee": delivery_fee,
        "total_amount": order.total_amount
    }

async def execute_confirm_order(db: AsyncSession, order_id: int) -> Dict[str, Any]:
    res = await db.execute(
        select(Order).options(selectinload(Order.items).selectinload(OrderItem.variant)).where(Order.id == order_id)
    )
    order = res.scalars().first()
    if not order:
        return {"success": False, "message": f"Order #{order_id} not found."}

    # Deduct stock
    for item in order.items:
        if item.variant:
            item.variant.stock = max(0, item.variant.stock - item.quantity)

    order.status = "confirmed"
    await db.commit()

    return {
        "success": True,
        "order_id": order.id,
        "status": "confirmed",
        "total_amount": order.total_amount,
        "message": f"Order #{order.id} has been confirmed successfully."
    }

async def execute_handover_to_human(db: AsyncSession, reason: str, thread_id: Optional[int] = None) -> Dict[str, Any]:
    if thread_id:
        res = await db.execute(select(Thread).where(Thread.id == thread_id))
        thread = res.scalars().first()
        if thread:
            thread.status = "human_takeover"
            thread.handover_reason = reason
            await db.commit()

    return {
        "handover_triggered": True,
        "reason": reason,
        "status": "human_takeover",
        "message": "Human agent alerted. Bot is paused for this thread."
    }
