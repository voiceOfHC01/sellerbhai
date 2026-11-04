import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schema import Post, Product, FacebookConnection, InstagramConnection
from app.routers.auth import get_current_admin
from app.ai.caption_generator import generate_post_variants
from app.services.post_scheduler import (
    publish_single_post, run_post_scheduler_tick, to_dhaka_display, dhaka_to_utc, utc_now
)

router = APIRouter(prefix="/posts", tags=["Social Commerce Posts & Calendar"])

# --- Schemas ---

class GenerateVariantsRequest(BaseModel):
    notes: str
    product_id: Optional[int] = None
    language: str = "Bangla"  # Bangla, Banglish, English
    tone: str = "Friendly"  # Friendly, Sales / Promotional, Urgent / Limited Offer, Formal, Storytelling

class PostVariantItem(BaseModel):
    variant_number: int
    style_description: str
    title: str
    caption: str
    hashtags: str

class GenerateVariantsResponse(BaseModel):
    language: str
    tone: str
    variants: List[PostVariantItem]

class PostCreateRequest(BaseModel):
    title: Optional[str] = None
    caption: str
    hashtags: Optional[str] = None
    media_urls: Optional[List[str]] = []
    language: str = "Bangla"
    tone: str = "Friendly"
    product_id: Optional[int] = None
    target_platforms: List[str] = ["facebook"]
    # Publish mode: "draft", "schedule", "publish_now"
    publish_mode: str = "draft"
    scheduled_at_dhaka: Optional[str] = None  # e.g. "2026-11-05T15:30:00"
    scheduled_at_utc: Optional[datetime] = None
    variants_json: Optional[Any] = None

class PostUpdateRequest(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[str] = None
    media_urls: Optional[List[str]] = None
    target_platforms: Optional[List[str]] = None
    scheduled_at_dhaka: Optional[str] = None
    status: Optional[str] = None

class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: Optional[str] = None
    caption: str
    hashtags: Optional[str] = None
    media_urls: Optional[List[str]] = None
    language: Optional[str] = None
    tone: Optional[str] = None
    product_id: Optional[int] = None
    product_title: Optional[str] = None
    target_platforms: Optional[List[str]] = None
    status: str
    scheduled_at: Optional[datetime] = None
    scheduled_at_dhaka: Optional[str] = None
    published_at: Optional[datetime] = None
    published_at_dhaka: Optional[str] = None
    facebook_post_id: Optional[str] = None
    instagram_media_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime

# --- Endpoints ---

@router.post("/generate-variants", response_model=GenerateVariantsResponse)
async def generate_variants(
    req: GenerateVariantsRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    AI Generator: Generates 3 rich social media post variants with titles, captions, and hashtags.
    Tailored for Bangladeshi e-commerce in chosen language and tone.
    """
    product_title = None
    product_price = None

    if req.product_id:
        p_res = await db.execute(select(Product).where(Product.id == req.product_id))
        prod = p_res.scalars().first()
        if prod:
            product_title = prod.title
            product_price = prod.base_price

    variants_raw = await generate_post_variants(
        notes=req.notes,
        product_title=product_title,
        price=product_price,
        language=req.language,
        tone=req.tone
    )

    items = [
        PostVariantItem(
            variant_number=v.get("variant_number", i + 1),
            style_description=v.get("style_description", f"Style {i+1}"),
            title=v.get("title", ""),
            caption=v.get("caption", ""),
            hashtags=v.get("hashtags", "")
        )
        for i, v in enumerate(variants_raw)
    ]

    return GenerateVariantsResponse(
        language=req.language,
        tone=req.tone,
        variants=items
    )

@router.get("", response_model=List[PostResponse])
async def list_posts(
    status_filter: Optional[str] = Query(None, alias="status"),
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Lists social posts sorted by scheduled/created time descending."""
    stmt = select(Post).order_by(Post.created_at.desc())
    if status_filter:
        stmt = stmt.where(Post.status == status_filter)

    res = await db.execute(stmt)
    posts = res.scalars().all()

    output = []
    for p in posts:
        # Check platform filter
        if platform and p.target_platforms and platform not in p.target_platforms:
            continue

        prod_title = None
        if p.product_id:
            pr = await db.execute(select(Product.title).where(Product.id == p.product_id))
            prod_title = pr.scalar_one_or_none()

        output.append(
            PostResponse(
                id=p.id,
                title=p.title,
                caption=p.caption,
                hashtags=p.hashtags,
                media_urls=p.media_urls or [],
                language=p.language,
                tone=p.tone,
                product_id=p.product_id,
                product_title=prod_title,
                target_platforms=p.target_platforms or [],
                status=p.status,
                scheduled_at=p.scheduled_at,
                scheduled_at_dhaka=to_dhaka_display(p.scheduled_at),
                published_at=p.published_at,
                published_at_dhaka=to_dhaka_display(p.published_at),
                facebook_post_id=p.facebook_post_id,
                instagram_media_id=p.instagram_media_id,
                error_message=p.error_message,
                retry_count=p.retry_count or 0,
                created_at=p.created_at
            )
        )
    return output

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    req: PostCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Creates a new post in Draft, Scheduled, or Immediately Published state.
    Converts Dhaka display time to UTC for safe storage.
    """
    scheduled_utc = None
    initial_status = "draft"

    if req.publish_mode == "schedule":
        if req.scheduled_at_utc:
            scheduled_utc = req.scheduled_at_utc
        elif req.scheduled_at_dhaka:
            scheduled_utc = dhaka_to_utc(req.scheduled_at_dhaka)
        else:
            raise HTTPException(
                status_code=400,
                detail="A valid scheduled date and time must be specified for scheduled posts."
            )
        initial_status = "scheduled"
    elif req.publish_mode == "publish_now":
        initial_status = "scheduled"
        scheduled_utc = utc_now()

    post = Post(
        title=req.title,
        caption=req.caption,
        hashtags=req.hashtags,
        media_urls=req.media_urls or [],
        language=req.language,
        tone=req.tone,
        product_id=req.product_id,
        target_platforms=req.target_platforms or ["facebook"],
        status=initial_status,
        scheduled_at=scheduled_utc,
        variants_json=req.variants_json
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    # If publish_now requested, trigger immediately
    if req.publish_mode == "publish_now":
        await publish_single_post(post.id, db)
        await db.refresh(post)

    return PostResponse(
        id=post.id,
        title=post.title,
        caption=post.caption,
        hashtags=post.hashtags,
        media_urls=post.media_urls or [],
        language=post.language,
        tone=post.tone,
        product_id=post.product_id,
        target_platforms=post.target_platforms or [],
        status=post.status,
        scheduled_at=post.scheduled_at,
        scheduled_at_dhaka=to_dhaka_display(post.scheduled_at),
        published_at=post.published_at,
        published_at_dhaka=to_dhaka_display(post.published_at),
        facebook_post_id=post.facebook_post_id,
        instagram_media_id=post.instagram_media_id,
        error_message=post.error_message,
        retry_count=post.retry_count or 0,
        created_at=post.created_at
    )

@router.get("/failures", response_model=List[PostResponse])
async def list_failed_posts(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Returns posts in 'failed' status for dashboard failure notices."""
    stmt = select(Post).where(Post.status == "failed").order_by(Post.updated_at.desc())
    res = await db.execute(stmt)
    posts = res.scalars().all()
    return [
        PostResponse(
            id=p.id,
            title=p.title,
            caption=p.caption,
            hashtags=p.hashtags,
            media_urls=p.media_urls or [],
            language=p.language,
            tone=p.tone,
            product_id=p.product_id,
            target_platforms=p.target_platforms or [],
            status=p.status,
            scheduled_at=p.scheduled_at,
            scheduled_at_dhaka=to_dhaka_display(p.scheduled_at),
            published_at=p.published_at,
            published_at_dhaka=to_dhaka_display(p.published_at),
            facebook_post_id=p.facebook_post_id,
            instagram_media_id=p.instagram_media_id,
            error_message=p.error_message,
            retry_count=p.retry_count or 0,
            created_at=p.created_at
        )
        for p in posts
    ]

@router.post("/{post_id}/publish-now", response_model=Dict[str, Any])
async def publish_post_now(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Immediately triggers publication of a post."""
    result = await publish_single_post(post_id, db)
    return result

@router.post("/{post_id}/retry", response_model=Dict[str, Any])
async def retry_failed_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Retries publishing a post that was in 'failed' status.
    Safe against double-posting.
    """
    p_res = await db.execute(select(Post).where(Post.id == post_id))
    post = p_res.scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    result = await publish_single_post(post_id, db)
    return result

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Deletes a post."""
    p_res = await db.execute(select(Post).where(Post.id == post_id))
    post = p_res.scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    await db.delete(post)
    await db.commit()
    return None

@router.post("/worker/run-tick", response_model=Dict[str, Any])
async def trigger_scheduler_tick(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """
    Triggers an immediate worker cycle for the post scheduler.
    Scans for due scheduled posts and dispatches publishing with double-posting safety.
    """
    result = await run_post_scheduler_tick(db)
    return result
