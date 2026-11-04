import re
import json
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import Comment, Setting, FacebookConnection, InstagramConnection
from app.services.meta_client import MetaClient
from app.core.crypto import decrypt_token
from app.ai.engine import process_chat_message

DEFAULT_ABUSIVE_WORDS = [
    "scam", "fraud", "fake", "foul", "bastard", "chor", "batpar", "cheat", "harami", "shala", "bogus", "chora"
]

LINK_REGEX = re.compile(
    r"(?:https?:\/\/|www\.)\S+|\b[a-zA-Z0-9-]+\.(?:com|net|org|xyz|info|biz|co|io|me|site|online|app|live)\b",
    re.IGNORECASE
)

# Bangladeshi phone numbers in comments
PHONE_REGEX = re.compile(
    r"(?:\+?880|0)\s*1[3-9]\s*\d{2}[\s-]?\d{3}[\s-]?\d{3}|[০-৯]{11}",
    re.IGNORECASE
)

def is_spam_comment(text: str, settings_dict: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Evaluates whether a Facebook or Instagram comment is spam based on:
    1. Unauthorized links or URLs
    2. Phone numbers (scam/phishing attempts in public comments)
    3. Abusive, profane, or defamatory words
    """
    if not text:
        return False, None

    # 1. Link / URL check
    hide_links = settings_dict.get("spam_hide_links", True)
    if hide_links and LINK_REGEX.search(text):
        return True, "link_detected"

    # 2. Phone number check
    hide_phones = settings_dict.get("spam_hide_phones", True)
    if hide_phones and PHONE_REGEX.search(text):
        return True, "phone_number_detected"

    # 3. Abusive words check
    abusive_list = settings_dict.get("abusive_words", DEFAULT_ABUSIVE_WORDS)
    lower_text = text.lower()
    for word in abusive_list:
        word = word.strip().lower()
        if not word:
            continue
        # check whole word or substring
        if re.search(r'\b' + re.escape(word) + r'\b', lower_text) or (len(word) > 4 and word in lower_text):
            return True, f"abusive_word: {word}"

    return False, None

def match_comment_rule(text: str, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Matches a comment against merchant-configured keyword rules."""
    if not text or not rules:
        return None

    lower_text = text.lower()
    for rule in rules:
        keyword = rule.get("keyword", "").strip().lower()
        if not keyword:
            continue
        if keyword in lower_text:
            return rule

    return None

async def get_comment_settings(db: AsyncSession) -> Dict[str, Any]:
    """Loads all comment automation and spam filter settings from the database."""
    res = await db.execute(select(Setting))
    settings_rows = res.scalars().all()
    s_map = {s.key: s.value for s in settings_rows}

    # Parse abusive words list
    raw_abusive = s_map.get("abusive_words")
    abusive_words = DEFAULT_ABUSIVE_WORDS
    if raw_abusive:
        try:
            abusive_words = json.loads(raw_abusive)
        except Exception:
            abusive_words = [w.strip() for w in raw_abusive.split(",") if w.strip()]

    # Parse comment rules
    raw_rules = s_map.get("comment_rules")
    comment_rules = []
    if raw_rules:
        try:
            comment_rules = json.loads(raw_rules)
        except Exception:
            comment_rules = []

    return {
        "comment_auto_reply_enabled": s_map.get("comment_auto_reply_enabled", "true").lower() == "true",
        "spam_filter_enabled": s_map.get("spam_filter_enabled", "true").lower() == "true",
        "spam_hide_links": s_map.get("spam_hide_links", "true").lower() == "true",
        "spam_hide_phones": s_map.get("spam_hide_phones", "true").lower() == "true",
        "abusive_words": abusive_words,
        "comment_rules": comment_rules,
        "comment_fallback_ai": s_map.get("comment_fallback_ai", "true").lower() == "true",
    }

async def process_incoming_comment(
    platform: str,
    platform_comment_id: str,
    message: str,
    author_id: str,
    author_name: Optional[str],
    post_id: Optional[str],
    db: AsyncSession,
    page_or_ig_id: Optional[str] = None
) -> Comment:
    """
    Main pipeline for incoming Facebook Page & Instagram comments:
    1. Idempotency: verify comment hasn't already been processed.
    2. Spam Engine: hide links, phone numbers, and abusive words immediately.
    3. Rules Engine: keyword matching to reply templates + private DM.
    4. Private Reply Gate: Meta allows only 1 private reply per comment.
    5. AI Fallback: helpful contextual responses when no rule matches.
    """
    # 1. Idempotency
    existing_res = await db.execute(
        select(Comment).where(Comment.platform_comment_id == platform_comment_id)
    )
    existing_comment = existing_res.scalars().first()
    if existing_comment:
        return existing_comment

    comment = Comment(
        platform=platform,
        platform_comment_id=platform_comment_id,
        post_id=post_id,
        author_id=author_id,
        author_name=author_name or f"User_{author_id[-4:]}",
        message=message,
        status="pending",
        actions_taken=[],
        is_hidden=False,
        is_private_reply_sent=False
    )
    db.add(comment)
    await db.flush()

    # Retrieve access token
    access_token = None
    if platform == "facebook":
        fb_res = await db.execute(select(FacebookConnection).where(FacebookConnection.is_active == True))
        fb_conn = fb_res.scalars().first()
        if fb_conn:
            access_token = decrypt_token(fb_conn.encrypted_access_token)
    elif platform == "instagram":
        ig_res = await db.execute(select(InstagramConnection).where(InstagramConnection.is_active == True))
        ig_conn = ig_res.scalars().first()
        if ig_conn:
            access_token = decrypt_token(ig_conn.encrypted_access_token)

    meta_client = MetaClient(page_access_token=access_token)
    config = await get_comment_settings(db)

    # 2. Check Spam
    if config["spam_filter_enabled"]:
        is_spam, spam_reason = is_spam_comment(message, config)
        if is_spam:
            # Action: Hide spam comment on platform
            try:
                await meta_client.hide_comment(platform_comment_id)
                comment.is_hidden = True
                comment.status = "hidden_spam"
                comment.actions_taken = ["hidden_spam", f"reason: {spam_reason}"]
            except Exception as e:
                comment.actions_taken = [f"hide_failed: {str(e)}", f"reason: {spam_reason}"]
                comment.status = "hidden_spam"

            await db.commit()
            return comment

    if not config["comment_auto_reply_enabled"]:
        comment.status = "ignored"
        comment.actions_taken = ["auto_reply_disabled"]
        await db.commit()
        return comment

    # 3. Rules Engine: Keyword Match
    matched_rule = match_comment_rule(message, config["comment_rules"])
    public_reply_text = None
    private_reply_text = None
    should_send_private = False

    if matched_rule:
        public_reply_text = matched_rule.get("public_reply")
        private_reply_text = matched_rule.get("private_reply")
        should_send_private = matched_rule.get("send_private_dm", True)
    elif config["comment_fallback_ai"]:
        # AI fallback for general inquiries
        ai_res = await process_chat_message(
            db=db,
            customer_message=f"A customer commented on our post: '{message}'. Please provide a short, friendly response inviting them to order or DM.",
            customer_name=comment.author_name
        )
        public_reply_text = ai_res.get("reply", "ধন্যবাদ আপনার কমেন্টের জন্য! বিস্তারিত জানতে দয়া করে আমাদের ইনবক্সে মেসেজ করুন।")

    actions: List[str] = []

    # 4. Post Public Reply on Comment
    if public_reply_text:
        try:
            await meta_client.post_public_comment_reply(
                comment_id=platform_comment_id,
                message_text=public_reply_text,
                platform=platform
            )
            comment.public_reply_text = public_reply_text
            actions.append("public_reply_sent")
        except Exception as e:
            actions.append(f"public_reply_failed: {str(e)}")

    # 5. Private Reply to Comment (Enforcing strictly ONE private reply per comment)
    if should_send_private and private_reply_text:
        if comment.is_private_reply_sent:
            # Platform Limit: Meta allows only 1 private reply per comment.
            actions.append("private_reply_blocked (already sent for this comment)")
        else:
            try:
                await meta_client.send_private_reply_to_comment(
                    comment_id=platform_comment_id,
                    message_text=private_reply_text,
                    platform=platform,
                    ig_user_id=page_or_ig_id
                )
                comment.is_private_reply_sent = True
                comment.private_reply_text = private_reply_text
                actions.append("private_reply_sent")
            except Exception as e:
                actions.append(f"private_reply_blocked: {str(e)}")

    comment.actions_taken = actions
    comment.status = "replied" if ("public_reply_sent" in actions or "private_reply_sent" in actions) else "pending"
    await db.commit()
    return comment
