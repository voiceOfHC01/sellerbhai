import re
from typing import Tuple, Optional

INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
    r"disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions",
    r"system\s+(?:override|prompt|instructions)",
    r"you\s+are\s+now\s+(?:in\s+)?(?:developer|god|dan|unrestricted)\s+mode",
    r"pretend\s+(?:you\s+have\s+no\s+rules|to\s+be\s+an\s+unrestricted)",
    r"(?:give|offer)\s+(?:me\s+)?(?:\d{2,3}%\s+discount|for\s+free|for\s+1\s+taka|at\s+0\s+price)",
    r"(?:override|bypass|hack)\s+(?:pricing|rules|guardrails|database)",
    r"i\s+am\s+(?:the\s+)?(?:admin|owner|developer|creator)\s+of\s+this\s+bot",
    r"reveal\s+(?:your\s+)?(?:system\s+prompt|hidden\s+instructions)"
]

INJECTION_REGEX = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

def detect_prompt_injection(text: str) -> Tuple[bool, Optional[str]]:
    """
    Scans customer input for prompt injection, jailbreak attempts, or unauthorized discount demands.
    Returns (is_injection: bool, matched_category: Optional[str])
    """
    if not text:
        return False, None

    m = INJECTION_REGEX.search(text)
    if m:
        return True, m.group(0)

    # Check for extreme discount bargaining > 50%
    disc_match = re.search(r'([6-9]\d|100)%\s*discount', text, re.IGNORECASE)
    if disc_match:
        return True, "unauthorized_extreme_discount"

    return False, None

def get_injection_defense_response(language: str) -> str:
    """Returns a firm, polite refusal in the customer's language."""
    if language == "bangla":
        return "দুঃখিত, আমাদের স্টোরের পণ্যের মূল্য এবং পলিসি সম্পূর্ণ নির্দিষ্ট। কোনো অননুমোদিত নির্দেশ বা অননুমোদিত ডিসকাউন্ট পরিবর্তন করা সম্ভব নয়। আপনি কি আমাদের নির্ধারিত মূল্যে পণ্যটি দেখতে চান?"
    elif language == "banglish":
        return "Dukkhito, amader store er price ebong policy fixed. Kono unverified discount ba rule change kora shombhob noy. Apni ki catalog price e order korte chan?"
    else:
        return "I apologize, but I must adhere strictly to official store policies and catalog prices. I cannot apply unauthorized discounts or alter system guidelines."
