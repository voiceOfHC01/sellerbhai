import os
from typing import List, Union
from pydantic import field_validator, ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "ReplyBD Commerce AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Single-Owner Admin Account
    ADMIN_EMAIL: str = "admin@replybd.com"
    ADMIN_PASSWORD: str = "admin_secure_pass_2026"

    # Security
    JWT_SECRET: str = "super_secret_jwt_key_replace_in_production_xyz123456"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    TOKEN_ENCRYPTION_KEY: str = ""

    # Meta Messenger & Webhooks
    META_APP_ID: str = ""
    META_APP_SECRET: str = "meta_app_secret_test_key_123456"
    META_VERIFY_TOKEN: str = "replybd_meta_verify_token_2026"
    META_GRAPH_VERSION: str = "v21.0"
    FACEBOOK_AUTO_SEND: bool = False  # False = approve before send (drafts), True = full auto-pilot

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/social_commerce"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/social_commerce"
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Configuration
    LLM_PROVIDER: str = "mock"
    EMBEDDING_PROVIDER: str = "mock"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    FAST_LLM_MODEL: str = "gemini-1.5-flash"
    REPLY_LLM_MODEL: str = "gemini-1.5-flash"
    PRICE_FORMAT: str = "symbol"  # "symbol" (৳850) or "word" (850 টাকা)

    # Store Settings & Tone
    STORE_NAME: str = "StyleCraft BD"
    STORE_TONE: str = "Friendly, polite, helpful Bangladeshi online shop assistant. Speak naturally in the customer's language (Bangla, Banglish, or English). Always address customers respectfully."
    DEFAULT_DELIVERY_INSIDE_DHAKA: float = 80.0
    DEFAULT_DELIVERY_OUTSIDE_DHAKA: float = 150.0

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

settings = Settings()

if settings.GEMINI_API_KEY and settings.LLM_PROVIDER == "mock":
    settings.LLM_PROVIDER = "gemini"
    settings.EMBEDDING_PROVIDER = "gemini"
elif settings.OPENAI_API_KEY and settings.LLM_PROVIDER == "mock":
    settings.LLM_PROVIDER = "openai"
    settings.EMBEDDING_PROVIDER = "openai"
