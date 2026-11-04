import hmac
import hashlib
import json
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.core.crypto import encrypt_token, decrypt_token
from app.services.window_guard import check_messaging_window, validate_send_allowed, MessagingWindowExpiredError
from app.services.meta_service import process_incoming_meta_webhook
from app.models.schema import Thread, Message, Customer
from sqlalchemy import select

def generate_meta_signature(payload_bytes: bytes, secret: str) -> str:
    h = hmac.new(secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={h}"

@pytest.mark.asyncio
async def test_signature_validation_and_rejection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "object": "page",
            "entry": []
        }
        raw_body = json.dumps(payload).encode('utf-8')

        # 1. Invalid signature should be rejected with 403 Forbidden
        bad_sig = "sha256=invalid_hash_value_123456"
        res_bad = await client.post(
            "/api/webhooks/meta",
            content=raw_body,
            headers={"X-Hub-Signature-256": bad_sig, "Content-Type": "application/json"}
        )
        assert res_bad.status_code == 403

        # 2. Valid signature should return 200 immediately
        good_sig = generate_meta_signature(raw_body, settings.META_APP_SECRET)
        res_good = await client.post(
            "/api/webhooks/meta",
            content=raw_body,
            headers={"X-Hub-Signature-256": good_sig, "Content-Type": "application/json"}
        )
        assert res_good.status_code == 200
        assert res_good.json()["status"] == "EVENT_RECEIVED"

@pytest.mark.asyncio
async def test_duplicate_webhook_ignored_idempotency(test_db):
    async with test_db() as session:
        test_mid = f"mid_test_{int(datetime.now().timestamp()*1000)}"
        psid = "psid_user_998877"
        payload = {
            "object": "page",
            "entry": [
                {
                    "id": "page_id_123",
                    "time": 1730000000,
                    "messaging": [
                        {
                            "sender": {"id": psid},
                            "recipient": {"id": "page_id_123"},
                            "timestamp": 1730000000,
                            "message": {
                                "mid": test_mid,
                                "text": "vai eitar dam koto?"
                            }
                        }
                    ]
                }
            ]
        }

        # First delivery: should process and store customer message
        await process_incoming_meta_webhook(payload, session)

        res_msgs = await session.execute(
            select(Message).where(Message.platform_message_id == test_mid)
        )
        msgs = res_msgs.scalars().all()
        assert len(msgs) == 1

        # Second delivery with identical mid (Meta retry): should be ignored
        await process_incoming_meta_webhook(payload, session)

        res_msgs_after = await session.execute(
            select(Message).where(Message.platform_message_id == test_mid)
        )
        msgs_after = res_msgs_after.scalars().all()
        assert len(msgs_after) == 1  # No duplicate message created!

@pytest.mark.asyncio
async def test_window_guard_blocks_late_replies():
    now = datetime.now(timezone.utc)

    # 1. Customer messaged 2 hours ago: WITHIN 24h window -> Allowed
    recent_time = now - timedelta(hours=2)
    allowed, hours_rem, msg = check_messaging_window(recent_time)
    assert allowed is True
    assert hours_rem > 20.0

    # 2. Customer messaged 26 hours ago: OUTSIDE 24h window -> Blocked
    expired_time = now - timedelta(hours=26)
    allowed_late, _, err_msg = check_messaging_window(expired_time)
    assert allowed_late is False
    assert "Blocked" in err_msg
    assert "24-hour messaging window has expired" in err_msg

    with pytest.raises(MessagingWindowExpiredError):
        validate_send_allowed(expired_time)

@pytest.mark.asyncio
async def test_token_encryption():
    sample_page_token = "EAABwzLixxxx_Secret_Page_Token_12345"
    encrypted = encrypt_token(sample_page_token)
    assert encrypted != sample_page_token

    decrypted = decrypt_token(encrypted)
    assert decrypted == sample_page_token
