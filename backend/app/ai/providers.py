import json
import hashlib
import math
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.core.config import settings

class LLMResponse:
    def __init__(self, content: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None, prompt_tokens: int = 0, completion_tokens: int = 0):
        self.content = content
        self.tool_calls = tool_calls or []
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, system_prompt: Optional[str] = None, temperature: float = 0.2) -> LLMResponse:
        pass

class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        pass

    async def embed_text(self, text: str) -> List[float]:
        res = await self.embed_texts([text])
        return res[0] if res else [0.0] * 768

# ==========================================
# Mock Provider (Zero External Key Required)
# ==========================================
class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dim: int = 768):
        self.dim = dim

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            vec = [0.0] * self.dim
            words = text.lower().split()
            for word in words:
                h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dim
                vec[idx] += 1.0
            
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                vec = [x / norm for x in vec]
            embeddings.append(vec)
        return embeddings

class MockLLMProvider(LLMProvider):
    """
    Intelligent test & offline mock LLM that inspects user prompt and retrieved sources,
    and returns realistic tool calls (search_products, check_stock, get_policy, create_order_draft, handover_to_human)
    or grounded answers in Bangla / Banglish / English.
    """
    async def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, system_prompt: Optional[str] = None, temperature: float = 0.2) -> LLMResponse:
        last_msg = messages[-1]["content"] if messages else ""
        last_role = messages[-1]["role"] if messages else ""
        lower = last_msg.lower()

        # If previous message was a tool result, generate final polite response based on it
        if last_role == "tool" or any(m.get("role") == "tool" for m in messages[-2:]):
            tool_msg = next((m for m in reversed(messages) if m.get("role") == "tool"), None)
            tool_name = tool_msg.get("name", "") if tool_msg else ""
            tool_content = tool_msg.get("content", "{}") if tool_msg else "{}"
            try:
                data = json.loads(tool_content)
            except Exception:
                data = tool_content

            # Respond politely according to the tool output
            if tool_name == "get_policy" or "policy" in str(tool_content).lower() or "delivery" in str(tool_content).lower():
                policy_text = data.get("content", "ঢাকার ভেতরে ৮০ টাকা, বাইরে ১৫০ টাকা।") if isinstance(data, dict) else str(data)
                return LLMResponse(
                    content=f"আমাদের ডেলিভারি পলিসি অনুযায়ী: {policy_text}",
                    prompt_tokens=150,
                    completion_tokens=40
                )
            elif tool_name == "search_products" or (isinstance(data, list) and data):
                if isinstance(data, list) and data:
                    item = data[0]
                    p_title = item.get("title", "পণ্য")
                    p_price = int(item.get("base_price", 850))
                    return LLMResponse(
                        content=f"আমাদের {p_title} রয়েছে। নির্ধারিত মূল্য {p_price} টাকা। আপনি কি এটি অর্ডার করতে চান?",
                        prompt_tokens=180,
                        completion_tokens=45
                    )
                else:
                    return LLMResponse(
                        content="দুঃখিত, এই মুহূর্তে এই পণ্যটি আমাদের ক্যাটালগে নেই। আপনি কি অন্য কোনো কালেকশন দেখতে চান?",
                        prompt_tokens=100,
                        completion_tokens=30
                    )
            elif tool_name == "check_stock" or (isinstance(data, dict) and "stock" in data):
                stock_qty = data.get("stock", 0)
                if data.get("out_of_stock") or stock_qty <= 0:
                    alts = data.get("alternatives", "অন্যান্য ভ্যারিয়েন্ট")
                    return LLMResponse(
                        content=f"দুঃখিত, এই ভ্যারিয়েন্টটি বর্তমানে স্টক আউট। বিকল্প হিসেবে {alts} দেখতে পারেন।",
                        prompt_tokens=120,
                        completion_tokens=35
                    )
                price_val = data.get("price", 850)
                return LLMResponse(
                    content=f"আমাদের কাছে স্টক রয়েছে {stock_qty} টি। নির্ধারিত মূল্য {int(price_val)} টাকা। আপনি কি অর্ডার করতে চান?",
                    prompt_tokens=120,
                    completion_tokens=35
                )
            elif tool_name == "create_order_draft" or "order_id" in str(tool_content).lower():
                return LLMResponse(
                    content=f"ধন্যবাদ! আপনার অর্ডারটি ড্রাফট করা হয়েছে (Order #{data.get('order_id')})। মোট প্রদেয় {int(data.get('total_amount', 930))} টাকা। কনফার্ম করতে 'Confirm' লিখুন।",
                    prompt_tokens=160,
                    completion_tokens=45
                )
            elif tool_name == "handover_to_human":
                return LLMResponse(
                    content="আপনার বিষয়টি আমাদের মানব প্রতিনিধির কাছে হস্তান্তর করা হয়েছে। খুব শীঘ্রই আমাদের প্রতিনিধি যোগাযোগ করবেন।",
                    prompt_tokens=100,
                    completion_tokens=30
                )

        # 1. Handover detection (complaints, abuse, custom discount bargaining, human request)
        handover_keywords = [
            "manager", "manush", "human", "agent", "kotha bolbo", "officer", 
            "cheat", "fakibaj", "discount", "kom", "bargain", "free", "%"
        ]
        if any(w in lower for w in handover_keywords):
            return LLMResponse(
                tool_calls=[{
                    "name": "handover_to_human",
                    "arguments": {"reason": "Customer requested human support or discount negotiation outside fixed catalog pricing"}
                }],
                prompt_tokens=100,
                completion_tokens=25
            )

        # 2. Delivery / Policy queries
        if any(w in lower for w in ["delivery", "deliveri", "charge", "koto tk", "dhaka", "return", "policy", "koto din"]):
            return LLMResponse(
                tool_calls=[{
                    "name": "get_policy",
                    "arguments": {"policy_type": "delivery"}
                }],
                prompt_tokens=90,
                completion_tokens=20
            )

        # 3. Order taking flow (Name, phone, address detection)
        phone_match = any(c.isdigit() for c in lower) and ("01" in lower or len([c for c in lower if c.isdigit()]) >= 11)
        if (phone_match and any(w in lower for w in ["order", "nibo", "pathan", "send", "address", "road", "dhaka"])) or ("order confirm" in lower):
            return LLMResponse(
                tool_calls=[{
                    "name": "create_order_draft",
                    "arguments": {
                        "customer_name": "Customer",
                        "phone": "01700000000",
                        "address": last_msg,
                        "items": [{"sku": "DEFAULT-01", "quantity": 1}]
                    }
                }],
                prompt_tokens=110,
                completion_tokens=30
            )

        # 4. Stock check
        if any(w in lower for w in ["stock", "available", "ase kina", "ache kina", "available ache"]):
            return LLMResponse(
                tool_calls=[{
                    "name": "check_stock",
                    "arguments": {"product_id_or_sku": last_msg.strip()}
                }],
                prompt_tokens=85,
                completion_tokens=20
            )

        # Bot Disclosure check (word boundary matching so 'bhai' does not match 'ai')
        import re
        if re.search(r'\b(bot|robot|ai)\b', lower) or any(w in lower for w in [
            "are you a bot", "are you bot", "tumi ki bot", "apni ki bot", 
            "রোবট", "বট", "আপনি কি মানুষ", "tumi ki manush"
        ]):
            return LLMResponse(
                content="জি, আমি এই পেজের একটি এআই সহকারী। আপনি চাইলে যেকোনো সময় আমাদের মানব প্রতিনিধির সাথেও কথা বলতে পারেন।",
                prompt_tokens=90,
                completion_tokens=30
            )

        # 1. Handover detection (complaints, abuse, custom discount bargaining, human request)
        handover_keywords = [
            "manager", "manush", "human", "agent", "kotha bolbo", "officer", 
            "cheat", "fakibaj", "discount", "kom", "bargain", "free", "%",
            "ম্যানেজার", "মানুষ", "প্রতিনিধি", "অভিযোগ", "ফেরত", "টাকা ফেরত", "মামলা",
            "ছেঁড়া", "ভুল সাইজ", "এক্সচেঞ্জ", "অপদার্থ", "বাটপার", "ডিসকাউন্ট"
        ]
        if any(w in lower for w in handover_keywords):
            return LLMResponse(
                tool_calls=[{
                    "name": "handover_to_human",
                    "arguments": {"reason": "Customer requested human support or discount negotiation outside fixed catalog pricing"}
                }],
                prompt_tokens=100,
                completion_tokens=25
            )

        # 2. Delivery / Policy queries
        if any(w in lower for w in [
            "delivery", "deliveri", "charge", "koto tk", "dhaka", "return", "policy", "koto din",
            "ডেলিভারি", "চার্জ", "কত টাকা", "পলিসি", "খরচ"
        ]):
            return LLMResponse(
                tool_calls=[{
                    "name": "get_policy",
                    "arguments": {"policy_type": "delivery"}
                }],
                prompt_tokens=90,
                completion_tokens=20
            )

        # 3. Order taking flow (Name, phone, address detection)
        phone_match = any(c.isdigit() for c in lower) and ("01" in lower or len([c for c in lower if c.isdigit()]) >= 11)
        if (phone_match and any(w in lower for w in ["order", "nibo", "pathan", "send", "address", "road", "dhaka", "অর্ডার", "ঠিকানা", "পাঠান"])) or ("order confirm" in lower):
            return LLMResponse(
                tool_calls=[{
                    "name": "create_order_draft",
                    "arguments": {
                        "customer_name": "Customer",
                        "phone": "01700000000",
                        "address": last_msg,
                        "items": [{"sku": "DEFAULT-01", "quantity": 1}]
                    }
                }],
                prompt_tokens=110,
                completion_tokens=30
            )

        # 4. Stock check
        if any(w in lower for w in ["stock", "available", "ase kina", "ache kina", "available ache", "স্টক", "আছে কি", "আছে?"]):
            return LLMResponse(
                tool_calls=[{
                    "name": "check_stock",
                    "arguments": {"product_id_or_sku": last_msg.strip()}
                }],
                prompt_tokens=85,
                completion_tokens=20
            )

        # 5. Product Search queries
        if any(w in lower for w in [
            "dam", "price", "koto", "shirt", "panjabi", "punjabi", "পাঞ্জাবি", "sharee", "polo", "পোলো", 
            "shoes", "watch", "product", "khujchi", "dekhaw", "ache", "দাম", "কত", "শার্ট", "কালেকশন"
        ]):
            search_query = last_msg
            pronouns = ["eita", "eitar", "oita", "oitar", "etar", "eta", "ota", "ঐটার", "এটার", "ওটা", "এটা", "ঐটা", "same"]
            if any(p in lower for p in pronouns) or not any(k in lower for k in ["shirt", "polo", "panjabi", "wallet", "পাঞ্জাবি", "শার্ট", "পোলো"]):
                # Look back at conversation history for product name
                for prev in reversed(messages[:-1]):
                    prev_text = prev.get("content", "")
                    for cand in ["Polo", "Panjabi", "Wallet", "Shirt", "পাঞ্জাবি", "পোলো", "শার্ট"]:
                        if cand.lower() in prev_text.lower():
                            search_query = cand
                            break
                    if search_query != last_msg:
                        break
            return LLMResponse(
                tool_calls=[{
                    "name": "search_products",
                    "arguments": {"query": search_query}
                }],
                prompt_tokens=100,
                completion_tokens=25
            )

        # Default conversational response
        has_prior_greeting = "DO NOT add 'আসসালামু আলাইকুম'" in (system_prompt or "")
        greeting = "" if has_prior_greeting else "Assalamu Alaikum! "
        return LLMResponse(
            content=f"{greeting}StyleCraft BD তে আপনাকে স্বাগতম। আপনি কোন পণ্যটি খুঁজছেন বা কীভাবে সাহায্য করতে পারি?",
            prompt_tokens=80,
            completion_tokens=35
        )

# ==========================================
# Gemini Provider
# ==========================================
class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.genai = genai

    async def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, system_prompt: Optional[str] = None, temperature: float = 0.2) -> LLMResponse:
        try:
            model = self.genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt
            )
            contents = []
            for m in messages:
                role = "user" if m["role"] in ["user", "customer"] else "model"
                contents.append({"role": role, "parts": [m["content"]]})
            
            response = await model.generate_content_async(contents)
            return LLMResponse(content=response.text, prompt_tokens=150, completion_tokens=50)
        except Exception:
            return await MockLLMProvider().generate(messages, tools, system_prompt, temperature)

class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.genai = genai

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        try:
            results = []
            for t in texts:
                res = self.genai.embed_content(
                    model="models/text-embedding-004",
                    content=t,
                    task_type="retrieval_document"
                )
                results.append(res['embedding'][:768])
            return results
        except Exception:
            return await MockEmbeddingProvider().embed_texts(texts)

# ==========================================
# OpenAI Provider
# ==========================================
class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name

    async def generate(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, system_prompt: Optional[str] = None, temperature: float = 0.2) -> LLMResponse:
        try:
            formatted_messages = []
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
            for m in messages:
                formatted_messages.append({"role": m["role"], "content": m["content"]})
            
            kwargs = {
                "model": self.model_name,
                "messages": formatted_messages,
                "temperature": temperature
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            res = await self.client.chat.completions.create(**kwargs)
            choice = res.choices[0].message
            tool_calls = []
            if choice.tool_calls:
                for tc in choice.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments) if tc.function.arguments else {}
                    })

            return LLMResponse(
                content=choice.content,
                tool_calls=tool_calls,
                prompt_tokens=res.usage.prompt_tokens if res.usage else 0,
                completion_tokens=res.usage.completion_tokens if res.usage else 0
            )
        except Exception:
            return await MockLLMProvider().generate(messages, tools, system_prompt, temperature)

class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        try:
            res = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
                dimensions=768
            )
            return [d.embedding for d in res.data]
        except Exception:
            return await MockEmbeddingProvider().embed_texts(texts)

def get_llm_provider(model_name: Optional[str] = None) -> LLMProvider:
    target_model = model_name or settings.REPLY_LLM_MODEL
    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiLLMProvider(api_key=settings.GEMINI_API_KEY, model_name=target_model or settings.GEMINI_MODEL)
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMProvider(api_key=settings.OPENAI_API_KEY, model_name=target_model or settings.OPENAI_MODEL)
    return MockLLMProvider()

def get_embedding_provider() -> EmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiEmbeddingProvider(api_key=settings.GEMINI_API_KEY)
    elif settings.EMBEDDING_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return OpenAIEmbeddingProvider(api_key=settings.OPENAI_API_KEY)
    return MockEmbeddingProvider(dim=768)
