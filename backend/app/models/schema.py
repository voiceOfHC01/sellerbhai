import json
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, TypeDecorator
)
from sqlalchemy.orm import relationship
from app.core.database import Base

# Vector type handling: support pgvector when on postgres, JSON fallback for SQLite test environments
try:
    from pgvector.sqlalchemy import Vector
    PG_VECTOR_AVAILABLE = True
except ImportError:
    PG_VECTOR_AVAILABLE = False

class FlexibleVector(TypeDecorator):
    """Stores vectors as pgvector.Vector on PostgreSQL and as JSON on SQLite."""
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 768):
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and PG_VECTOR_AVAILABLE:
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql" and PG_VECTOR_AVAILABLE:
            return value
        if isinstance(value, list):
            return value
        return list(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return []
        return list(value)

def utc_now():
    return datetime.now(timezone.utc)

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(100), default="Owner Admin")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), index=True, nullable=True)
    base_price = Column(Float, nullable=False)
    aliases = Column(Text, nullable=True)  # Comma-separated or phonetic aliases (e.g. panjabi, পাঞ্জাবি, punjabi)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    chunks = relationship("KBChunk", back_populates="product", cascade="all, delete-orphan")

class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    color = Column(String(50), nullable=True)
    size = Column(String(50), nullable=True)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    product = relationship("Product", back_populates="variants")

class KBDocument(Base):
    __tablename__ = "kb_documents"

    id = Column(Integer, primary_key=True, index=True)
    doc_type = Column(String(50), nullable=False)  # faq, policy, general
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    chunks = relationship("KBChunk", back_populates="document", cascade="all, delete-orphan")

class KBChunk(Base):
    __tablename__ = "kb_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(FlexibleVector(768), nullable=True)
    chunk_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    document = relationship("KBDocument", back_populates="chunks")
    product = relationship("Product", back_populates="chunks")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, default="Guest Customer")
    phone = Column(String(50), index=True, nullable=True)
    address = Column(Text, nullable=True)
    channel = Column(String(50), default="web_test")  # facebook, whatsapp, instagram, web_test
    channel_id = Column(String(100), index=True, nullable=True)
    is_opted_in = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    threads = relationship("Thread", back_populates="customer")
    orders = relationship("Order", back_populates="customer")

class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(50), default="web_test")
    status = Column(String(50), default="active")  # active, human_takeover, closed
    ai_enabled = Column(Boolean, default=True)
    handover_reason = Column(String(255), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    last_activity_at = Column(DateTime, default=utc_now)
    last_customer_message_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    customer = relationship("Customer", back_populates="threads")
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="thread")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    sender_type = Column(String(50), nullable=False)  # customer, bot, admin
    content = Column(Text, nullable=False)
    language = Column(String(30), nullable=True)  # bangla, banglish, english
    platform_message_id = Column(String(150), index=True, nullable=True)  # Meta 'mid' / 'wamid'
    is_draft = Column(Boolean, default=False)  # True when awaiting merchant approval
    delivery_status = Column(String(50), default="sent")  # sent, draft, failed, blocked_outside_window
    audio_url = Column(String(500), nullable=True)  # WhatsApp voice note audio path/url
    voice_transcript = Column(Text, nullable=True)  # STT transcription text
    voice_confidence = Column(Float, nullable=True)  # STT confidence score (0.0 - 1.0)
    is_voice_message = Column(Boolean, default=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    thread = relationship("Thread", back_populates="messages")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="pending")  # pending, confirmed, shipped, delivered, cancelled
    payment_method = Column(String(50), default="COD")  # COD, bKash, Nagad
    total_amount = Column(Float, default=0.0)
    delivery_fee = Column(Float, default=0.0)
    delivery_address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    customer = relationship("Customer", back_populates="orders")
    thread = relationship("Thread", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    line_total = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")

class AIRun(Base):
    __tablename__ = "ai_runs"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="SET NULL"), nullable=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    user_message = Column(Text, nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    retrieved_chunks = Column(JSON, nullable=True)
    tool_calls = Column(JSON, nullable=True)
    raw_response = Column(Text, nullable=True)
    detected_language = Column(String(30), nullable=True)
    model_name = Column(String(100), nullable=True, default="gemini-1.5-flash")
    token_cost_usd = Column(Float, default=0.0)
    is_blocked = Column(Boolean, default=False)
    blocked_reason = Column(Text, nullable=True)
    prompt_version = Column(String(50), default="v1.1")
    corrected_reply = Column(Text, nullable=True)
    is_flagged_wrong = Column(Boolean, default=False)
    correction_notes = Column(Text, nullable=True)
    corrected_kb_doc_id = Column(Integer, ForeignKey("kb_documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    corrected_kb_doc = relationship("KBDocument")

class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class FacebookConnection(Base):
    __tablename__ = "facebook_connections"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String(100), unique=True, index=True, nullable=False)
    page_name = Column(String(255), nullable=False)
    encrypted_access_token = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    auto_send = Column(Boolean, default=False)  # False = approve before send; True = auto send
    connected_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class InstagramConnection(Base):
    __tablename__ = "instagram_connections"

    id = Column(Integer, primary_key=True, index=True)
    ig_user_id = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    page_id = Column(String(100), nullable=True)
    encrypted_access_token = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    auto_send = Column(Boolean, default=False)
    connected_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False)  # "facebook" or "instagram"
    platform_comment_id = Column(String(150), unique=True, index=True, nullable=False)
    post_id = Column(String(150), index=True, nullable=True)
    author_id = Column(String(150), nullable=False)
    author_name = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, replied, hidden_spam, ignored
    actions_taken = Column(JSON, default=list)  # ["hidden_spam", "public_reply_sent", "private_reply_sent"]
    public_reply_text = Column(Text, nullable=True)
    private_reply_text = Column(Text, nullable=True)
    is_hidden = Column(Boolean, default=False)
    is_private_reply_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class WhatsAppConnection(Base):
    __tablename__ = "whatsapp_connections"

    id = Column(Integer, primary_key=True, index=True)
    phone_number_id = Column(String(100), unique=True, index=True, nullable=False)
    waba_id = Column(String(100), nullable=True)
    phone_number = Column(String(50), nullable=True)
    encrypted_access_token = Column(Text, nullable=False)
    is_test_number = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    auto_send = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class WhatsAppTemplate(Base):
    __tablename__ = "whatsapp_templates"

    id = Column(Integer, primary_key=True, index=True)
    waba_id = Column(String(100), nullable=True)
    name = Column(String(100), index=True, nullable=False)
    category = Column(String(50), nullable=False)  # MARKETING, UTILITY, AUTHENTICATION, SERVICE
    language = Column(String(20), default="bn")
    status = Column(String(50), default="APPROVED")  # APPROVED, PENDING, REJECTED, PAUSED
    header_text = Column(String(255), nullable=True)
    body_text = Column(Text, nullable=False)
    footer_text = Column(String(255), nullable=True)
    buttons_json = Column(JSON, nullable=True)
    meta_template_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class WhatsAppUsageLog(Base):
    __tablename__ = "whatsapp_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(150), nullable=True)
    thread_id = Column(Integer, nullable=True)
    customer_id = Column(Integer, nullable=True)
    recipient_phone = Column(String(50), nullable=False)
    category = Column(String(50), index=True, nullable=False)  # service, utility, marketing, authentication
    direction = Column(String(20), default="outbound")
    template_name = Column(String(100), nullable=True)
    status = Column(String(50), default="sent")
    timestamp = Column(DateTime, default=utc_now)

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    caption = Column(Text, nullable=False)
    hashtags = Column(Text, nullable=True)
    media_urls = Column(JSON, default=list)  # list of image URLs
    language = Column(String(50), default="Bangla")  # Bangla, Banglish, English
    tone = Column(String(50), default="Friendly")  # Friendly, Sales, Urgent, Formal, Storytelling
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    target_platforms = Column(JSON, default=list)  # ["facebook", "instagram"]
    
    # Post lifecycle state: draft, scheduled, publishing, published, failed
    status = Column(String(50), default="draft", index=True)
    scheduled_at = Column(DateTime, nullable=True)  # stored in UTC
    published_at = Column(DateTime, nullable=True)  # stored in UTC
    
    facebook_post_id = Column(String(100), nullable=True)
    instagram_media_id = Column(String(100), nullable=True)
    
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)
    variants_json = Column(JSON, nullable=True)  # 3 AI generated variants
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    product = relationship("Product")

class WhatsAppBroadcast(Base):
    __tablename__ = "whatsapp_broadcasts"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("whatsapp_templates.id", ondelete="CASCADE"), nullable=False)
    template_name = Column(String(100), nullable=False)
    status = Column(String(50), default="completed")  # draft, processing, completed, failed
    total_recipients = Column(Integer, default=0)
    successful_sends = Column(Integer, default=0)
    failed_sends = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    currency = Column(String(10), default="BDT")
    parameters_json = Column(JSON, nullable=True)
    error_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    template = relationship("WhatsAppTemplate")
