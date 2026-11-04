import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_engine, AsyncSessionLocal, Base
from app.core.security import get_password_hash
from app.models.schema import AdminUser, Product, ProductVariant, KBDocument, Setting, WhatsAppTemplate
from app.routers import auth, catalog, kb, settings as settings_router, chat, meta, facebook, inbox, orders, instagram, comments, whatsapp, posts, broadcasts, dashboard, ai_review
from app.ai.rag import reindex_all_knowledge
from app.services.post_scheduler import run_post_scheduler_tick
from app.core.rate_limiter import InMemoryRateLimiterMiddleware

async def seed_initial_data():
    async with AsyncSessionLocal() as session:
        # 1. Seed Single-Owner Admin Account
        admin_res = await session.execute(
            select(AdminUser).where(AdminUser.email == settings.ADMIN_EMAIL)
        )
        if not admin_res.scalars().first():
            admin = AdminUser(
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                name="Shop Owner Admin"
            )
            session.add(admin)

        # 2. Seed Initial Store Settings
        import json
        default_comment_rules = [
            {
                "keyword": "dam",
                "public_reply": "ধন্যবাদ কমেন্টের জন্য! দাম এবং বিস্তারিত তথ্য ইনবক্সে পাঠানো হয়েছে। দয়া করে মেসেজ চেক করুন 😊",
                "private_reply": "আসসালামু আলাইকুম! আমাদের পোলো শার্টের দাম মাত্র ৮৫০ টাকা। সারা বাংলাদেশে ক্যাশ অন ডেলিভারি সুবিধা আছে। অর্ডার করতে আপনার সাইজ ও ঠিকানা দিন।",
                "send_private_dm": True
            },
            {
                "keyword": "price",
                "public_reply": "Thank you for commenting! We have sent the price and full details to your DM. Please check your inbox 😊",
                "private_reply": "Hello! The price is 850 BDT. We offer cash on delivery all over Bangladesh. Let us know your preferred size and address to place an order.",
                "send_private_dm": True
            },
            {
                "keyword": "size",
                "public_reply": "আমাদের M, L, XL সাইজ এভেইলেবল রয়েছে। বিস্তারিত সাইজ চার্ট ইনবক্সে দেওয়া হলো!",
                "private_reply": "আমাদের বর্তমান সাইজ চার্ট: M (Chest 38, Length 27), L (Chest 40, Length 28), XL (Chest 42, Length 29)। আপনি কোন সাইজটি নিতে চান?",
                "send_private_dm": True
            }
        ]
        default_abusive_words = [
            "scam", "fraud", "fake", "foul", "bastard", "chor", "batpar", "cheat", "harami", "shala", "bogus", "chora"
        ]

        settings_defaults = [
            ("store_name", settings.STORE_NAME, "Official store brand name"),
            ("brand_tone", settings.STORE_TONE, "System prompt tone and behavioral persona"),
            ("delivery_inside_dhaka", str(settings.DEFAULT_DELIVERY_INSIDE_DHAKA), "Delivery charge inside Dhaka city"),
            ("delivery_outside_dhaka", str(settings.DEFAULT_DELIVERY_OUTSIDE_DHAKA), "Delivery charge outside Dhaka city"),
            ("llm_provider", settings.LLM_PROVIDER, "Active LLM provider (gemini, openai, mock)"),
            ("embedding_provider", settings.EMBEDDING_PROVIDER, "Active Embedding provider (gemini, openai, mock)"),
            ("comment_auto_reply_enabled", "true", "Automatically reply to Facebook and Instagram comments"),
            ("spam_filter_enabled", "true", "Automatically hide spam comments"),
            ("spam_hide_links", "true", "Hide comments containing external URLs"),
            ("spam_hide_phones", "true", "Hide comments containing phone numbers"),
            ("abusive_words", json.dumps(default_abusive_words), "List of abusive keywords to hide"),
            ("comment_rules", json.dumps(default_comment_rules), "Rules engine for keyword matching in comments"),
            ("comment_fallback_ai", "true", "Use AI engine to answer comments without keyword matches"),
            ("whatsapp_rate_marketing", "5.50", "WhatsApp Marketing conversation rate in chosen currency"),
            ("whatsapp_rate_utility", "1.80", "WhatsApp Utility conversation rate in chosen currency"),
            ("whatsapp_rate_service", "0.00", "WhatsApp Service conversation rate in chosen currency"),
            ("whatsapp_rate_authentication", "1.50", "WhatsApp Authentication conversation rate in chosen currency"),
            ("whatsapp_currency", "BDT", "Currency for WhatsApp usage cost calculations (BDT, USD, etc.)")
        ]
        for key, val, desc in settings_defaults:
            s_res = await session.execute(select(Setting).where(Setting.key == key))
            if not s_res.scalars().first():
                session.add(Setting(key=key, value=val, description=desc))

        # 2b. Seed Starter WhatsApp Templates
        tpl_res = await session.execute(select(WhatsAppTemplate))
        if not tpl_res.scalars().first():
            session.add_all([
                WhatsAppTemplate(
                    name="order_update_bd",
                    category="UTILITY",
                    language="bn",
                    status="APPROVED",
                    header_text="অর্ডার আপডেট",
                    body_text="প্রিয় {{1}}, আপনার অর্ডার #{{2}} সফলভাবে প্যাকেজিং সম্পন্ন হয়েছে এবং ডেলিভারির জন্য প্রস্তুত করা হয়েছে।",
                    footer_text="StyleCraft BD Customer Support"
                ),
                WhatsAppTemplate(
                    name="promotional_offer_bd",
                    category="MARKETING",
                    language="bn",
                    status="APPROVED",
                    header_text="বিশেষ ছাড় অফার!",
                    body_text="আসসালামু আলাইকুম {{1}}! আমাদের নতুন এক্সপোর্ট কোয়ালিটি পোলো শার্টে চলছে বিশেষ মূল্যছাড়। আজই অর্ডার করুন!",
                    footer_text="Reply STOP to unsubscribe"
                )
            ])

        # 3. Seed Starter Catalog Products if table is empty
        p_res = await session.execute(select(Product))
        if not p_res.scalars().first():
            # Product 1: Cotton Polo Shirt
            polo = Product(
                title="Premium Combed Cotton Polo Shirt",
                description="100% export quality combed compact cotton polo shirt with ribbed collar and double-needle hemmed sleeves. Breathable and durable.",
                category="Men's Fashion",
                base_price=850.0,
                image_url="https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=600&auto=format&fit=crop&q=80",
                is_active=True
            )
            session.add(polo)
            await session.flush()

            session.add_all([
                ProductVariant(product_id=polo.id, sku="POLO-BLK-M", title="Black - Medium (M)", price=850.0, stock=25, color="Black", size="M", is_active=True),
                ProductVariant(product_id=polo.id, sku="POLO-BLK-L", title="Black - Large (L)", price=850.0, stock=20, color="Black", size="L", is_active=True),
                ProductVariant(product_id=polo.id, sku="POLO-NVY-L", title="Navy Blue - Large (L)", price=850.0, stock=15, color="Navy", size="L", is_active=True),
                ProductVariant(product_id=polo.id, sku="POLO-WHT-XL", title="Off-White - XL", price=890.0, stock=12, color="White", size="XL", is_active=True),
            ])

            # Product 2: Embroidered Semi-fitted Panjabi
            panjabi = Product(
                title="Classic Embroidered Cotton Panjabi",
                description="Semi-fitted festive cotton panjabi with exquisite thread embroidery on collar and placket. Ideal for Jummah, Eid, and formal gatherings.",
                category="Ethnic Wear",
                base_price=1650.0,
                image_url="https://images.unsplash.com/photo-1617627143750-d86bc21e42bb?w=600&auto=format&fit=crop&q=80",
                is_active=True
            )
            session.add(panjabi)
            await session.flush()

            session.add_all([
                ProductVariant(product_id=panjabi.id, sku="PANJ-WHT-40", title="White - Size 40", price=1650.0, stock=18, color="White", size="40", is_active=True),
                ProductVariant(product_id=panjabi.id, sku="PANJ-WHT-42", title="White - Size 42", price=1650.0, stock=14, color="White", size="42", is_active=True),
                ProductVariant(product_id=panjabi.id, sku="PANJ-MAR-42", title="Maroon - Size 42", price=1750.0, stock=8, color="Maroon", size="42", is_active=True),
            ])

            # Product 3: Leather Slim Wallet
            wallet = Product(
                title="Genuine Top-Grain Leather Bifold Wallet",
                description="Handcrafted 100% genuine top-grain cowhide leather wallet with RFID blocking, 6 card slots, and dual cash compartments.",
                category="Accessories",
                base_price=950.0,
                image_url="https://images.unsplash.com/photo-1627123424574-724758594e93?w=600&auto=format&fit=crop&q=80",
                is_active=True
            )
            session.add(wallet)
            await session.flush()

            session.add_all([
                ProductVariant(product_id=wallet.id, sku="WLT-BRN-01", title="Vintage Brown", price=950.0, stock=30, color="Brown", size="Standard", is_active=True),
                ProductVariant(product_id=wallet.id, sku="WLT-BLK-01", title="Classic Black", price=950.0, stock=35, color="Black", size="Standard", is_active=True),
            ])

        # 4. Seed Starter FAQs & Policies
        kb_res = await session.execute(select(KBDocument))
        if not kb_res.scalars().first():
            session.add_all([
                KBDocument(
                    doc_type="policy",
                    title="Delivery Charges & Time",
                    content="ঢাকার ভেতরে ডেলিভারি চার্জ ৮০ টাকা এবং সময় লাগে ২৪ থেকে ৪৮ ঘণ্টা। ঢাকার বাইরে ডেলিভারি চার্জ ১৫০ টাকা এবং সময় লাগে ২ থেকে ৪ দিন। সারা বাংলাদেশে ক্যাশ অন ডেলিভারি (Cash on Delivery) সুবিধা রয়েছে।",
                    is_active=True
                ),
                KBDocument(
                    doc_type="policy",
                    title="Return & Exchange Policy",
                    content="ডেলিভারিম্যানের উপস্থিতিতে পণ্য চেক করে গ্রহণ করবেন। কোনো সমস্যা থাকলে ডেলিভারি চার্জ দিয়ে রিটার্ন করতে পারবেন। গ্রহণের পর কোনো সাইজ ইস্যু বা ত্রুটি থাকলে ৩ দিনের মধ্যে জানালে এক্সচেঞ্জ করা যাবে।",
                    is_active=True
                ),
                KBDocument(
                    doc_type="faq",
                    title="Payment Methods",
                    content="আমরা ক্যাশ অন ডেলিভারি (COD), বিকাশ (bKash), নগদ (Nagad) এবং রকেট এর মাধ্যমে পেমেন্ট গ্রহণ করি। ঢাকার বাইরে অর্ডারের ক্ষেত্রে অনেক সময় ডেলিভারি চার্জ অগ্রিম প্রযোজ্য হতে পারে।",
                    is_active=True
                ),
                KBDocument(
                    doc_type="faq",
                    title="How to Place Order",
                    content="অর্ডার করতে আপনার নাম, মোবাইল নম্বর এবং পূর্ণ ডেলিভারি ঠিকানা চ্যাটে লিখে দিন। আমাদের এআই সিস্টেম অর্ডার ড্রাফট তৈরি করে কনফার্মেশন জানিয়ে দেবে।",
                    is_active=True
                )
            ])

        await session.commit()

        # 5. Automatically perform initial indexing into pgvector / chunks
        await reindex_all_knowledge(session)

async def _post_scheduler_worker_loop():
    """Background worker that periodically checks and publishes scheduled posts."""
    while True:
        try:
            await asyncio.sleep(30)
            async with AsyncSessionLocal() as session:
                await run_post_scheduler_tick(session)
        except asyncio.CancelledError:
            break
        except Exception:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed initial admin and starter catalog
    await seed_initial_data()
    # Start background scheduler worker
    worker_task = asyncio.create_task(_post_scheduler_worker_loop())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Multi-Channel Bangla Social Commerce AI Agent Engine",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Security Rate Limiter (Brute force & CPU DoS protection)
app.add_middleware(InMemoryRateLimiterMiddleware)

# Mount Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(catalog.router, prefix=settings.API_V1_STR)
app.include_router(kb.router, prefix=settings.API_V1_STR)
app.include_router(settings_router.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(meta.router, prefix=settings.API_V1_STR)
app.include_router(facebook.router, prefix=settings.API_V1_STR)
app.include_router(inbox.router, prefix=settings.API_V1_STR)
app.include_router(orders.router, prefix=settings.API_V1_STR)
app.include_router(instagram.router, prefix=settings.API_V1_STR)
app.include_router(comments.router, prefix=settings.API_V1_STR)
app.include_router(whatsapp.router, prefix=settings.API_V1_STR)
app.include_router(posts.router, prefix=settings.API_V1_STR)
app.include_router(broadcasts.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(ai_review.router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_provider": settings.EMBEDDING_PROVIDER
    }
