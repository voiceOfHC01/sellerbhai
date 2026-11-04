import re
from typing import Set, Tuple, Optional, List, Dict, Any
from app.ai.prompts import to_english_digits

def extract_numbers_from_text(text: str) -> Set[int]:
    """
    Extracts all whole numbers from text, converting Bengali digits to standard integers.
    Ignores punctuation and extracts sequences of digits.
    """
    eng_text = to_english_digits(text)
    # Find all sequences of digits
    raw_numbers = re.findall(r'\b\d+\b', eng_text)
    numbers = set()
    for n in raw_numbers:
        try:
            val = int(n)
            # Filter out years like 2026 or trivial single zeros unless relevant
            numbers.add(val)
        except ValueError:
            pass
    return numbers

def sanitize_and_limit_questions(text: str) -> str:
    """
    Ensures at most ONE question is asked in the draft response.
    If multiple questions are present, keeps only the first question and drops subsequent ones.
    """
    # Split text into parts around question marks
    parts = re.split(r'(\?|？)', text)
    if len(parts) <= 3:
        # 1 question mark: parts has [pre_q, '?', post_q]
        return text
    
    # More than 1 question: Keep up through the first question
    first_part = "".join(parts[:2]).strip()
    return first_part

def clean_sentence_length(text: str, max_sentences: int = 3, max_words: int = 70) -> str:
    """
    Trims excessive text to at most max_sentences and max_words while maintaining grammatical closure.
    """
    # Split sentences by standard delimiters . ! ।
    sentences = re.split(r'([.!।\n]+)', text)
    reconstructed = []
    sentence_count = 0
    
    for i in range(0, len(sentences) - 1, 2):
        s_text = sentences[i].strip()
        sep = sentences[i+1] if i + 1 < len(sentences) else "."
        if s_text:
            reconstructed.append(s_text + sep)
            sentence_count += 1
            if sentence_count >= max_sentences:
                break
                
    result = " ".join(reconstructed).strip() if reconstructed else text
    
    # Word count check
    words = result.split()
    if len(words) > max_words:
        result = " ".join(words[:max_words])
        if not result.endswith(('.', '।', '!', '?')):
            result += "।"
            
    return result

def perform_draft_self_check(
    draft_reply: str,
    allowed_numbers: Set[int],
    detected_language: str,
    customer_message: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Self-checks AI draft before sending:
    1. Grounding check: Every number (price, fee, stock) must be in allowed_numbers.
    2. One question rule: Max 1 question mark.
    3. Conciseness: Max 3 sentences, <= 70 words.
    
    Returns (is_passed, final_draft, failure_reason)
    """
    if not draft_reply or not draft_reply.strip():
        return False, "", "Empty draft reply"

    clean_text = draft_reply.strip()
    
    # 1. Number Grounding Check
    draft_numbers = extract_numbers_from_text(clean_text)
    
    # Ignore common communicative counts (e.g. 1, 2, 3 items, 24 hours, 3 days return policy, 7 days)
    standard_whitelisted_numbers = {1, 2, 3, 4, 5, 7, 10, 11, 24, 60, 80, 120, 150}
    combined_allowed = allowed_numbers.union(standard_whitelisted_numbers)
    
    # Extract any customer provided numbers (e.g. phone numbers, their proposed quantities)
    customer_numbers = extract_numbers_from_text(customer_message)
    combined_allowed = combined_allowed.union(customer_numbers)
    
    unauthorized_numbers = draft_numbers - combined_allowed
    # Filter out year numbers like 2026, 2025
    unauthorized_numbers = {n for n in unauthorized_numbers if n not in [2024, 2025, 2026, 2027]}
    
    if unauthorized_numbers:
        reason = f"Draft contains ungrounded/invented price or number: {sorted(list(unauthorized_numbers))}"
        return False, clean_text, reason
        
    # 2. Limit to at most ONE question
    clean_text = sanitize_and_limit_questions(clean_text)
    
    # 3. Trim length if too wordy
    clean_text = clean_sentence_length(clean_text, max_sentences=3, max_words=70)
    
    return True, clean_text, None
