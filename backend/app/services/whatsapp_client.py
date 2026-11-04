import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.services.window_guard import validate_send_allowed, MessagingWindowExpiredError

def normalize_whatsapp_recipient(phone: str) -> str:
    """Normalizes phone numbers to Meta WhatsApp international format (e.g. 88017XXXXXXXX)."""
    cleaned = "".join(c for c in phone if c.isdigit())
    if cleaned.startswith("880") and len(cleaned) == 13:
        return cleaned
    if cleaned.startswith("01") and len(cleaned) == 11:
        return f"88{cleaned}"
    if cleaned.startswith("1") and len(cleaned) == 10:
        return f"880{cleaned}"
    return cleaned

class WhatsAppCustomerServiceWindowError(MessagingWindowExpiredError):
    """Raised when attempting to send a free-form message outside WhatsApp's 24-hour Customer Service Window."""
    def __init__(self, message: str, hours_elapsed: float = 24.0):
        super().__init__(message, hours_elapsed=hours_elapsed)

class WhatsAppClient:
    """
    Client for WhatsApp Business Cloud API v21.0.
    Official Documentation: https://developers.facebook.com/docs/whatsapp/cloud-api
    """

    def __init__(self, phone_number_id: Optional[str] = None, access_token: Optional[str] = None):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.api_version = settings.META_GRAPH_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    async def download_media(self, media_id: str) -> bytes:
        """
        Downloads binary media (e.g. voice notes, audio, images) from WhatsApp Cloud API.
        Two-step process:
        1. Query media metadata URL via GET /{media_id}
        2. Stream download binary bytes from the temporary Facebook CDN URL.
        """
        if not self.access_token or self.access_token.startswith("mock_") or self.access_token == "test":
            # Return realistic mock audio bytes for test environments
            if media_id.startswith("media_short") or media_id.startswith("low_conf"):
                return b"short_muffled_audio_noise"
            return b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00MOCK_AUDIO_DATA_FOR_BANGLA_VOICE_NOTE" * 10

        headers = {"Authorization": f"Bearer {self.access_token}"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            meta_res = await client.get(f"{self.base_url}/{media_id}", headers=headers)
            if meta_res.status_code != 200:
                raise Exception(f"Failed to fetch media metadata for {media_id}: {meta_res.text}")
            media_url = meta_res.json().get("url")
            if not media_url:
                raise Exception(f"No media download URL returned for {media_id}")

            from urllib.parse import urlparse
            parsed = urlparse(media_url)
            host = (parsed.hostname or "").lower()
            if not (host.endswith(".facebook.com") or host.endswith(".fbcdn.net") or host.endswith(".fbsbx.com")):
                raise ValueError(f"Security error: Untrusted media download host '{host}'")

            media_res = await client.get(media_url, headers=headers)
            if media_res.status_code != 200:
                raise Exception(f"Failed to stream media payload: {media_res.text}")
            return media_res.content

    async def send_text_message(
        self,
        recipient_phone: str,
        message_text: str,
        last_customer_message_at: Optional[datetime]
    ) -> Dict[str, Any]:
        """
        Sends a free-form customer-service text message to a WhatsApp user.
        STRICT WINDOW GUARD:
        Under Meta WhatsApp Cloud API rules, free-form replies can ONLY be dispatched
        within the 24-hour Customer Service Window. Outside this window, only pre-approved
        templates are permitted.
        """
        # 1. Enforce 24-hour Customer Service Window Guard
        try:
            validate_send_allowed(last_customer_message_at)
        except MessagingWindowExpiredError as e:
            raise WhatsAppCustomerServiceWindowError(
                f"WhatsApp Customer Service Window Expired: Cannot send free-form message outside the 24-hour window. "
                f"You must use an approved WhatsApp Template to initiate re-engagement. Details: {e}"
            )

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalize_whatsapp_recipient(recipient_phone),
            "type": "text",
            "text": {"preview_url": False, "body": message_text}
        }

        if not self.access_token or self.access_token.startswith("mock_") or self.access_token == "test":
            return {
                "messaging_product": "whatsapp",
                "contacts": [{"input": recipient_phone, "wa_id": recipient_phone}],
                "messages": [{"id": f"wamid.mock_{int(datetime.now().timestamp()*1000)}"}],
                "mock": True
            }

        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            data = resp.json()
            if resp.status_code != 200:
                err_msg = data.get("error", {}).get("message", "Unknown WhatsApp Cloud API Error")
                err_code = data.get("error", {}).get("code")
                raise Exception(f"WhatsApp Send API Error (Code {err_code}): {err_msg}")
            return data

    async def send_template_message(
        self,
        recipient_phone: str,
        template_name: str,
        language_code: str = "bn",
        body_parameters: Optional[List[str]] = None,
        customer_opted_in: bool = True
    ) -> Dict[str, Any]:
        """
        Sends a pre-approved WhatsApp Template message.
        Allowed BOTH inside and outside the 24-hour window for opted-in customers.
        Documentation: https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates
        """
        if not customer_opted_in:
            raise Exception("Cannot send template: Customer has not opted in to receive WhatsApp business notifications.")

        components = []
        if body_parameters:
            parameters = [{"type": "text", "text": str(param)} for param in body_parameters]
            components.append({
                "type": "body",
                "parameters": parameters
            })

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalize_whatsapp_recipient(recipient_phone),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components
            }
        }

        if not self.access_token or self.access_token.startswith("mock_") or self.access_token == "test":
            return {
                "messaging_product": "whatsapp",
                "contacts": [{"input": recipient_phone, "wa_id": recipient_phone}],
                "messages": [{"id": f"wamid.mock_tpl_{int(datetime.now().timestamp()*1000)}"}],
                "mock": True
            }

        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            data = resp.json()
            if resp.status_code != 200:
                err_msg = data.get("error", {}).get("message", "Unknown WhatsApp Template Error")
                err_code = data.get("error", {}).get("code")
                raise Exception(f"WhatsApp Template Send Error (Code {err_code}): {err_msg}")
            return data
