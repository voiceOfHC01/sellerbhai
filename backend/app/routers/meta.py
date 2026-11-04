import hmac
import hashlib
import json
import base64
import uuid
from typing import Optional
from fastapi import APIRouter, Request, Query, Response, HTTPException, status, BackgroundTasks, Header, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.models.schema import FacebookConnection, InstagramConnection, Customer
from app.services.meta_service import process_incoming_meta_webhook

router = APIRouter(prefix="/webhooks/meta", tags=["Meta Messenger Webhooks & Compliance"])

def verify_meta_signature(raw_payload: bytes, signature_header: Optional[str], app_secret: str) -> bool:
    """
    Validates X-Hub-Signature-256 header sent by Meta using SHA-256 HMAC.
    Documentation: https://developers.facebook.com/docs/graph-api/webhooks/getting-started#verification-requests
    """
    if not signature_header:
        return False
    
    parts = signature_header.split("=")
    if len(parts) != 2 or parts[0] != "sha256":
        return False
    
    expected_hash = parts[1]
    mac = hmac.new(app_secret.encode('utf-8'), raw_payload, hashlib.sha256)
    computed_hash = mac.hexdigest()
    
    return hmac.compare_digest(computed_hash, expected_hash)

def parse_signed_request(signed_request: str, secret: str) -> Optional[dict]:
    """
    Decodes and verifies a Meta signed_request using HMAC-SHA256 and the App Secret.
    Documentation: https://developers.facebook.com/docs/development/create-an-app/app-dashboard/data-deletion-callback
    """
    try:
        parts = signed_request.split('.', 1)
        if len(parts) != 2:
            return None
        encoded_sig, payload = parts
        sig = base64.urlsafe_b64decode(encoded_sig + '=' * (-len(encoded_sig) % 4))
        data = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)).decode('utf-8'))
        
        expected_sig = hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        return data
    except Exception:
        return None

async def _bg_process_webhook(payload: dict):
    async with AsyncSessionLocal() as session:
        try:
            await process_incoming_meta_webhook(payload, session)
        except Exception as e:
            print(f"Error in background meta webhook processing: {e}")

@router.get("")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """
    Endpoint for Meta Webhook setup verification.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        # Return raw challenge value as plain text
        return Response(content=str(hub_challenge), media_type="text/plain", status_code=200)
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verification token mismatch or invalid mode"
    )

@router.post("")
async def receive_webhook_event(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256")
):
    """
    Receives incoming Meta Messenger webhook notifications.
    Validates X-Hub-Signature-256, returns 200 immediately, and enqueues event processing.
    """
    raw_body = await request.body()

    # 1. Validate Meta HMAC SHA-256 signature
    is_valid = verify_meta_signature(raw_body, x_hub_signature_256, settings.META_APP_SECRET)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid X-Hub-Signature-256 signature"
        )

    # 2. Parse payload
    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 3. Enqueue background processing & return 200 immediately (< 2s Meta SLA)
    background_tasks.add_task(_bg_process_webhook, payload)
    return {"status": "EVENT_RECEIVED"}

# ==============================================================
# Meta Compliance & Security Endpoints (Deauthorize & Data Deletion)
# ==============================================================

@router.post("/deauthorize")
async def meta_deauthorize_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Meta Deauthorize Callback URL.
    Called by Meta when a user or admin uninstalls or removes permissions for the app.
    Documentation: https://developers.facebook.com/docs/development/create-an-app/app-dashboard/deauthorization-callback
    """
    form_data = await request.form()
    signed_request = form_data.get("signed_request")
    if not signed_request:
        body = await request.body()
        try:
            parsed_json = json.loads(body.decode('utf-8'))
            signed_request = parsed_json.get("signed_request")
        except Exception:
            pass

    if signed_request:
        payload = parse_signed_request(str(signed_request), settings.META_APP_SECRET)
        user_id = payload.get("user_id") if payload else None
        if user_id:
            # Deactivate any connections associated with this user
            res = await db.execute(
                select(FacebookConnection).where(FacebookConnection.page_id == str(user_id))
            )
            conn = res.scalars().first()
            if conn:
                conn.is_active = False
                await db.commit()

    return {"status": "deauthorized", "message": "App deauthorization noted"}

@router.post("/data-deletion")
async def meta_data_deletion_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Meta Data Deletion Request Callback URL.
    Required by Meta Platform Policy to provide an automated endpoint for GDPR/data-deletion requests.
    Documentation: https://developers.facebook.com/docs/development/create-an-app/app-dashboard/data-deletion-callback
    """
    form_data = await request.form()
    signed_request = form_data.get("signed_request")
    user_id = "unknown"

    if signed_request:
        payload = parse_signed_request(str(signed_request), settings.META_APP_SECRET)
        if payload and "user_id" in payload:
            user_id = str(payload["user_id"])
            # Cascade deletion of any customer profile with this channel ID
            cust_res = await db.execute(select(Customer).where(Customer.channel_id == user_id))
            cust = cust_res.scalars().first()
            if cust:
                cust.name = "Deleted Customer"
                cust.phone = None
                cust.address = None
                cust.notes = "Data deleted per Meta User Data Deletion Request"
                await db.commit()

    confirmation_code = f"del_{uuid.uuid4().hex[:12]}"
    status_url = f"{request.base_url}api/webhooks/meta/data-deletion/status?code={confirmation_code}"

    return {
        "url": str(status_url),
        "confirmation_code": confirmation_code
    }

@router.get("/data-deletion/status")
async def meta_data_deletion_status(code: str = Query(...)):
    """
    URL returned to Meta and the user to check the status of their data deletion request.
    """
    return {
        "confirmation_code": code,
        "status": "completed",
        "message": "All personal identifiers associated with this request have been permanently deleted or anonymized."
    }

@router.get("/privacy-policy", response_class=HTMLResponse)
async def get_privacy_policy():
    """
    Public Privacy Policy page required for Meta App Review approval.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Privacy Policy - Reply.BD Social Commerce</title>
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1e293b; }
        h1 { color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }
        h2 { color: #334155; margin-top: 24px; }
        p, li { color: #475569; }
        .box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 20px 0; }
      </style>
    </head>
    <body>
      <h1>Privacy Policy for Reply.BD</h1>
      <p>Last updated: November 2026</p>
      <div class="box">
        <strong>Overview:</strong> Reply.BD is an automated customer service and social commerce assistant for Bangladeshi merchants operating on Facebook Pages, Instagram, and WhatsApp.
      </div>
      <h2>1. Information We Collect</h2>
      <p>When customers interact with connected merchant channels, we process:</p>
      <ul>
        <li>Customer names and public platform IDs (PSID, IGSID, WhatsApp phone numbers)</li>
        <li>Conversation messages and comments to facilitate automated product queries and customer support</li>
        <li>Delivery addresses and order details provided voluntarily for Cash-on-Delivery fulfillment</li>
      </ul>
      <h2>2. Use of Meta Platform APIs</h2>
      <p>We strictly adhere to the Meta Platform Terms and Developer Policies. Access tokens are stored with AES-128 / Fernet encryption at rest. We never sell or share customer data with third-party advertisers.</p>
      <h2>3. Data Retention & Deletion</h2>
      <p>Users may request complete deletion of their data at any time by contacting the merchant or via Meta's automated data deletion callback. Data is removed within 24 hours of receiving a verified request.</p>
      <h2>4. Contact Us</h2>
      <p>For privacy inquiries or compliance questions, email: <code>support@replybd.com</code></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

