import re

# Unicode range for Bengali characters: U+0980 to U+09FF
BANGLA_CHAR_PATTERN = re.compile(r"[\u0980-\u09FF]")

# Distinctive Banglish words / phonetic tokens (excluding purely English words like stock, size, color)
BANGLISH_PATTERNS = [
    r"\b(vai|bhai|apu|apa|dada)\b",
    r"\b(dam|daam|koto)\b",
    r"\b(eitar|eita|atar|eta|etar|oitar|oita)\b",
    r"\b(nibo|nibona|lagbe|lagbena|chai)\b",
    r"\b(kobe|kivabe|kemne|kemon|koi|kothay)\b",
    r"\b(ache|ase|achhe|nai|paini|pabo)\b",
    r"\b(apnader|apnar|amader|amar)\b",
    r"\b(dhaka|dhakar|chittagong|ctg|bhitore|baire|vitore)\b",
    r"\b(pathan|pathaben|pathai)\b",
    r"\b(korte|korbo|korben|korle)\b",
    r"\b(thikana|nam|shundor|bhalo|valo|kharap)\b"
]
BANGLISH_REGEX = re.compile("|".join(BANGLISH_PATTERNS), re.IGNORECASE)

def detect_language(text: str) -> str:
    """
    Detects whether text is in:
    - 'bangla' (Bengali script)
    - 'banglish' (Bengali phonetics written in Latin script)
    - 'english' (Standard English)
    """
    if not text or not text.strip():
        return "english"

    stripped = text.strip()

    # 1. Count Bengali Unicode characters
    bangla_chars = len(BANGLA_CHAR_PATTERN.findall(stripped))
    total_alpha = len([c for c in stripped if c.isalpha()])

    if total_alpha > 0 and (bangla_chars / total_alpha) > 0.25:
        return "bangla"
    if bangla_chars >= 2:
        return "bangla"

    # 2. Check for Banglish phonetic keywords
    banglish_matches = len(BANGLISH_REGEX.findall(stripped))
    
    words = [w for w in re.split(r"\s+", stripped) if w]
    if len(words) > 0 and (banglish_matches / len(words)) >= 0.15:
        return "banglish"
    if banglish_matches >= 2:
        return "banglish"
    if banglish_matches == 1 and len(words) <= 4:
        return "banglish"

    # 3. Default to English
    return "english"
