import json
from typing import List, Dict, Any, Optional
from app.ai.providers import get_llm_provider

SYSTEM_PROMPT = """You are an expert Bangladeshi social media copywriter and marketing strategist for Facebook Pages and Instagram.
Your job is to generate 3 high-converting post variants for Bangladeshi online shops based on merchant notes and product details.

Guidelines:
1. Generate exactly 3 distinct variants with different angles:
   - Variant 1: Direct Value & Promotional (Focus on product features, price, delivery offer, clear CTA)
   - Variant 2: Lifestyle & Engaging Story (Focus on everyday relatable context, benefits, emotional connection)
   - Variant 3: Urgency / Curiosity Hook (Focus on limited stock, trend, exclusive offer, question)
2. Honor the requested Language:
   - "Bangla": Natural, modern Unicode Bengali script (বাংলা) used by top Bangladeshi brands.
   - "Banglish": Natural phonetic Romanized Bengali (e.g. "Assalamu Alaikum! Apnader jonno niye elam...").
   - "English": Polished, engaging global e-commerce English.
3. Honor the requested Tone (e.g. Friendly, Sales / Promotional, Urgent / Limited Offer, Formal, Storytelling).
4. Include authentic Bangladeshi social commerce elements:
   - Cash on delivery mention ("ক্যাশ অন ডেলিভারি সুবিধা", "Cash on delivery available")
   - Clear delivery charge notes (e.g. Dhaka inside/outside)
   - Clear Call-to-Action ("অর্ডার করতে ইনবক্স করুন", "Order korte inbox korun")
   - 4-8 popular, targeted hashtags (e.g. #BDOnlineShop #DhakaShopping #BangladeshiBrand #FashionBD).
5. Output MUST be valid JSON with the format:
{
  "variants": [
    {
      "variant_number": 1,
      "style_description": "Promotional & Direct Value",
      "title": "...",
      "caption": "...",
      "hashtags": "#tag1 #tag2 ..."
    },
    ...
  ]
}
"""

def generate_offline_variants(
    notes: str,
    product_title: Optional[str],
    price: Optional[float],
    language: str,
    tone: str
) -> List[Dict[str, Any]]:
    """Generates 3 realistic Bangladeshi commerce post variants when offline or in test environments."""
    prod_name = product_title or "এক্সক্লুসিভ কালেকশন" if language == "Bangla" else (product_title or "Exclusive Collection")
    price_str = f"৳{int(price)}" if price else "সেরা মূল্যে" if language == "Bangla" else "Special Price"

    if language == "Bangla":
        v1 = {
            "variant_number": 1,
            "style_description": "অফার ও সেলস-ফোকাসড (Direct Offer & Value)",
            "title": f"✨ প্রিমিয়াম কোয়ালিটি {prod_name} — আকর্ষণীয় অফারে!",
            "caption": (
                f"আসসালামু আলাইকুম! আপনার পছন্দের {prod_name} এখন আমাদের স্টকে এভেইলএবল।\n\n"
                f"🌟 মূল আকর্ষণ:\n"
                f"• {notes or '১০০% অরিজিনাল কোয়ালিটি এবং নিখুঁত ফিনিশিং'}\n"
                f"• মূল্য: মাত্র {price_str}\n"
                f"• সারা বাংলাদেশে দ্রুত ক্যাশ অন ডেলিভারি 🚚\n\n"
                f"📦 ঢাকার ভেতরে ডেলিভারি চার্জ ৬০ টাকা, ঢাকার বাইরে ১২০ টাকা।\n"
                f"পণ্য হাতে পেয়ে দেখে মূল্য পরিশোধ করার সুবিধা রয়েছে।\n\n"
                f"👉 অর্ডার করতে এখনই পেইজে ইনবক্স করুন অথবা আপনার ফোন নম্বর কমেন্ট করুন!"
            ),
            "hashtags": "#BDOnlineShop #ExclusiveCollection #DhakaShopping #BangladeshiBrand #CashOnDeliveryBD #FreeDelivery"
        }
        v2 = {
            "variant_number": 2,
            "style_description": "লাইফস্টাইল ও আন্তরিক উপস্থাপন (Lifestyle & Friendly)",
            "title": f"🌿 দৈনন্দিন ব্যবহারের জন্য পারফেক্ট {prod_name}",
            "caption": (
                f"একটু ভিন্নতা আর স্বাচ্ছন্দ্য খুঁজছেন? আমাদের {prod_name} আপনার দৈনন্দিন লুকে আনবে দারুণ আভিজাত্য।\n\n"
                f"গুণগত মান এবং আরামদায়ক অনুভূতির শতভাগ নিশ্চয়তা দিচ্ছি আমরা।\n"
                f"{notes if notes else 'সীমিত স্টক, তাই দেরি না করে আপনারটি এখনই সুরক্ষিত করুন।'}\n\n"
                f"💰 মূল্য: {price_str}\n"
                f"✅ ১০০% ক্যাশ অন ডেলিভারি সাপোর্ট।\n\n"
                f"📩 বিস্তারিত জানতে বা বুকিং করতে ইনবক্সে মেসেজ পাঠান।"
            ),
            "hashtags": "#LifestyleBD #DailyEssentials #FashionBD #DhakaTrends #OnlineShoppingBD"
        }
        v3 = {
            "variant_number": 3,
            "style_description": "সীমিত স্টক ও জরুরি কল-টু-অ্যাকশন (Urgent & Limited Stock)",
            "title": f"🔥 স্টক সীমিত! দ্রুত সংগ্রহ করুন আপনার {prod_name}",
            "caption": (
                f"অসাধারণ সাড়া পেয়েছি আপনাদের কাছ থেকে! আমাদের {prod_name}-এর স্টক প্রায় শেষ পর্যায়ে।\n\n"
                f"⚡ অফার প্রাইস: {price_str}\n"
                f"⚡ {notes or 'সর্বোচ্চ কোয়ালিটি নিশ্চিত করে আমরা দিচ্ছি সেরা ডিল।'}\n\n"
                f"দেরি করলে পছন্দের সাইজ বা ভ্যারিয়েন্ট মিস হতে পারে! এখনই 'Send Message' বাটনে ক্লিক করে অর্ডার কনফার্ম করুন। 🛒"
            ),
            "hashtags": "#LimitedStock #FlashSaleBD #BestDealBD #ShopNowBD #TrendingBD"
        }
    elif language == "Banglish":
        v1 = {
            "variant_number": 1,
            "style_description": "Direct Offer & Value (অফার ও সেলস-ফোকাসড)",
            "title": f"✨ Premium Quality {prod_name} - Best Offer Price!",
            "caption": (
                f"Assalamu Alaikum! Apnader shobai ke swagotom. Amader new collection-e chole esheche {prod_name}!\n\n"
                f"Highlights:\n"
                f"• {notes or '100% premium quality guaranteed'}\n"
                f"• Price: matro {price_str}\n"
                f"• Shara Bangladesh-e Cash on Delivery available 🚚\n\n"
                f"Dhakar vitore delivery matro 60 taka, bahire 120 taka. Hate peye check kore taka diben!\n\n"
                f"👉 Order korte ekhoni Inbox korun ba comment korun!"
            ),
            "hashtags": "#BDOnlineShop #BanglishPost #DhakaShopping #CashOnDelivery #BestPriceBD"
        }
        v2 = {
            "variant_number": 2,
            "style_description": "Friendly & Engaging (বন্ধুত্বপূর্ণ ও স্টোরিটেলিং)",
            "title": f"🌿 Comfort & Style eksathe - {prod_name}",
            "caption": (
                f"Apnar daily style-e unique look ante amader {prod_name} perfectly match korbe.\n\n"
                f"{notes or 'Comfortable finish ebong durable quality.'}\n\n"
                f"💰 Special Price: {price_str}\n"
                f"✅ Cash on delivery shob jaygay available.\n\n"
                f"📩 Aro jante ba order confirm korte amader Page Inbox-e knock korun!"
            ),
            "hashtags": "#DailyStyleBD #FashionBangla #DhakaVibes #OnlineStoreBD"
        }
        v3 = {
            "variant_number": 3,
            "style_description": "Urgent & Limited Stock (দ্রুত অর্ডারের জন্য)",
            "title": f"🔥 Hurry Up! Limited Stock for {prod_name}",
            "caption": (
                f"Eto sundor response pabo asha korini! Amader {prod_name}-er stock khub druto shesh hoye jacche.\n\n"
                f"⚡ Price: {price_str}\n"
                f"⚡ {notes or 'Late korle miss hoye jete pare.'}\n\n"
                f"Ekdom miss korben na. Ekhoni Send Message click kore apnar order confirm korun! 🛒"
            ),
            "hashtags": "#LimitedStockBD #FlashSale #OrderNow #DhakaBoutique"
        }
    else:  # English
        v1 = {
            "variant_number": 1,
            "style_description": "Promotional & Direct Value",
            "title": f"✨ Discover Our Premium {prod_name} at an Unbeatable Price",
            "caption": (
                f"Elevate your lifestyle with our newly stocked {prod_name}!\n\n"
                f"Key Features:\n"
                f"• {notes or 'Premium craftsmanship and authentic build quality'}\n"
                f"• Price: Only {price_str}\n"
                f"• Nationwide Cash on Delivery across Bangladesh 🚚\n\n"
                f"Inspect your parcel before payment. Fast dispatch guaranteed!\n\n"
                f"👉 Click 'Send Message' or DM us to place your order now."
            ),
            "hashtags": "#EcommerceBD #DhakaShopping #PremiumQuality #CashOnDelivery #ShopOnlineBD"
        }
        v2 = {
            "variant_number": 2,
            "style_description": "Storytelling & Brand Focus",
            "title": f"🌿 Crafted for Comfort and Everyday Elegance - {prod_name}",
            "caption": (
                f"Looking for something that blends effortless style with enduring comfort? Our {prod_name} is curated just for you.\n\n"
                f"{notes or 'Designed to give you a standout look for any occasion.'}\n\n"
                f"💰 Price: {price_str}\n"
                f"📦 Hassle-free home delivery throughout Bangladesh.\n\n"
                f"📩 Send us a direct message today to reserve yours."
            ),
            "hashtags": "#StyleInspiration #CuratedCollection #OnlineShoppingDhaka #BangladeshShop"
        }
        v3 = {
            "variant_number": 3,
            "style_description": "Urgent & Limited Offer",
            "title": f"🔥 Selling Out Fast: Limited Stock of {prod_name}!",
            "caption": (
                f"Due to high demand, quantities of our {prod_name} are strictly limited.\n\n"
                f"⚡ Special Price: {price_str}\n"
                f"⚡ {notes or 'Grab yours before sizes and stock run out.'}\n\n"
                f"Don't wait! Tap the message button below and secure your order right away. 🛒"
            ),
            "hashtags": "#LimitedOffer #TrendingBD #ShopNow #ExclusiveDrop"
        }

    return [v1, v2, v3]

async def generate_post_variants(
    notes: str,
    product_title: Optional[str] = None,
    price: Optional[float] = None,
    language: str = "Bangla",
    tone: str = "Friendly"
) -> List[Dict[str, Any]]:
    """
    Generates 3 rich social media post variants tailored for Facebook & Instagram.
    """
    llm = get_llm_provider()
    prompt = (
        f"Product/Item: {product_title or 'General Store Item'}\n"
        f"Base Price: {price if price else 'Not specified'}\n"
        f"Merchant Notes / Selling Points: {notes}\n"
        f"Selected Language: {language}\n"
        f"Selected Tone: {tone}\n\n"
        f"Please generate 3 distinct variants as JSON with keys 'variants' -> list of 3 items (variant_number, style_description, title, caption, hashtags)."
    )

    try:
        res = await llm.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7
        )
        if res.content:
            # Try to extract JSON from response
            cleaned = res.content.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(cleaned)
            variants = parsed.get("variants", [])
            if len(variants) >= 3:
                return variants[:3]
    except Exception:
        pass

    # Fallback to authentic offline generator
    return generate_offline_variants(
        notes=notes,
        product_title=product_title,
        price=price,
        language=language,
        tone=tone
    )
