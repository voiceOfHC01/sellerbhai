# Reply.BD — Social Commerce & AI Assistant Platform for Bangladesh

An enterprise-grade, single-owner AI commerce and conversational automation platform designed specifically for Bangladeshi merchants on **Facebook Page (Messenger)**, **Instagram (Direct & Comments)**, and **WhatsApp Business**.

Reply.BD understands **Bangla**, **Banglish**, and **English**, grounds every reply in the merchant's real product catalog and store policies (preventing price inventions and hallucinations), collects complete Cash-on-Delivery orders question-by-question, manages 24-hour customer service messaging windows, detects spam comments, schedules social posts to Meta channels, and provides executive dashboards with human-in-the-loop AI teaching tools.

---

## Architecture Overview

```
                        +------------------------------------+
                        |   Meta Graph API & Webhooks        |
                        | (Messenger, Instagram, WhatsApp)   |
                        +-----------------+------------------+
                                          |
                                          | HMAC-SHA256 verified
                                          v
+-----------------------+     +-------------------------------+     +----------------------+
|  Frontend (React+TS)  | <-> |   FastAPI Backend Server      | <-> | Redis & Background   |
|  Tailwind CSS UI      |     |   - Sliding Rate Limiter      |     | Task Scheduler       |
|  Executive Dashboard  |     |   - Window Guard (24h)        |     +----------------------+
|  Unified Inbox        |     |   - AI Engine & Guardrails    |
|  Post Composer        |     |   - Fernet AES Token Crypto   |
|  AI Review & Teaching |     +---------------+---------------+
+-----------------------+                     |
                                              v
                              +-------------------------------+
                              |    PostgreSQL + pgvector      |
                              |  - Vector semantic search     |
                              |  - Relational catalog & orders|
                              |  - Complete audit logs        |
                              +-------------------------------+
```

---

## Key Features by Phase

### Phase 1: Core Foundation & AI Catalog RAG
- **Catalog Management**: Products, variants (sizes, colors, SKU), prices, stock, FAQ, and policies.
- **RAG & Vector Search**: Automatic chunking and embedding storage in `pgvector`.
- **Tri-lingual Language Detection**: Accurately classifies Bengali script, phonetic Banglish, and English.
- **Grounding & Guardrails**: System prompt restricts the bot to strictly retrieved knowledge; refuses to hallucinate uncataloged discounts.

### Phase 2: Facebook Messenger & Unified Inbox
- **Webhook Gateway**: Instant `200 OK` return with `X-Hub-Signature-256` verification and platform message deduplication.
- **Token Security**: Cryptographically encrypted Page tokens stored using Fernet AES-128.
- **Messaging Window Guard**: Enforces Meta's 24-hour standard messaging policy and blocks late outbound sends with clear UI warnings.
- **Unified Inbox**: Human takeover button, live chat thread view, message history, and approval queue.

### Phase 3: Conversational Orders & Handover Logic
- **Step-by-Step Order Collection**: Asks one detail at a time (Name -> Bangladeshi 01XXXXXXXXX Phone -> Address -> Payment Method) and confirms before finalizing.
- **Orders Dashboard**: Filter, manage status (Pending, Confirmed, Shipped, Delivered, Cancelled), and export to CSV.
- **Honest Stock Checks**: Proactively warns when items are out of stock and recommends available catalog alternatives.
- **Prompt Injection Defense**: Defends against system prompt overrides, prompt leaking, and adversarial discount attempts.
- **Automated Handover Rules**: Triggers bot pause and flags inbox badge upon refund requests, disputes, customer asking for human, or 2 consecutive failed understandings.

### Phase 4: Instagram Direct & Social Comment Automation
- **Instagram Professional Setup**: Connected via Facebook Page linking and Instagram Graph API.
- **Automated Comment Moderation**: Regex and keyword filter hiding spam links, raw phone numbers, and abusive language.
- **Private DM Replies**: Sends a private message to comment authors (within Meta's 1-reply-per-comment limit) while publicly replying.
- **Comments Log**: Dedicated review screen showing all moderated comments and automated actions.

### Phase 5: WhatsApp Cloud API & Voice Notes
- **WhatsApp Cloud API Integration**: Direct integration via Meta Cloud API v21.0.
- **Customer Service Window**: Free-form replies inside 24 hours; outside window, only pre-approved Meta message templates are permitted.
- **Bangla Voice Note Handling**: Audio download and transcription via speech-to-text with confidence scoring; low confidence triggers human handover.
- **Cost Awareness**: Usage logs for Marketing, Utility, and Service conversations with estimated monthly cost calculation in BDT/USD.

### Phase 6: Post Composer & Multi-Channel Scheduler
- **AI Post Composer**: Generates 3 distinct caption, title, and hashtag variants from raw merchant notes.
- **Publishing Engine**: Schedules and publishes to Facebook Pages and Instagram Business accounts using container creation and publish steps.
- **Double-Posting Protection**: Atomic database status locking prevents concurrent duplicate publications.
- **Asia/Dhaka Calendar**: Displays schedule in Bangladesh Standard Time (UTC+6) with UTC storage.
- **WhatsApp Broadcast Screen**: Separate opt-in template broadcast workflow with explicit pricing notices.

### Phase 7: Analytics, Security, Review & Production Hardening
- **Executive Dashboard**: Total replies, AI vs. manual share ratio, chat-to-order conversion rate, average response latency, and token expenditure.
- **AI Review & Teaching Screen**: Merchants inspect actual AI runs with user input, retrieved context, and bot responses; clicking "Mark Wrong" creates a knowledge base correction and reindexes vector chunks.
- **Security Hardening**: Sliding-window rate limiting on login, chat, and webhook endpoints; locked CORS origin policy; verified encrypted tokens.
- **Compliance Callbacks**: Meta deauthorization and data-deletion callbacks with verification code lookup endpoints; per-customer data erasure button.
- **Automated Backup & Restore**: Automated PostgreSQL dump scripts with 7-day rolling retention and recovery instructions.

---

## Assumptions to Verify Against Current Official Meta Docs

Before production deployment and submitting for Meta App Review, verify the following platform assumptions against the current [Meta for Developers Documentation](https://developers.facebook.com/docs/):

### 1. Graph API Versioning
- **Current Baseline**: Built against **Meta Graph API v21.0**.
- **Endpoints Used**:
  - `POST https://graph.facebook.com/v21.0/me/messages` (Messenger Send API)
  - `POST https://graph.facebook.com/v21.0/{ig_user_id}/messages` (Instagram Send API)
  - `POST https://graph.facebook.com/v21.0/{phone_number_id}/messages` (WhatsApp Cloud API)
  - `POST https://graph.facebook.com/v21.0/{page_id}/feed` (Facebook Page Posting)
  - `POST https://graph.facebook.com/v21.0/{ig_user_id}/media` & `media_publish` (Instagram Media Container flow)
- **Action**: Check if any endpoint parameters have been deprecated in newer Graph API releases.

### 2. Messenger & Instagram 24-Hour Messaging Policy
- **Standard Window**: Standard messaging allows businesses to respond to user-initiated messages within 24 hours of the user's latest message.
- **Message Tags**: For messages sent outside 24 hours on Messenger, Meta supports Message Tags (`CONFIRMED_EVENT_UPDATE`, `POST_PURCHASE_UPDATE`, `ACCOUNT_UPDATE`, `HUMAN_AGENT`).
- **Human Agent Tag**: Meta's `HUMAN_AGENT` tag extends the customer response window to 7 days for authorized human responses. Verify whether your app qualifies for this permission if extended human response times are required.

### 3. Instagram Comment Private Replies
- **Limits**: Meta enforces a strict limit of **one private reply per comment**.
- **Timeframe**: Private replies to comments must be made within **7 days** of the comment creation timestamp.
- **Reference**: The `POST /{comment_id}/replies` endpoint requires `recipient={"comment_id": "..."}`.

### 4. WhatsApp Cloud API Conversation-Based Pricing
- **Pricing Model**: Meta bills WhatsApp Cloud API conversations per 24-hour session across four categories: `Marketing`, `Utility`, `Authentication`, and `Service` (user-initiated).
- **Free Tier Allowance**: As of official Meta policy, the first 1,000 service conversations per WhatsApp Business Account per month are free.
- **Rates**: Check Meta's official WhatsApp Business Platform Pricing sheet for Bangladesh country code (`+880`) to configure accurate rates in Settings.

### 5. Instagram Media Publishing Specifications
- **Container Publishing Flow**: Instagram Graph API requires creating a media container (`POST /{ig_user_id}/media`) with `image_url` followed by polling status and publishing (`POST /{ig_user_id}/media_publish`).
- **Image Requirements**: Images must be hosted on a public HTTPS URL, formatted as JPEG or PNG, have an aspect ratio between 4:5 and 1.91:1, and not exceed 8 MB.

### 6. Meta App Review Required Permissions
Ensure your Meta Developer App requests and receives approval for:
- `pages_messaging` (Messenger bot & human handover)
- `pages_read_engagement` & `pages_manage_posts` (Facebook post scheduling & comment reading)
- `pages_manage_metadata` (Facebook Page webhook subscriptions)
- `instagram_basic` & `instagram_manage_messages` (Instagram DM automation)
- `instagram_manage_comments` (Instagram comment auto-reply and spam hiding)
- `whatsapp_business_management` & `whatsapp_business_messaging` (WhatsApp Cloud API)

---

## Getting Started

### Local Development Setup

1. **Clone the repository**:
   ```bash
   cd C:\Users\HP\Downloads
   ```

2. **Backend Setup**:
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Frontend Setup**:
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```

4. **Run All Tests**:
   ```bash
   cd ../backend
   .venv\Scripts\python.exe -m pytest -v
   ```
   *All 43 unit and integration tests across all 7 phases should pass.*

---

## Production Deployment on a Small VPS

See [`DEPLOYMENT.md`](file:///c:/Users/HP/Downloads/DEPLOYMENT.md) for full step-by-step instructions:
- Docker Compose production stack (`docker-compose.prod.yml`)
- Automatic TLS with Caddy reverse proxy (`deploy/Caddyfile`)
- Environment variable configuration (`deploy/env.production.example`)
- Automated nightly PostgreSQL backups (`BACKUP_AND_RESTORE.md`)
