import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import (
    Customer, Thread, Message, FacebookConnection, InstagramConnection,
    WhatsAppConnection, WhatsAppUsageLog
)
from app.ai.engine import process_chat_message
from app.services.meta_client import MetaClient
from app.services.comment_engine import process_incoming_comment
from app.services.whatsapp_client import WhatsAppClient
from app.services.stt_service import get_stt_provider
from app.core.crypto import decrypt_token
from app.core.config import settings

async def process_incoming_meta_webhook(payload: Dict[str, Any], db: AsyncSession):
    """
    Unified webhook handler for Meta:
    1. Messenger DMs (object == "page", messaging events)
    2. Instagram DMs (object == "instagram", messaging events)
    3. Facebook Page Comments (object == "page", changes with field == "feed")
    4. Instagram Comments (object == "instagram", changes with field == "comments")
    5. WhatsApp Cloud API (object == "whatsapp_business_account", changes with field == "messages")
    """
    obj = payload.get("object")
    if obj not in ("page", "instagram", "whatsapp_business_account"):
        return

    # --- C. Handle WhatsApp Cloud API Messages & Voice Notes ---
    if obj == "whatsapp_business_account":
        entries = payload.get("entry", [])
        for entry in entries:
            waba_id = str(entry.get("id"))
            changes = entry.get("changes", [])
            for change in changes:
                if change.get("field") != "messages":
                    continue
                val = change.get("value", {})
                metadata = val.get("metadata", {})
                phone_number_id = str(metadata.get("phone_number_id"))

                # Fetch WhatsApp Connection settings
                conn_res = await db.execute(
                    select(WhatsAppConnection).where(WhatsAppConnection.phone_number_id == phone_number_id)
                )
                wa_conn = conn_res.scalars().first()
                auto_send_enabled = wa_conn.auto_send if wa_conn else False
                token = decrypt_token(wa_conn.encrypted_access_token) if wa_conn else None

                wa_client = WhatsAppClient(phone_number_id=phone_number_id, access_token=token)
                stt_provider = get_stt_provider()

                contacts_map = {c.get("wa_id"): c.get("profile", {}).get("name") for c in val.get("contacts", [])}
                messages_list = val.get("messages", [])

                for msg_item in messages_list:
                    wamid = msg_item.get("id")
                    from_wa_id = msg_item.get("from")
                    msg_type = msg_item.get("type")

                    if not wamid or not from_wa_id:
                        continue

                    # 1. Idempotency Check: Ignore duplicate webhook deliveries
                    existing_msg_res = await db.execute(
                        select(Message).where(Message.platform_message_id == wamid)
                    )
                    if existing_msg_res.scalars().first():
                        continue

                    # 2. Extract Message Content (Text vs Audio / Voice Note)
                    incoming_text = ""
                    is_voice = False
                    voice_confidence = None
                    audio_url = None

                    if msg_type == "text":
                        incoming_text = msg_item.get("text", {}).get("body", "")
                    elif msg_type == "audio":
                        is_voice = True
                        audio_obj = msg_item.get("audio", {})
                        media_id = audio_obj.get("id")
                        mime_type = audio_obj.get("mime_type", "audio/ogg")
                        audio_url = f"whatsapp://media/{media_id}"

                        try:
                            # Download voice note audio
                            audio_bytes = await wa_client.download_media(media_id)
                            # Transcribe spoken Bangla / Banglish
                            transcript, confidence = await stt_provider.transcribe_audio(
                                audio_bytes=audio_bytes,
                                mime_type=mime_type,
                                language="bn"
                            )
                            incoming_text = transcript
                            voice_confidence = confidence
                        except Exception as e:
                            incoming_text = "[ভয়েস নোট ডাউনলোড/ট্রান্সক্রিপশনে সমস্যা হয়েছে]"
                            voice_confidence = 0.0

                    if not incoming_text:
                        continue

                    # 3. Normalize Customer
                    c_res = await db.execute(
                        select(Customer).where(Customer.channel == "whatsapp", Customer.channel_id == from_wa_id)
                    )
                    customer = c_res.scalars().first()
                    contact_name = contacts_map.get(from_wa_id) or f"WhatsApp (+{from_wa_id[-4:]})"
                    if not customer:
                        customer = Customer(
                            name=contact_name,
                            phone=from_wa_id,
                            channel="whatsapp",
                            channel_id=from_wa_id,
                            notes=f"WhatsApp User: +{from_wa_id}"
                        )
                        db.add(customer)
                        await db.flush()

                    # 4. Normalize Thread
                    t_res = await db.execute(
                        select(Thread).where(Thread.customer_id == customer.id, Thread.channel == "whatsapp")
                    )
                    thread = t_res.scalars().first()
                    now_utc = datetime.now(timezone.utc)

                    if not thread:
                        thread = Thread(
                            customer_id=customer.id,
                            channel="whatsapp",
                            status="active",
                            ai_enabled=True,
                            last_activity_at=now_utc,
                            last_customer_message_at=now_utc
                        )
                        db.add(thread)
                        await db.flush()
                    else:
                        thread.last_activity_at = now_utc
                        thread.last_customer_message_at = now_utc

                    # Check for Low-Confidence Voice Note Handover Trigger
                    handover_for_voice = False
                    if is_voice and voice_confidence is not None and voice_confidence < 0.60:
                        handover_for_voice = True
                        thread.status = "human_takeover"
                        thread.ai_enabled = False
                        thread.handover_reason = f"Voice note low transcription confidence ({voice_confidence:.2f}): manual listening required"

                    # 5. Save Incoming Customer Message
                    cust_msg = Message(
                        thread_id=thread.id,
                        sender_type="customer",
                        content=incoming_text,
                        platform_message_id=wamid,
                        is_voice_message=is_voice,
                        audio_url=audio_url,
                        voice_transcript=incoming_text if is_voice else None,
                        voice_confidence=voice_confidence,
                        is_draft=False,
                        delivery_status="sent",
                        metadata_json=msg_item
                    )
                    db.add(cust_msg)
                    await db.commit()

                    # 6. AI Engine Processing (Skip if low-confidence voice note triggered handover)
                    if thread.ai_enabled and thread.status != "human_takeover" and not handover_for_voice:
                        ai_res = await process_chat_message(
                            db=db,
                            customer_message=incoming_text,
                            thread_id=thread.id,
                            customer_name=customer.name
                        )
                        ai_reply = ai_res.get("reply", "")

                        if auto_send_enabled:
                            try:
                                # Dispatch free-form response within the 24-hour Customer Service Window
                                send_res = await wa_client.send_text_message(
                                    recipient_phone=from_wa_id,
                                    message_text=ai_reply,
                                    last_customer_message_at=thread.last_customer_message_at
                                )
                                out_msg_id = send_res.get("messages", [{}])[0].get("id")
                                bot_msg = Message(
                                    thread_id=thread.id,
                                    sender_type="bot",
                                    content=ai_reply,
                                    platform_message_id=out_msg_id,
                                    is_draft=False,
                                    delivery_status="sent"
                                )
                                # Log usage cost awareness category="service"
                                db.add(WhatsAppUsageLog(
                                    message_id=out_msg_id,
                                    thread_id=thread.id,
                                    customer_id=customer.id,
                                    recipient_phone=from_wa_id,
                                    category="service",
                                    direction="outbound",
                                    status="sent"
                                ))
                            except Exception as e:
                                bot_msg = Message(
                                    thread_id=thread.id,
                                    sender_type="bot",
                                    content=ai_reply,
                                    is_draft=True,
                                    delivery_status="failed",
                                    metadata_json={"error": str(e)}
                                )
                            db.add(bot_msg)
                            await db.commit()
                        else:
                            # Default "Approve Before Send" draft mode
                            draft_msg = Message(
                                thread_id=thread.id,
                                sender_type="bot",
                                content=ai_reply,
                                is_draft=True,
                                delivery_status="draft",
                                metadata_json={
                                    "detected_language": ai_res.get("detected_language"),
                                    "tool_calls": ai_res.get("tool_calls"),
                                    "requires_approval": True,
                                    "channel": "whatsapp"
                                }
                            )
                            db.add(draft_msg)
                            await db.commit()
        return

    # --- Direct Messaging & Comments for Facebook and Instagram ---
    entries = payload.get("entry", [])
    for entry in entries:
        account_id = str(entry.get("id"))

        # --- A. Process Direct Messaging Events (Messenger & Instagram DM) ---
        messaging_events = entry.get("messaging", [])
        if messaging_events:
            channel = "instagram" if obj == "instagram" else "facebook"

            # Fetch account connection settings
            auto_send_enabled = False
            token = None
            if channel == "facebook":
                conn_res = await db.execute(
                    select(FacebookConnection).where(FacebookConnection.page_id == account_id)
                )
                fb_conn = conn_res.scalars().first()
                auto_send_enabled = fb_conn.auto_send if fb_conn else settings.FACEBOOK_AUTO_SEND
                token = decrypt_token(fb_conn.encrypted_access_token) if fb_conn else None
            else:
                conn_res = await db.execute(
                    select(InstagramConnection).where(InstagramConnection.ig_user_id == account_id)
                )
                ig_conn = conn_res.scalars().first()
                auto_send_enabled = ig_conn.auto_send if ig_conn else False
                token = decrypt_token(ig_conn.encrypted_access_token) if ig_conn else None

            meta_client = MetaClient(page_access_token=token)

            for event in messaging_events:
                sender = event.get("sender", {})
                sender_id = sender.get("id")
                message_obj = event.get("message")

                # Ignore delivery receipts, read receipts, or echoes
                if not message_obj or not sender_id or message_obj.get("is_echo"):
                    continue

                mid = message_obj.get("mid")
                incoming_text = message_obj.get("text", "")
                if not incoming_text:
                    continue

                # 1. Idempotency Check: Ignore duplicate webhook deliveries
                if mid:
                    existing_msg_res = await db.execute(
                        select(Message).where(Message.platform_message_id == mid)
                    )
                    if existing_msg_res.scalars().first():
                        continue

                # 2. Normalize Customer
                c_res = await db.execute(
                    select(Customer).where(Customer.channel == channel, Customer.channel_id == sender_id)
                )
                customer = c_res.scalars().first()
                if not customer:
                    display_prefix = "Instagram User" if channel == "instagram" else "Facebook User"
                    customer = Customer(
                        name=f"{display_prefix} ({sender_id[-4:]})",
                        channel=channel,
                        channel_id=sender_id,
                        notes=f"{channel.capitalize()} ID: {sender_id}"
                    )
                    db.add(customer)
                    await db.flush()

                # 3. Normalize Thread
                t_res = await db.execute(
                    select(Thread).where(Thread.customer_id == customer.id, Thread.channel == channel)
                )
                thread = t_res.scalars().first()
                now_utc = datetime.now(timezone.utc)

                if not thread:
                    thread = Thread(
                        customer_id=customer.id,
                        channel=channel,
                        status="active",
                        ai_enabled=True,
                        last_activity_at=now_utc,
                        last_customer_message_at=now_utc
                    )
                    db.add(thread)
                    await db.flush()
                else:
                    thread.last_activity_at = now_utc
                    thread.last_customer_message_at = now_utc

                # 4. Save Customer Message
                cust_msg = Message(
                    thread_id=thread.id,
                    sender_type="customer",
                    content=incoming_text,
                    platform_message_id=mid,
                    is_draft=False,
                    delivery_status="sent",
                    metadata_json=event
                )
                db.add(cust_msg)
                await db.commit()

                # 5. Invoke AI Engine if AI is active and thread not in human takeover
                if thread.ai_enabled and thread.status != "human_takeover":
                    ai_res = await process_chat_message(
                        db=db,
                        customer_message=incoming_text,
                        thread_id=thread.id,
                        customer_name=customer.name
                    )
                    ai_reply = ai_res.get("reply", "")

                    if auto_send_enabled:
                        try:
                            if channel == "instagram":
                                send_res = await meta_client.send_instagram_message(
                                    recipient_igsid=sender_id,
                                    message_text=ai_reply,
                                    last_customer_message_at=thread.last_customer_message_at,
                                    ig_user_id=account_id
                                )
                            else:
                                send_res = await meta_client.send_text_message(
                                    recipient_psid=sender_id,
                                    message_text=ai_reply,
                                    last_customer_message_at=thread.last_customer_message_at
                                )
                            bot_msg = Message(
                                thread_id=thread.id,
                                sender_type="bot",
                                content=ai_reply,
                                platform_message_id=send_res.get("message_id"),
                                is_draft=False,
                                delivery_status="sent"
                            )
                        except Exception as e:
                            bot_msg = Message(
                                thread_id=thread.id,
                                sender_type="bot",
                                content=ai_reply,
                                is_draft=True,
                                delivery_status="failed",
                                metadata_json={"error": str(e)}
                            )
                        db.add(bot_msg)
                        await db.commit()
                    else:
                        # Default "Approve Before Send" mode: Create draft for merchant approval
                        draft_msg = Message(
                            thread_id=thread.id,
                            sender_type="bot",
                            content=ai_reply,
                            is_draft=True,
                            delivery_status="draft",
                            metadata_json={
                                "detected_language": ai_res.get("detected_language"),
                                "tool_calls": ai_res.get("tool_calls"),
                                "requires_approval": True,
                                "channel": channel
                            }
                        )
                        db.add(draft_msg)
                        await db.commit()

        # --- B. Process Comments Events (Facebook Feed Comments & Instagram Post Comments) ---
        changes_events = entry.get("changes", [])
        for change in changes_events:
            field = change.get("field")
            val = change.get("value", {})

            # 1. Facebook Page Comment: field == "feed" and item == "comment"
            if obj == "page" and field == "feed":
                item_type = val.get("item")
                verb = val.get("verb", "add")
                if item_type == "comment" and verb == "add":
                    comment_id = str(val.get("comment_id"))
                    post_id = str(val.get("post_id"))
                    from_user = val.get("from", {})
                    author_id = str(from_user.get("id"))
                    author_name = from_user.get("name")
                    text = val.get("message", "")

                    if comment_id and text:
                        await process_incoming_comment(
                            platform="facebook",
                            platform_comment_id=comment_id,
                            message=text,
                            author_id=author_id,
                            author_name=author_name,
                            post_id=post_id,
                            db=db,
                            page_or_ig_id=account_id
                        )

            # 2. Instagram Comment: field == "comments"
            elif obj == "instagram" and field == "comments":
                comment_id = str(val.get("id"))
                text = val.get("text", "")
                from_user = val.get("from", {})
                author_id = str(from_user.get("id", ""))
                author_name = from_user.get("username")
                media_obj = val.get("media", {})
                media_id = str(media_obj.get("id", ""))

                if comment_id and text:
                    await process_incoming_comment(
                        platform="instagram",
                        platform_comment_id=comment_id,
                        message=text,
                        author_id=author_id,
                        author_name=author_name,
                        post_id=media_id,
                        db=db,
                        page_or_ig_id=account_id
                    )
