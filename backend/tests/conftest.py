import os
import sys

# Ensure backend folder is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import Base
from app.core.security import get_password_hash
from app.models.schema import AdminUser, Product, ProductVariant, KBDocument, Setting
from app.ai.rag import reindex_all_knowledge

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Seed Admin
        admin = AdminUser(
            email="admin@replybd.com",
            hashed_password=get_password_hash("admin_secure_pass_2026"),
            name="Admin Owner"
        )
        session.add(admin)

        # Seed Settings
        session.add_all([
            Setting(key="store_name", value="StyleCraft BD", description="Store name"),
            Setting(key="brand_tone", value="Polite, friendly Bangladeshi assistant", description="Tone"),
            Setting(key="delivery_inside_dhaka", value="80", description="Dhaka delivery fee"),
            Setting(key="delivery_outside_dhaka", value="150", description="Outside Dhaka delivery fee"),
        ])

        # Seed Products
        polo = Product(
            title="Premium Cotton Polo Shirt",
            description="100% combed cotton polo shirt. Soft and breathable.",
            category="Men's Fashion",
            base_price=850.0,
            is_active=True
        )
        session.add(polo)
        await session.flush()

        session.add_all([
            ProductVariant(product_id=polo.id, sku="POLO-BLK-M", title="Black Polo M", price=850.0, stock=10, is_active=True),
            ProductVariant(product_id=polo.id, sku="POLO-WHT-L", title="White Polo L", price=890.0, stock=5, is_active=True),
        ])

        # Seed KB Documents
        session.add_all([
            KBDocument(
                doc_type="policy",
                title="Delivery Policy",
                content="ঢাকার ভেতরে ডেলিভারি চার্জ ৮০ টাকা, ঢাকার বাইরে ১৫০ টাকা। ক্যাশ অন ডেলিভারি প্রযোজ্য।",
                is_active=True
            ),
            KBDocument(
                doc_type="policy",
                title="Return Policy",
                content="পণ্য গ্রহণের সময় চেক করে নেবেন। ত্রুটি থাকলে ৩ দিনের মধ্যে এক্সচেঞ্জ করতে পারবেন।",
                is_active=True
            )
        ])

        await session.commit()
        await reindex_all_knowledge(session)

    yield async_session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
