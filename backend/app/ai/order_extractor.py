import re
from typing import Optional, Dict, Any, Tuple

# Mapping for Bengali numerals to Western digits
BN_NUMERALS_MAP = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

def normalize_digits(text: str) -> str:
    """Converts Bengali digits (০-৯) to Arabic numerals (0-9)."""
    return text.translate(BN_NUMERALS_MAP)

def extract_bd_phone(text: str) -> Optional[str]:
    """
    Extracts and normalizes a Bangladeshi mobile number from messy input.
    Valid BD mobile operators: 013, 014, 015, 016, 017, 018, 019.
    Normalizes both +8801XXXXXXXXX and 01XXXXXXXXX to standard 11 digits.
    """
    if not text:
        return None

    clean_text = normalize_digits(text)
    
    # First, handle international prefix +880 or 880
    # Strip spaces/dashes between digits
    subbed = re.sub(r'(?<=\d)[\s\-\.](?=\d)', '', clean_text)
    # Also handle '+880 1...' where space is after 880
    subbed = re.sub(r'\+?880\s*', '880', subbed)

    # 1. Match 8801XXXXXXXXX (13 digits)
    m1 = re.search(r'\b880(1[3-9]\d{8})\b', subbed)
    if m1:
        return f"0{m1.group(1)}"

    # 2. Match standard 01XXXXXXXXX (11 digits)
    m2 = re.search(r'\b(01[3-9]\d{8})\b', subbed)
    if m2:
        return m2.group(1)

    # 3. Handle raw digits extraction if spaced out: e.g. "01812 345 678"
    all_digits = re.sub(r'\D', '', clean_text)
    if len(all_digits) == 11 and all_digits.startswith("01") and all_digits[2] in "3456789":
        return all_digits
    elif len(all_digits) == 13 and all_digits.startswith("8801") and all_digits[4] in "3456789":
        return f"0{all_digits[3:]}"

    return None

def is_valid_bd_phone(phone: str) -> bool:
    """Validates if string is a strict 11-digit Bangladeshi mobile number."""
    if not phone:
        return False
    digits = re.sub(r'\D', '', normalize_digits(phone))
    return bool(re.match(r'^01[3-9]\d{8}$', digits))

def extract_payment_method(text: str) -> Optional[str]:
    """
    Identifies payment preference: COD, bKash, or Nagad.
    """
    if not text:
        return None
    lower = text.lower()
    
    if any(k in lower for k in ["bkash", "বিকাশ"]):
        return "bKash"
    if any(k in lower for k in ["nagad", "নগদ"]):
        return "Nagad"
    if any(k in lower for k in [
        "cod", "cash on delivery", "cash", "hath e", "hate peye", "হাতে পেয়ে", 
        "ক্যাশ অন ডেলিভারি", "ডেলিভারির সময়", "পণ্য পেয়ে"
    ]):
        return "COD"
    return None

def extract_quantity(text: str) -> int:
    """
    Extracts item quantity if specified (e.g. 2 ta, ২টা, 3 pcs, qty 2).
    """
    if not text:
        return 1
    clean = normalize_digits(text.lower())
    m = re.search(r'(\d+)\s*(?:ta|ti|টা|টি|piece|pcs|pair|set|জোড়া)', clean)
    if m:
        try:
            return max(1, int(m.group(1)))
        except ValueError:
            return 1
    return 1

def extract_customer_name(text: str) -> Optional[str]:
    """
    Extracts customer full name from input lines like 'নাম: তানভীর', 'Name: Tanvir', etc.
    """
    if not text:
        return None
    patterns = [
        r'(?:নাম|name|amar nam|আমার নাম)\s*[:=\-]?\s*([A-Za-z\u0980-\u09FF\s]{2,40})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            candidate = re.split(r'(?:phone|ফোন|ঠিকানা|address|বাসা|,|\d)', candidate, flags=re.IGNORECASE)[0].strip()
            if len(candidate) >= 2:
                return candidate
    return None

def extract_address(text: str) -> Optional[str]:
    """
    Extracts address portion from user message.
    """
    if not text:
        return None
    patterns = [
        r'(?:ঠিকানা|address|thikana)\s*[:=\-]?\s*([^\n\r]+?)(?=\s*(?:phone|ফোন|mobile|মোবাইল|নাম|name|payment|পেমেন্ট|$))',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().rstrip('।.,')
            if len(candidate) >= 4:
                return candidate

    areas = ["dhaka", "chittagong", "sylhet", "rajshahi", "khulna", "barisal", "rangpur", "gazipur", "narayanganj",
             "ঢাকা", "চট্টগ্রাম", "সিলেট", "রাজশাহী", "খুলনা", "মিরপুর", "ধানমন্ডি", "গুলশান", "উত্তরা", "বনানী", "বারিধারা",
             "road", "house", "বাড়ি", "রোড", "থানা", "বাসা"]
    lower = text.lower()
    if any(area in lower for area in areas):
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for line in lines:
            line_lower = line.lower()
            if any(area in line_lower for area in areas):
                clean_line = re.sub(r'^(?:বাসা|house|ঠিকানা|address)\s*[:=\-]?\s*', '', line, flags=re.IGNORECASE).strip().rstrip('।.,')
                if len(clean_line) >= 4:
                    return clean_line
        segments = re.split(r'[\n,]+', text)
        for seg in segments:
            seg_lower = seg.lower()
            if any(area in seg_lower for area in areas) and len(seg.strip()) >= 4:
                clean_seg = re.sub(r'^(?:বাসা|house|ঠিকানা|address)\s*[:=\-]?\s*', '', seg.strip(), flags=re.IGNORECASE).strip().rstrip('।.,')
                if len(clean_seg) >= 4:
                    return clean_seg

    return None
