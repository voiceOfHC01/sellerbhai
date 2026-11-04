import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.services.window_guard import validate_send_allowed, MessagingWindowExpiredError

class MetaClient:
    """
    Client for Meta Messenger & Instagram Graph API v21.0.
    Official Documentation:
    - Messenger Send API: https://developers.facebook.com/docs/messenger-platform/reference/send-api
    - Instagram Graph API Messages: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/messages
    - Comments API & Private Replies: https://developers.facebook.com/docs/messenger-platform/discovery/private-replies
    """

    def __init__(self, page_access_token: Optional[str] = None):
        self.access_token = page_access_token
        self.api_version = settings.META_GRAPH_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    async def send_text_message(
        self,
        recipient_psid: str,
        message_text: str,
        last_customer_message_at: Optional[datetime],
        messaging_type: str = "RESPONSE"
    ) -> Dict[str, Any]:
        """
        Sends a standard text response to a customer's Page-Scoped ID (PSID).
        Enforces Meta's 24-hour Standard Messaging Window policy before dispatch.
        """
        # 1. Enforce 24-hour Window Guard
        validate_send_allowed(last_customer_message_at)

        payload = {
            "recipient": {"id": recipient_psid},
            "messaging_type": messaging_type,
            "message": {"text": message_text}
        }

        # 2. Check if real Page Access Token is provided
        if not self.access_token or self.access_token.startswith("mock_") or self.access_token == "test":
            # Test / Sandbox mock send simulation
            return {
                "recipient_id": recipient_psid,
                "message_id": f"m_mock_mid_{int(datetime.now().timestamp()*1000)}",
                "mock": True,
                "status": "delivered_in_mock_mode"
            }

        # 3. Call official Graph API
        url = f"{self.base_url}/me/messages"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                params={"access_token": self.access_token},
                json=payload
            )
            data = resp.json()

            if resp.status_code != 200:
                error_detail = data.get("error", {}).get("message", "Unknown Meta Graph API error")
                error_code = data.get("error", {}).get("code")
                error_subcode = data.get("error", {}).get("error_subcode")
                raise Exception(
                    f"Meta Send API Error (Code {error_code}, Subcode {error_subcode}): {error_detail}"
                )

            return data

    async def send_instagram_message(
        self,
        recipient_igsid: str,
        message_text: str,
        last_customer_message_at: Optional[datetime],
        ig_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a direct message reply to an Instagram User (IGSID).
        Enforces Meta's 24-hour Standard Messaging Window policy for Instagram Professional accounts.
        Documentation: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/messages
        """
        validate_send_allowed(last_customer_message_at)

        payload = {
            "recipient": {"id": recipient_igsid},
            "message": {"text": message_text}
        }

        if not self.access_token or self.access_token.startswith("mock_") or self.access_token == "test":
            return {
                "recipient_id": recipient_igsid,
                "message_id": f"ig_m_mock_{int(datetime.now().timestamp()*1000)}",
                "mock": True,
                "status": "delivered_in_mock_mode"
            }

        endpoint = f"{self.base_url}/{ig_user_id}/messages" if ig_user_id else f"{self.base_url}/me/messages"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                endpoint,
                params={"access_token": self.access_token},
                json=payload
            )
            data = resp.json()
            if resp.status_code != 200:
                error_detail = data.get("error", {}).get("message", "Unknown Instagram Graph API error")
                error_code = data.get("error", {}).get("code")
                raise Exception(f"Instagram Send API Error (Code {error_code}): {error_detail}")
            return data

    async def hide_comment(self, comment_id: str) -> Dict[str, Any]:
        """
        Hides a spam comment on Facebook Page feed or Instagram post.
        Works for both Facebook comment IDs and Instagram comment IDs using POST /{comment-id}?is_hidden=true.
        Documentation: https://developers.facebook.com/docs/graph-api/reference/v21.0/comment
        """
        if not self.access_token or self.access_token.startswith("mock_") or self.access_token == "test":
            return {"success": True, "comment_id": comment_id, "is_hidden": True, "mock": True}

        url = f"{self.base_url}/{comment_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                params={"access_token": self.access_token, "is_hidden": "true"}
            )
            data = resp.json()
            if resp.status_code != 200:
                error_detail = data.get("error", {}).get("message", "Failed to hide comment")
                raise Exception(f"Hide Comment Error: {error_detail}")
            return data

    async def post_public_comment_reply(
        self,
        comment_id: str,
        message_text: str,
        platform: str = "facebook"
    ) -> Dict[str, Any]:
        """
        Posts a public comment reply beneath a Facebook or Instagram comment.
        For Facebook: POST /{comment_id}/comments with message=<text>
        For Instagram: POST /{comment_id}/replies with message=<text>
        """
        if not self.access_token or self.access_token.startswith("mock_") or self.access_token == "test":
            return {
                "id": f"mock_reply_{int(datetime.now().timestamp()*1000)}",
                "parent_id": comment_id,
                "text": message_text,
                "mock": True
            }

        endpoint = f"{self.base_url}/{comment_id}/replies" if platform == "instagram" else f"{self.base_url}/{comment_id}/comments"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                endpoint,
                params={"access_token": self.access_token},
                json={"message": message_text}
            )
            data = resp.json()
            if resp.status_code != 200:
                error_detail = data.get("error", {}).get("message", "Failed to post public reply")
                raise Exception(f"Public Reply Error: {error_detail}")
            return data

    async def send_private_reply_to_comment(
        self,
        comment_id: str,
        message_text: str,
        platform: str = "facebook",
        ig_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a private message into DM to a user who commented on a Facebook Page post or Instagram post.
        Strict Platform Limits:
        - Meta allows ONLY ONE private reply per comment.
        - Must be sent within 7 days of the comment creation.
        Documentation: https://developers.facebook.com/docs/messenger-platform/discovery/private-replies
        """
        payload = {
            "recipient": {"comment_id": comment_id},
            "message": {"text": message_text}
        }

        if not self.access_token or self.access_token.startswith("mock_") or self.access_token == "test":
            return {
                "recipient_id": f"comment_author_{comment_id}",
                "message_id": f"m_private_dm_{int(datetime.now().timestamp()*1000)}",
                "mock": True
            }

        endpoint = f"{self.base_url}/{ig_user_id}/messages" if (platform == "instagram" and ig_user_id) else f"{self.base_url}/me/messages"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                endpoint,
                params={"access_token": self.access_token},
                json=payload
            )
            data = resp.json()
            if resp.status_code != 200:
                error_detail = data.get("error", {}).get("message", "Failed to send private reply")
                error_code = data.get("error", {}).get("code")
                raise Exception(f"Private Reply Error (Code {error_code}): {error_detail}")
            return data

    async def publish_facebook_page_post(
        self,
        page_id: str,
        message: str,
        image_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Publishes a post to a Facebook Page via Graph API v21.0.
        - Photo post: POST /{page_id}/photos with url and caption
        - Text post: POST /{page_id}/feed with message
        Documentation: https://developers.facebook.com/docs/pages-api/publishing
        Media limits: Max 4MB (up to 10MB via Graph API), JPEG/PNG/GIF/WebP.
        """
        now_ts = int(datetime.now().timestamp() * 1000)
        if not self.access_token or self.access_token.startswith("mock_") or self.access_token == "test":
            mock_post_id = f"{page_id}_{now_ts}"
            return {
                "id": mock_post_id,
                "post_id": mock_post_id,
                "mock": True,
                "published_at": datetime.now().isoformat()
            }

        async with httpx.AsyncClient(timeout=20.0) as client:
            if image_urls and len(image_urls) > 0:
                url = f"{self.base_url}/{page_id}/photos"
                payload = {
                    "url": image_urls[0],
                    "caption": message,
                    "published": True
                }
            else:
                url = f"{self.base_url}/{page_id}/feed"
                payload = {
                    "message": message
                }

            resp = await client.post(
                url,
                params={"access_token": self.access_token},
                json=payload
            )
            data = resp.json()
            if resp.status_code != 200:
                err_msg = data.get("error", {}).get("message", "Facebook post publication failed")
                err_code = data.get("error", {}).get("code")
                raise Exception(f"Facebook Publishing Error (Code {err_code}): {err_msg}")
            return data

    async def publish_instagram_post(
        self,
        ig_user_id: str,
        image_url: str,
        caption: str
    ) -> Dict[str, Any]:
        """
        Publishes a single photo post to an Instagram Professional account via Content Publishing API.
        Two-step container flow:
        1. POST /{ig_user_id}/media with image_url and caption -> returns {id: container_id}
        2. POST /{ig_user_id}/media_publish with creation_id -> returns {id: instagram_media_id}
        Documentation: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/content-publishing
        Requirements & Limits:
        - Image format: JPEG strictly recommended (PNG supported)
        - Aspect ratio: between 4:5 (vertical) and 1.91:1 (horizontal)
        - Max file size: 8MB
        - Max caption length: 2,200 characters, max 30 hashtags
        - Publishing limit: 25 published posts per 24 hours per account
        """
        now_ts = int(datetime.now().timestamp() * 1000)
        if not self.access_token or self.access_token.startswith("mock_") or self.access_token == "test":
            return {
                "id": f"ig_media_{now_ts}",
                "mock": True,
                "published_at": datetime.now().isoformat()
            }

        async with httpx.AsyncClient(timeout=25.0) as client:
            # Step 1: Create Container
            create_url = f"{self.base_url}/{ig_user_id}/media"
            create_payload = {
                "image_url": image_url,
                "caption": caption
            }
            create_resp = await client.post(
                create_url,
                params={"access_token": self.access_token},
                json=create_payload
            )
            create_data = create_resp.json()
            if create_resp.status_code != 200:
                err_msg = create_data.get("error", {}).get("message", "Failed to create Instagram media container")
                err_code = create_data.get("error", {}).get("code")
                raise Exception(f"Instagram Container Error (Code {err_code}): {err_msg}")

            container_id = create_data.get("id")
            if not container_id:
                raise Exception("Instagram API returned no container_id")

            # Step 2: Publish Container
            publish_url = f"{self.base_url}/{ig_user_id}/media_publish"
            publish_payload = {
                "creation_id": container_id
            }
            pub_resp = await client.post(
                publish_url,
                params={"access_token": self.access_token},
                json=publish_payload
            )
            pub_data = pub_resp.json()
            if pub_resp.status_code != 200:
                err_msg = pub_data.get("error", {}).get("message", "Failed to publish Instagram media container")
                err_code = pub_data.get("error", {}).get("code")
                raise Exception(f"Instagram Publish Error (Code {err_code}): {err_msg}")

            return pub_data
