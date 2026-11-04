import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from zoneinfo import ZoneInfo
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.core.crypto import decrypt_token
from app.models.schema import Post, FacebookConnection, InstagramConnection
from app.services.meta_client import MetaClient

try:
    DHAKA_TZ = ZoneInfo("Asia/Dhaka")
except Exception:
    DHAKA_TZ = timezone(timedelta(hours=6))

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def to_dhaka_display(utc_dt: Optional[datetime]) -> Optional[str]:
    """Converts a UTC datetime into an Asia/Dhaka display string (UTC+6)."""
    if not utc_dt:
        return None
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    dhaka_dt = utc_dt.astimezone(DHAKA_TZ)
    return dhaka_dt.strftime("%Y-%m-%d %I:%M %p (BST)")

def dhaka_to_utc(dhaka_str_or_dt: Any) -> datetime:
    """Converts an Asia/Dhaka datetime or ISO string to UTC datetime for database storage."""
    if isinstance(dhaka_str_or_dt, str):
        # Support ISO formats: '2026-11-05T14:30:00'
        dt = datetime.fromisoformat(dhaka_str_or_dt)
    else:
        dt = dhaka_str_or_dt

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DHAKA_TZ)
    return dt.astimezone(timezone.utc)

async def publish_single_post(post_id: int, db: AsyncSession) -> Dict[str, Any]:
    """
    Publishes a scheduled post to Facebook Page and/or Instagram.
    SAFE AGAINST DOUBLE-POSTING:
    Uses an atomic database state transition to lock the post from 'scheduled' or 'failed'
    to 'publishing'. If another worker or process has already grabbed this post,
    rowcount == 0 and execution safely terminates immediately without duplicate publishing.
    """
    now = utc_now()

    # 1. Atomic Lock: transition to 'publishing'
    lock_stmt = (
        update(Post)
        .where(
            and_(
                Post.id == post_id,
                Post.status.in_(["scheduled", "failed", "draft"])
            )
        )
        .values(status="publishing", updated_at=now)
    )
    lock_res = await db.execute(lock_stmt)
    await db.commit()

    if lock_res.rowcount == 0:
        return {
            "status": "skipped",
            "post_id": post_id,
            "message": "Post is already locked in publishing state or already published."
        }

    # Fetch post data
    post_res = await db.execute(select(Post).where(Post.id == post_id))
    post = post_res.scalars().first()
    if not post:
        return {"status": "error", "message": "Post record not found"}

    target_platforms = post.target_platforms or ["facebook"]
    fb_res = None
    ig_res = None
    errors = []

    full_text = f"{post.caption}\n\n{post.hashtags or ''}".strip()
    image_list = post.media_urls if isinstance(post.media_urls, list) else []

    # 2. Publish to Facebook Page if in target
    if "facebook" in target_platforms:
        try:
            fb_conn_res = await db.execute(
                select(FacebookConnection).where(FacebookConnection.is_active == True)
            )
            fb_conn = fb_conn_res.scalars().first()
            if not fb_conn:
                raise Exception("No active Facebook Page connection found. Please connect your Facebook Page.")

            fb_token = decrypt_token(fb_conn.encrypted_access_token)
            client = MetaClient(page_access_token=fb_token)
            fb_res = await client.publish_facebook_page_post(
                page_id=fb_conn.page_id,
                message=full_text,
                image_urls=image_list
            )
            post.facebook_post_id = str(fb_res.get("post_id") or fb_res.get("id"))
        except Exception as e:
            errors.append(f"Facebook Publishing Error: {str(e)}")

    # 3. Publish to Instagram if in target
    if "instagram" in target_platforms:
        try:
            ig_conn_res = await db.execute(
                select(InstagramConnection).where(InstagramConnection.is_active == True)
            )
            ig_conn = ig_conn_res.scalars().first()
            if not ig_conn:
                raise Exception("No active Instagram Professional account found. Please connect Instagram.")

            if not image_list or len(image_list) == 0:
                raise Exception("Instagram Content Publishing API requires at least one public image URL (JPEG/PNG).")

            ig_token = decrypt_token(ig_conn.encrypted_access_token)
            client = MetaClient(page_access_token=ig_token)
            ig_res = await client.publish_instagram_post(
                ig_user_id=ig_conn.ig_user_id,
                image_url=image_list[0],
                caption=full_text
            )
            post.instagram_media_id = str(ig_res.get("id"))
        except Exception as e:
            errors.append(f"Instagram Publishing Error: {str(e)}")

    # 4. Finalize Post State
    if errors:
        post.status = "failed"
        post.error_message = " | ".join(errors)
        post.retry_count = (post.retry_count or 0) + 1
        await db.commit()
        return {
            "status": "failed",
            "post_id": post.id,
            "errors": errors,
            "retry_count": post.retry_count
        }

    post.status = "published"
    post.published_at = utc_now()
    post.error_message = None
    await db.commit()

    return {
        "status": "published",
        "post_id": post.id,
        "facebook_post_id": post.facebook_post_id,
        "instagram_media_id": post.instagram_media_id,
        "published_at": post.published_at.isoformat()
    }

async def run_post_scheduler_tick(db: AsyncSession) -> Dict[str, Any]:
    """
    Background worker cycle:
    Identifies all posts where status == 'scheduled' and scheduled_at <= now (UTC).
    Dispatches publication with safe concurrency locking against double-posting.
    """
    now = utc_now()

    # Query due post IDs
    stmt = (
        select(Post.id)
        .where(
            and_(
                Post.status == "scheduled",
                Post.scheduled_at <= now
            )
        )
        .order_by(Post.scheduled_at.asc())
    )
    res = await db.execute(stmt)
    due_ids = res.scalars().all()

    dispatched = []
    for pid in due_ids:
        out = await publish_single_post(pid, db)
        dispatched.append(out)

    return {
        "tick_timestamp_utc": now.isoformat(),
        "tick_dhaka": to_dhaka_display(now),
        "scheduled_posts_due": len(due_ids),
        "results": dispatched
    }
