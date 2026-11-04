import time
import json
import re
from typing import Dict, Any, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.schema import Setting, Thread, Message, AIRun, Customer, Product, ProductVariant
from app.ai.language_detector import detect_language
from app.ai.providers import get_llm_provider
from app.ai.rag import retrieve_relevant_knowledge
from app.ai.guardrails import detect_prompt_injection, get_injection_defense_response
from app.ai.prompts import (
    build_system_prompt, PROMPT_VERSION, format_price, to_bangla_digits, to_english_digits
)
from app.ai.self_check import perform_draft_self_check
from app.ai.order_extractor import (
    extract_bd_phone, is_valid_bd_phone, extract_payment_method, 
    extract_address, extract_customer_name, extract_quantity
)
from app.ai.tools import (
    TOOL_DEFINITIONS,
    execute_search_products,
    execute_check_stock,
    execute_get_policy,
    execute_create_order_draft,
    execute_confirm_order,
    execute_handover_to_human
)
from app.core.config import settings

async def get_setting_value(db: AsyncSession, key: str, default: str) -> str:
    res = await db.execute(select(Setting).where(Setting.key == key))
    s = res.scalars().first()
    return s.value if s else default

async def process_chat_message(
    db: AsyncSession,
    customer_message: str,
    thread_id: Optional[int] = None,
    customer_name: Optional[str] = None,
    customer_phone: Optional[str] = None
) -> Dict[str, Any]:
    start_time = time.time()
    raw_text = customer_message.strip()

    # 1. Detect language
    lang = detect_language(raw_text)
    lower = raw_text.lower()

    # 2. Retrieve or create Thread & Customer
    customer = None
    thread = None
    if thread_id:
        res = await db.execute(select(Thread).where(Thread.id == thread_id))
        thread = res.scalars().first()

    if not thread:
        c_name = customer_name or "Test Customer"
        c_phone = customer_phone or "01700000000"
        customer = Customer(name=c_name, phone=c_phone, channel="web_test")
        db.add(customer)
        await db.flush()

        thread = Thread(customer_id=customer.id, channel="web_test", status="active", metadata_json={})
        db.add(thread)
        await db.flush()

    thread_meta = thread.metadata_json or {}

    # If thread is already handed over to human, return notification
    if thread.status == "human_takeover":
        return {
            "reply": "আপনার চ্যাটটি বর্তমানে একজন মানব প্রতিনিধির (Human Agent) কাছে ট্রান্সফার করা আছে। অনুগ্রহ করে কিছুক্ষণ অপেক্ষা করুন, আমাদের প্রতিনিধি খুব শীঘ্রই যোগাযোগ করবেন।",
            "detected_language": lang,
            "retrieved_sources": [],
            "tool_calls": [],
            "handover_triggered": True,
            "thread_status": "human_takeover",
            "thread_id": thread.id
        }

    # Save user incoming message
    user_msg_record = Message(
        thread_id=thread.id,
        sender_type="customer",
        content=raw_text,
        language=lang
    )
    db.add(user_msg_record)
    await db.flush()

    # 3. Prompt-Injection & Adversarial Defense Guardrail
    is_injection, injection_tag = detect_prompt_injection(raw_text)
    if is_injection:
        defense_reply = get_injection_defense_response(lang)
        bot_msg = Message(thread_id=thread.id, sender_type="bot", content=defense_reply, language=lang)
        db.add(bot_msg)
        await db.commit()
        return {
            "reply": defense_reply,
            "detected_language": lang,
            "retrieved_sources": [],
            "tool_calls": [{"tool": "prompt_injection_defense", "result": f"Blocked attempt: {injection_tag}"}],
            "handover_triggered": False,
            "thread_status": thread.status,
            "thread_id": thread.id,
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }

    # 4. Honest Bot Disclosure Check
    is_bot_question = any(w in lower for w in [
        "are you a bot", "are you bot", "are you ai", "are you robot", 
        "tumi ki bot", "apni ki bot", "tumi ki robot", "apni ki robot", 
        "bot naki", "রোবট নাকি", "বট নাকি", "আপনি কি মানুষ", "tumi ki manush", "রোবট"
    ])
    if is_bot_question:
        store_name_val = await get_setting_value(db, "store_name", settings.STORE_NAME)
        if lang == "bangla":
            bot_disclosure = f"জি, আমি {store_name_val}-এর একটি অটোমেটেড এআই সহকারী। আপনি চাইলে যেকোনো সময় আমাদের মানব প্রতিনিধির সাথেও কথা বলতে পারেন।"
        elif lang == "banglish":
            bot_disclosure = f"Ji, ami {store_name_val} er ekjon automated AI assistant. Apni chaile je kono shomoy amader human agent er sathe kotha bolte paren."
        else:
            bot_disclosure = f"Yes, I am an automated AI assistant for {store_name_val}. I can also connect you with a human representative anytime."

        bot_msg = Message(thread_id=thread.id, sender_type="bot", content=bot_disclosure, language=lang)
        db.add(bot_msg)
        await db.commit()
        return {
            "reply": bot_disclosure,
            "detected_language": lang,
            "retrieved_sources": [],
            "tool_calls": [{"tool": "bot_disclosure", "result": "honest_disclosure"}],
            "handover_triggered": False,
            "thread_status": thread.status,
            "thread_id": thread.id,
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }

    # 4b. Handover Trigger Checks: Human request, Complaint, Refund, Dispute
    complaint_keywords = [
        "manager", "human", "agent", "kotha bolbo", "officer", "representative",
        "complain", "complaint", "refund", "taka ferot", "ferot chai", "dispute", "cheat",
        "fakibaj", "bhul jinish", "baje service", "churi", "kharap service",
        "ম্যানেজার", "প্রতিনিধি", "এজেন্ট", "অভিযোগ", "ফেরত", "টাকা ফেরত", "মামলা",
        "ছেঁড়া", "ভুল সাইজ", "এক্সচেঞ্জ", "নষ্ট", "বাজে", "অপদার্থ", "বাটপার", "প্রতারক"
    ]
    if any(k in lower for k in complaint_keywords) or ("manush" in lower and any(v in lower for v in ["chai", "bolbo", "kotha"])) or ("মানুষ" in lower and any(v in lower for v in ["চাই", "বলব", "কথা", "দিন"])):
        handover_res = await execute_handover_to_human(
            db, reason=f"Customer trigger: {raw_text[:50]}", thread_id=thread.id
        )
        thread.status = "human_takeover"
        thread.ai_enabled = False
        await db.commit()

        if lang == "bangla":
            reply_text = "আপনার বিষয়টি আমাদের মানব প্রতিনিধির কাছে হস্তান্তর করা হয়েছে। আমাদের একজন কাস্টমার কেয়ার অফিসার খুব শীঘ্রই আপনার সাথে যোগাযোগ করবেন।"
        elif lang == "banglish":
            reply_text = "Apnar request ta amader human agent er kache handover kora hoyeche. Khub shighroi ekjon representative apnake call/message korben."
        else:
            reply_text = "Your request has been escalated to a human agent. A representative will connect with you shortly."

        bot_msg = Message(thread_id=thread.id, sender_type="bot", content=reply_text, language=lang)
        db.add(bot_msg)
        await db.commit()
        return {
            "reply": reply_text,
            "detected_language": lang,
            "retrieved_sources": [],
            "tool_calls": [{"tool": "handover_to_human", "arguments": {"reason": raw_text}, "result": handover_res}],
            "handover_triggered": True,
            "thread_status": "human_takeover",
            "thread_id": thread.id,
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }

    # 5. Order State Machine: Multi-Step conversational order collection (ONE question at a time)
    order_flow = thread_meta.get("order_flow", {})
    order_intent = any(k in lower for k in [
        "order", "nibo", "kinbo", "lagbe", "pathan", "send", "korte chai", "confirm", "হাঁ", "হ্যাঁ", "yes", "অর্ডার", "নিব", "নিবো", "কিনব", "পাঠান"
    ]) or order_flow.get("active", False)

    if order_intent:
        if not order_flow.get("active"):
            order_flow = {
                "active": True,
                "product_title": None,
                "sku": None,
                "variant_id": None,
                "product_id": None,
                "quantity": 1,
                "price": 0.0,
                "name": None,
                "phone": None,
                "address": None,
                "payment_method": None,
                "awaiting_confirmation": False
            }

        # Extract whatever slots might be present in the message
        # A. Product match if not yet selected
        if not order_flow.get("product_title"):
            p_res = await db.execute(select(Product).options(selectinload(Product.variants)).where(Product.is_active == True))
            for p in p_res.scalars().all():
                p_tokens = p.title.lower().split()
                aliases_tokens = [a.strip().lower() for a in (p.aliases or "").split(",") if a.strip()]
                is_title_match = any(tok in lower for tok in p_tokens if len(tok) > 3) or p.category.lower() in lower
                is_alias_match = any(a in lower for a in aliases_tokens)
                if is_title_match or is_alias_match:
                    order_flow["product_title"] = p.title
                    order_flow["product_id"] = p.id
                    order_flow["price"] = p.base_price
                    # Match variant if color/size mentioned
                    for v in p.variants:
                        if (v.size and v.size.lower() in lower) or (v.color and v.color.lower() in lower) or (v.sku.lower() in lower):
                            order_flow["sku"] = v.sku
                            order_flow["variant_id"] = v.id
                            order_flow["price"] = v.price
                            order_flow["variant_title"] = v.title
                            break
                    if not order_flow.get("sku") and p.variants:
                        # Select first variant
                        order_flow["sku"] = p.variants[0].sku
                        order_flow["variant_id"] = p.variants[0].id
                        order_flow["price"] = p.variants[0].price
                        order_flow["variant_title"] = p.variants[0].title
                    break

        # B. Quantity
        qty = extract_quantity(raw_text)
        if qty > 1:
            order_flow["quantity"] = qty

        # C. Name
        extracted_name = extract_customer_name(raw_text)
        if extracted_name and not order_flow.get("name"):
            order_flow["name"] = extracted_name

        # D. Phone
        extracted_phone = extract_bd_phone(raw_text)
        if extracted_phone:
            if is_valid_bd_phone(extracted_phone):
                order_flow["phone"] = extracted_phone
            else:
                # Ask specifically for valid phone
                reply_text = "অনুগ্রহ করে আপনার সঠিক ১১ ডিজিটের বাংলাদেশী মোবাইল নম্বরটি দিন (যেমন: 017XXXXXXXX)।"
                bot_msg = Message(thread_id=thread.id, sender_type="bot", content=reply_text, language=lang)
                db.add(bot_msg)
                await db.commit()
                return {
                    "reply": reply_text,
                    "detected_language": lang,
                    "retrieved_sources": [],
                    "tool_calls": [],
                    "handover_triggered": False,
                    "thread_status": thread.status,
                    "thread_id": thread.id
                }

        # E. Address
        extracted_addr = extract_address(raw_text)
        if extracted_addr and not order_flow.get("address"):
            order_flow["address"] = extracted_addr

        # F. Payment Method
        extracted_payment = extract_payment_method(raw_text)
        if extracted_payment and not order_flow.get("payment_method"):
            order_flow["payment_method"] = extracted_payment

        # Handle Confirmation Response
        if order_flow.get("awaiting_confirmation"):
            if any(w in lower for w in ["yes", "ha", "hacche", "confirm", "হ্যাঁ", "হাঁ", "ঠিক আছে", "thik ache", "ok"]):
                # Customer confirmed: Perform Honest Stock Check before creating order
                variant_obj = None
                if order_flow.get("sku"):
                    vres = await db.execute(select(ProductVariant).where(ProductVariant.sku == order_flow["sku"]))
                    variant_obj = vres.scalars().first()

                if variant_obj and variant_obj.stock < order_flow["quantity"]:
                    # OUT OF STOCK HONESTY
                    alt_res = await db.execute(
                        select(ProductVariant).where(
                            ProductVariant.product_id == variant_obj.product_id,
                            ProductVariant.id != variant_obj.id,
                            ProductVariant.stock > 0
                        )
                    )
                    alts = alt_res.scalars().all()
                    alt_str = ", ".join([f"{a.title} (৳{a.price})" for a in alts]) if alts else "একই ক্যাটাগরির অন্য পণ্য"

                    reply_text = (
                        f"দুঃখিত! আপনার নির্বাচিত '{variant_obj.title}' বর্তমানে স্টক আউট হয়ে গেছে। "
                        f"তবে আমাদের কাছে বিকল্প হিসেবে রয়েছে: {alt_str}। আপনি কি এগুলোর কোনোটি দেখতে চান?"
                    )
                    order_flow["active"] = False
                    thread_meta["order_flow"] = order_flow
                    thread.metadata_json = thread_meta
                    bot_msg = Message(thread_id=thread.id, sender_type="bot", content=reply_text, language=lang)
                    db.add(bot_msg)
                    await db.commit()
                    return {
                        "reply": reply_text,
                        "detected_language": lang,
                        "retrieved_sources": [],
                        "tool_calls": [{"tool": "check_stock", "result": {"out_of_stock": True, "alternatives": alt_str}}],
                        "handover_triggered": False,
                        "thread_status": thread.status,
                        "thread_id": thread.id
                    }

                # Stock is available: create pending order
                order_res = await execute_create_order_draft(
                    db=db,
                    customer_name=order_flow.get("name") or "Valued Customer",
                    phone=order_flow.get("phone") or "01700000000",
                    address=order_flow.get("address") or "Dhaka",
                    items=[{"sku": order_flow["sku"], "quantity": order_flow["quantity"]}],
                    payment_method=order_flow.get("payment_method") or "COD",
                    status="pending",
                    thread_id=thread.id
                )

                order_flow["active"] = False
                thread_meta["order_flow"] = {}
                thread.metadata_json = thread_meta

                if lang == "bangla":
                    reply_text = (
                        f"🎉 ধন্যবাদ! আপনার অর্ডারটি সফলভাবে গ্রহণ করা হয়েছে (Order #{order_res['order_id']})।\n"
                        f"পণ্য: {order_flow.get('product_title')}\n"
                        f"পরিমাণ: {order_flow.get('quantity')} টি\n"
                        f"মোট প্রদেয়: ৳{order_res['total_amount']} ({order_res['payment_method']})\n"
                        f"আমাদের প্রতিনিধি খুব শীঘ্রই ডেলিভারির জন্য কল করবেন।"
                    )
                else:
                    reply_text = (
                        f"🎉 Thank you! Your order has been placed successfully (Order #{order_res['order_id']}).\n"
                        f"Item: {order_flow.get('product_title')}\n"
                        f"Total: ৳{order_res['total_amount']} ({order_res['payment_method']})\n"
                        f"We will dispatch your order shortly."
                    )

                bot_msg = Message(thread_id=thread.id, sender_type="bot", content=reply_text, language=lang)
                db.add(bot_msg)
                await db.commit()
                return {
                    "reply": reply_text,
                    "detected_language": lang,
                    "retrieved_sources": [],
                    "tool_calls": [{"tool": "create_order_draft", "result": order_res}],
                    "handover_triggered": False,
                    "thread_status": thread.status,
                    "thread_id": thread.id
                }

        # Step-by-Step: Ask ONE Question at a time
        missing_question = None

        if not order_flow.get("product_title"):
            missing_question = "আপনি কোন পণ্যটি (পোলো শার্ট, পাঞ্জাবি, বা ওয়ালেট) এবং কোন সাইজ/কালার নিতে চান বলবেন কি?"
        elif not order_flow.get("name"):
            missing_question = f"নিশ্চয়ই! {order_flow.get('product_title')} অর্ডার করার জন্য আপনার শুভ নামটি কি?"
        elif not order_flow.get("phone"):
            missing_question = "আপনার ১১ ডিজিটের মোবাইল নম্বরটি দিন (যেমন: 017XXXXXXXX)।"
        elif not order_flow.get("address"):
            missing_question = "আপনার পূর্ণ ডেলিভারি ঠিকানা (বাসা/রোড নম্বর, এলাকা, জেলা) লিখে দিন।"
        elif not order_flow.get("payment_method"):
            missing_question = "পেমেন্ট কীভাবে করতে চান? ক্যাশ অন ডেলিভারি (COD), বিকাশ (bKash) নাকি নগদ (Nagad)?"
        else:
            # All fields collected -> Show Summary & Ask Confirmation!
            order_flow["awaiting_confirmation"] = True
            is_dhaka = "dhaka" in (order_flow.get("address") or "").lower() or "ঢাকা" in (order_flow.get("address") or "")
            delivery_fee = 80.0 if is_dhaka else 150.0
            subtotal = (order_flow.get("price") or 850.0) * order_flow.get("quantity", 1)
            total = subtotal + delivery_fee

            summary_msg = (
                f"📦 আপনার অর্ডারের বিবরণ:\n"
                f"• পণ্য: {order_flow.get('product_title')} ({order_flow.get('variant_title') or order_flow.get('sku')})\n"
                f"• পরিমাণ: {order_flow.get('quantity')} টি (৳{subtotal})\n"
                f"• ডেলিভারি চার্জ: ৳{delivery_fee} ({'ঢাকার ভেতরে' if is_dhaka else 'ঢাকার বাইরে'})\n"
                f"• মোট প্রদেয়: ৳{total}\n"
                f"• নাম: {order_flow.get('name')}\n"
                f"• মোবাইল: {order_flow.get('phone')}\n"
                f"• ঠিকানা: {order_flow.get('address')}\n"
                f"• পেমেন্ট: {order_flow.get('payment_method')}\n\n"
                f"অর্ডারটি কনফার্ম করতে অনুগ্রহ করে 'হ্যাঁ / Confirm' লিখুন।"
            )
            missing_question = summary_msg

        thread_meta["order_flow"] = order_flow
        thread.metadata_json = thread_meta
        bot_msg = Message(thread_id=thread.id, sender_type="bot", content=missing_question, language=lang)
        db.add(bot_msg)
        await db.commit()
        return {
            "reply": missing_question,
            "detected_language": lang,
            "retrieved_sources": [],
            "tool_calls": [{"tool": "order_step_collector", "state": order_flow}],
            "handover_triggered": False,
            "thread_status": thread.status,
            "thread_id": thread.id,
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }

    # 6. Conversation Context & Pronoun Resolution
    msg_history_res = await db.execute(
        select(Message).where(Message.thread_id == thread.id).order_by(Message.id.desc()).limit(10)
    )
    prev_messages = list(reversed(msg_history_res.scalars().all()))

    pronoun_tokens = ["eita", "eitar", "oita", "oitar", "etar", "eta", "ota", "ঐটার", "এটার", "ওটা", "এটা", "ঐটা", "same"]
    last_product_title = thread_meta.get("last_discussed_product_title")
    if not last_product_title:
        for pm in reversed(prev_messages[:-1]):
            for p_cand in ["Polo", "Panjabi", "Wallet", "Shirt", "পাঞ্জাবি", "পোলো", "শার্ট"]:
                if p_cand.lower() in pm.content.lower():
                    last_product_title = p_cand
                    break
            if last_product_title:
                break

    rag_query = raw_text
    if any(p in lower for p in pronoun_tokens) and last_product_title:
        rag_query = f"{raw_text} {last_product_title}"

    # Standard RAG Knowledge Retrieval
    retrieved_chunks = await retrieve_relevant_knowledge(db, query=rag_query, top_k=4)
    retrieved_context = "\n\n".join(c["chunk_text"] for c in retrieved_chunks)
    max_confidence = max([c["score"] for c in retrieved_chunks]) if retrieved_chunks else 0.0

    # 7. Check 2 Failed Understandings Rule
    failed_count = thread_meta.get("failed_understanding_count", 0)
    # If confidence is very low (< 0.20) and no keywords match store domain
    is_domain_match = any(w in lower for w in ["price", "dam", "koto", "shirt", "panjabi", "wallet", "delivery", "policy", "stock", "size", "color", "taka"])
    if max_confidence < 0.20 and not is_domain_match:
        failed_count += 1
        thread_meta["failed_understanding_count"] = failed_count
        thread.metadata_json = thread_meta

        if failed_count >= 2:
            # Trigger Handover
            handover_res = await execute_handover_to_human(
                db, reason="2 consecutive failed understandings. Low confidence domain match.", thread_id=thread.id
            )
            thread.status = "human_takeover"
            thread.ai_enabled = False
            await db.commit()

            reply_text = (
                "দুঃখিত, আপনার বিষয়টি পুরোপুরি বুঝতে পারছি না। "
                "আমি চ্যাটটি আমাদের মানব প্রতিনিধির (Human Agent) কাছে ট্রান্সফার করে দিয়েছি। তিনি শীঘ্রই যোগাযোগ করবেন।"
            )
            bot_msg = Message(thread_id=thread.id, sender_type="bot", content=reply_text, language=lang)
            db.add(bot_msg)
            await db.commit()
            return {
                "reply": reply_text,
                "detected_language": lang,
                "retrieved_sources": retrieved_chunks,
                "tool_calls": [{"tool": "handover_to_human", "arguments": {"reason": "2 failed understandings"}}],
                "handover_triggered": True,
                "thread_status": "human_takeover",
                "thread_id": thread.id,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
    else:
        # Reset failed count on good comprehension
        thread_meta["failed_understanding_count"] = 0
        thread.metadata_json = thread_meta

    # 8. Fetch dynamic brand settings & system prompt
    store_name = await get_setting_value(db, "store_name", settings.STORE_NAME)
    brand_tone = await get_setting_value(db, "brand_tone", settings.STORE_TONE)
    price_format = await get_setting_value(db, "price_format", settings.PRICE_FORMAT)
    custom_template = await get_setting_value(db, "ai_system_prompt_template", "")
    fast_model = await get_setting_value(db, "fast_llm_model", settings.FAST_LLM_MODEL)
    reply_model = await get_setting_value(db, "reply_llm_model", settings.REPLY_LLM_MODEL)

    # 9. LLM Execution with Context History
    formatted_messages = [
        {"role": "user" if m.sender_type == "customer" else "assistant", "content": m.content}
        for m in prev_messages
    ]

    has_prior_greeting = any(
        m.sender_type == "bot" and ("সালাম" in m.content or "hello" in m.content.lower() or "স্বাগতম" in m.content)
        for m in prev_messages[:-1]
    )
    customer_used_bangla_digits = any(c in "০১২৩৪৫৬৭৮৯" for c in raw_text)

    system_prompt = build_system_prompt(
        store_name=store_name,
        brand_tone=brand_tone,
        retrieved_context=retrieved_context,
        detected_language=lang,
        has_prior_greeting=has_prior_greeting,
        customer_used_bangla_digits=customer_used_bangla_digits,
        price_format=price_format,
        custom_template=custom_template if custom_template.strip() else None
    )

    llm = get_llm_provider(model_name=reply_model)
    tool_calls_executed = []
    handover_triggered = False

    first_response = await llm.generate(
        messages=formatted_messages,
        tools=TOOL_DEFINITIONS,
        system_prompt=system_prompt,
        temperature=0.2
    )

    final_reply_text = first_response.content or ""

    if first_response.tool_calls:
        formatted_messages.append({"role": "assistant", "content": first_response.content or ""})

        for tc in first_response.tool_calls:
            t_name = tc.get("name")
            args = tc.get("arguments", {})
            t_output = {}

            if t_name == "search_products":
                search_q = args.get("query", "")
                q_lower = search_q.lower()
                pronoun_words = {"eita", "eitar", "oita", "oitar", "etar", "eta", "ota", "ঐটার", "এটার", "ওটা", "এটা", "ঐটা", "same"}
                q_tokens = set(re.findall(r'[\w\u0980-\u09FF]+', q_lower))
                if (q_tokens.intersection(pronoun_words) or not (q_tokens - pronoun_words - {"price", "dam", "koto", "bolben", "দাম", "কত", "ta", "er"})) and last_product_title:
                    search_q = last_product_title
                t_output = await execute_search_products(db, query=search_q, category=args.get("category"))
            elif t_name == "check_stock":
                t_output = await execute_check_stock(db, product_id_or_sku=args.get("product_id_or_sku", ""))
            elif t_name == "get_policy":
                t_output = await execute_get_policy(db, policy_type=args.get("policy_type", "delivery"))
            elif t_name == "create_order_draft":
                t_output = await execute_create_order_draft(
                    db,
                    customer_name=args.get("customer_name", "Customer"),
                    phone=args.get("phone", "01700000000"),
                    address=args.get("address", ""),
                    items=args.get("items", []),
                    payment_method=args.get("payment_method", "COD"),
                    status="pending",
                    thread_id=thread.id
                )
            elif t_name == "confirm_order":
                t_output = await execute_confirm_order(db, order_id=int(args.get("order_id", 0)))
            elif t_name == "handover_to_human":
                t_output = await execute_handover_to_human(db, reason=args.get("reason", "Customer request"), thread_id=thread.id)
                handover_triggered = True

            tool_calls_executed.append({
                "tool": t_name,
                "arguments": args,
                "result": t_output
            })
            formatted_messages.append({
                "role": "tool",
                "name": t_name,
                "content": json.dumps(t_output, ensure_ascii=False)
            })

        if handover_triggered:
            if lang == "bangla":
                final_reply_text = "আপনার বিষয়টি আমাদের মানব প্রতিনিধির কাছে হস্তান্তর করা হয়েছে। খুব শীঘ্রই আমাদের প্রতিনিধি যোগাযোগ করবেন।"
            elif lang == "banglish":
                final_reply_text = "Apnar request ta amader human representative er kache handover kora hoyeche. Khub shighroi contact korben."
            else:
                final_reply_text = "Your request has been forwarded to a human representative. Someone will contact you shortly."
        else:
            followup = await llm.generate(
                messages=formatted_messages,
                system_prompt=system_prompt,
                temperature=0.2
            )
            if followup.content:
                final_reply_text = followup.content

    if not final_reply_text:
        greeting_prefix = "" if has_prior_greeting else f"Assalamu Alaikum! {store_name} এ স্বাগতম। "
        final_reply_text = f"{greeting_prefix}আপনি কোন পণ্য সম্পর্কে জানতে চান?"

    # 10. Self-Check Guardrail Before Sending
    p_prices_res = await db.execute(select(Product.base_price).where(Product.is_active == True))
    allowed_numbers = {int(p) for p in p_prices_res.scalars().all() if p}
    v_prices_res = await db.execute(select(ProductVariant.price, ProductVariant.stock).where(ProductVariant.is_active == True))
    for v_p, v_s in v_prices_res.all():
        if v_p: allowed_numbers.add(int(v_p))
        if v_s is not None: allowed_numbers.add(int(v_s))

    # Standard allowed delivery fees & mock catalog prices
    allowed_numbers.update([60, 80, 120, 150, 850, 890, 950, 1250, 1500])

    is_blocked = False
    blocked_reason = None
    is_valid, clean_reply, fail_reason = perform_draft_self_check(
        draft_reply=final_reply_text,
        allowed_numbers=allowed_numbers,
        detected_language=lang,
        customer_message=raw_text
    )

    if not is_valid:
        is_blocked = True
        blocked_reason = fail_reason
        if "ungrounded" in (fail_reason or "").lower():
            if lang == "bangla":
                final_reply_text = "আমাদের ক্যাটালগে এই মূল্যে কোনো অফার বা পণ্য নির্ধারিত নেই। আমাদের সকল পণ্যের মূল্য ফিক্সড। আপনি চাইলে আমাদের মানব প্রতিনিধির সাথে কথা বলতে পারেন।"
            elif lang == "banglish":
                final_reply_text = "Amader catalog e ei price e kono offer nei. Sob product er price fixed. Apni chaile representative er sathe kotha bolte paren."
            else:
                final_reply_text = "This price is not in our official catalog. All prices are fixed. Let me connect you with a representative."
            handover_triggered = True
            thread.status = "human_takeover"
            thread.ai_enabled = False
        else:
            final_reply_text = clean_reply
    else:
        final_reply_text = clean_reply

    bot_msg_record = Message(
        thread_id=thread.id,
        sender_type="bot",
        content=final_reply_text,
        language=lang
    )
    db.add(bot_msg_record)
    await db.flush()

    latency_ms = round((time.time() - start_time) * 1000, 2)
    prompt_tokens = first_response.prompt_tokens
    comp_tokens = first_response.completion_tokens
    token_cost_usd = round((prompt_tokens * 0.00000015) + (comp_tokens * 0.0000006), 6)

    # Update metadata with last discussed product
    if retrieved_chunks:
        top_meta = retrieved_chunks[0].get("metadata", {})
        if top_meta.get("title"):
            thread_meta["last_discussed_product_title"] = top_meta["title"]
    thread.metadata_json = thread_meta

    ai_run = AIRun(
        thread_id=thread.id,
        message_id=bot_msg_record.id,
        user_message=customer_message,
        prompt_tokens=prompt_tokens,
        completion_tokens=comp_tokens,
        latency_ms=latency_ms,
        retrieved_chunks=[{"text": c["chunk_text"], "score": c["score"]} for c in retrieved_chunks],
        tool_calls=tool_calls_executed,
        raw_response=final_reply_text,
        detected_language=lang,
        model_name=reply_model,
        token_cost_usd=token_cost_usd,
        is_blocked=is_blocked,
        blocked_reason=blocked_reason,
        prompt_version=PROMPT_VERSION
    )
    db.add(ai_run)
    await db.commit()

    return {
        "reply": final_reply_text,
        "detected_language": lang,
        "retrieved_sources": retrieved_chunks,
        "tool_calls": tool_calls_executed,
        "handover_triggered": handover_triggered,
        "thread_status": thread.status,
        "thread_id": thread.id,
        "latency_ms": latency_ms
    }
