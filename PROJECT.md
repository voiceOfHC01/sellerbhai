# Master Spec: Multi-Channel Bangla Social Commerce AI Agent (Reply.BD / SaleMag Architecture)

## Executive Overview
An AI-powered social commerce assistant designed for Bangladeshi online merchants (Facebook Pages, WhatsApp Business, Instagram DM/Comments). The system understands **Bangla script**, **Banglish** (Romanized phonetic Bengali), and **English**. It provides conversational sales, accurate catalog retrieval, automated stock queries, draft/confirmed order taking (Cash on Delivery), and seamless human agent handover.

---

## Architectural Principles
1. **Never Hallucinate Prices or Policies**: The AI must only state prices, stock levels, and policies retrieved from the merchant's catalog and knowledge base. If information is missing or uncertain, it triggers `handover_to_human`.
2. **First-Class Trilingual Support**: Native handling of Unicode Bangla (বাংলা), Banglish (e.g. *"vai eitar dam koto? cash on delivery hobe?"*), and English.
3. **Single-Owner Admin**: Streamlined single-tenant owner model seeded securely via environment variables with JWT authentication.
4. **Pluggable AI & Embeddings**: Abstract provider architecture supporting Gemini, OpenAI, or local/mock engines for rapid local iteration and testing.
5. **Decoupled Phased Implementation**:
   - **Phase 1**: Core repo, single-owner auth, DB migrations, Catalog & Knowledge Base management, pgvector RAG, AI Engine with tool calls, interactive test-chat inspector, and automated test suite.
   - **Phase 2**: Meta Messenger Webhook Gateway, 24-hour window guard, human takeover state machine.
   - **Phase 3**: WhatsApp Cloud API integration, template messaging, order updates.
   - **Phase 4**: Instagram Professional DM & Comment automation, spam filtering, private replies.
   - **Phase 5**: Live Unified Inbox, Analytics & Multi-agent escalation.

---

## Phase 1 Specifications

### 1. Repository Structure
```
/
├── .env.example
├── docker-compose.yml
├── PROJECT.md
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── alembic.ini
│   ├── app/
│   │   ├── ai/
│   │   │   ├── engine.py
│   │   │   ├── language_detector.py
│   │   │   ├── providers.py
│   │   │   ├── rag.py
│   │   │   └── tools.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/
│   │   │   └── schema.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── catalog.py
│   │   │   ├── chat.py
│   │   │   ├── kb.py
│   │   │   └── settings.py
│   │   └── main.py
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_handover.py
│   │   ├── test_pricing_hallucination.py
│   │   └── test_retrieval.py
│   ├── Dockerfile
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── api/
    │   ├── components/
    │   │   ├── catalog/
    │   │   ├── chat/
    │   │   ├── kb/
    │   │   └── layout/
    │   ├── pages/
    │   │   ├── CatalogPage.tsx
    │   │   ├── KnowledgePage.tsx
    │   │   ├── LoginPage.tsx
    │   │   ├── SettingsPage.tsx
    │   │   └── TestChatPage.tsx
    │   ├── types/
    │   ├── App.tsx
    │   └── main.tsx
    ├── Dockerfile
    ├── package.json
    ├── tailwind.config.js
    └── vite.config.ts
```

### 2. Database Schema (PostgreSQL + pgvector)
- `products`: Product metadata, title, description, category, base_price, is_active.
- `product_variants`: Variants (SKU, title, price, stock, color, size, image_url, is_active).
- `kb_documents`: FAQs and store policies (doc_type: faq/policy, title, content, is_active).
- `kb_chunks`: Vector chunks with 768-dim / 1536-dim embeddings for similarity retrieval.
- `customers`: Customer profiles (name, phone, address, channel, channel_id).
- `threads`: Chat threads per customer (status: active, human_takeover, closed; handover_reason).
- `messages`: Conversation turns (sender_type: customer, bot, admin; content, detected language, metadata).
- `orders`: Orders taken by bot or admin (status: draft, confirmed, cancelled, delivered; total, delivery address).
- `order_items`: Line items linked to product variants with locked purchase price.
- `ai_runs`: Audit trail for every AI execution (tokens, latency, retrieved sources, tool calls, raw output).
- `settings`: Key-value store for brand name, tone, delivery guidelines, and thresholds.

### 3. AI Engine Tools
- `search_products(query, category)`: Fetches matching products from database.
- `check_stock(product_id_or_sku)`: Returns current real-time inventory for variants.
- `get_policy(policy_type)`: Retrieves delivery, return, or payment policies.
- `create_order_draft(customer_name, phone, address, items)`: Stages an order with draft status.
- `confirm_order(order_id)`: Finalizes draft order after customer confirmation.
- `handover_to_human(reason)`: Escalates conversation and flags thread for merchant intervention.

### 4. Language & Tone Guidelines
- Supports Bengali script, Banglish (phonetic Romanized Bengali), and English.
- Mirrors customer's language style politely with respectful Bangladeshi merchant greetings (*"Assalamu Alaikum"*, *"Apnar ki lagbe bolun"*, *"Dhakar bhitore delivery charge 80 taka"*).


---

## Phase 2 Specifications (Completed)

### 1. Webhook Endpoint for Meta
- **Verification (`GET /api/webhooks/meta`)**: Validates `hub.mode == "subscribe"` and `hub.verify_token == settings.META_VERIFY_TOKEN`. Returns raw `hub.challenge` string.
- **Payload Signature Validation (`POST /api/webhooks/meta`)**: Validates `X-Hub-Signature-256` header against `settings.META_APP_SECRET` using `hmac.new(secret, raw_body, hashlib.sha256)`. Rejects invalid signatures with 403 Forbidden.
- **Non-blocking Response**: Immediately returns HTTP 200 `{"status": "EVENT_RECEIVED"}` to satisfy Meta's <2s webhook SLA. Processing runs asynchronously in background tasks.
- **Idempotency**: Message IDs (`mid`) are deduplicated against the `platform_message_id` column in the `messages` table. Duplicate webhook deliveries are ignored.

### 2. Facebook Page Connection
- **Credentials & Encryption**: Page Access Tokens are encrypted before saving using symmetric AES-128 / Fernet encryption (`app/core/crypto.py`).
- **Connection API (`/api/facebook`)**: Provides status check, connect/reconnect, disconnect, and mode switching.
- **Connection Card**: Displays connection state, Page ID, Page Name, Reconnect button, and Webhook callback/verify token details.

### 3. Normalization into Internal Message Schema
- Incoming Meta payloads (`entry[].messaging[]`) are normalized into `Customer` (`channel="facebook"`, `channel_id=PSID`), `Thread` (`channel="facebook"`), and `Message` (`sender_type="customer"`).

### 4. Send API & 24-Hour Messaging-Window Guard
- **Send API**: Connects to official Graph API `POST https://graph.facebook.com/v21.0/me/messages`.
- **Window Guard (`app/services/window_guard.py`)**: Computes elapsed time since `thread.last_customer_message_at`. Blocks replies if `elapsed > 24 hours` with clear message: *"Blocked: Standard 24-hour messaging window has expired."*

### 5. Unified Inbox UI
- Multi-pane Inbox at `/inbox` displaying thread list, 24-hour window countdown, unread AI draft cards, "Approve & Send" action, AI toggle switch, and Takeover / Resume buttons.

### 6. AI Dispatch Modes
- **Approve Before Send (Default)**: AI generates a draft (`is_draft=True`, `delivery_status="draft"`). The merchant reviews and clicks "Approve & Send" or edits.
- **Full Auto-pilot**: Immediate dispatch via `MetaClient.send_text_message(...)`.
