import re
from typing import Tuple


def check_guardrails(text: str) -> Tuple[bool, str]:
    """
    Check if text violates guardrails (currency, percent, large numbers).
    Returns (is_valid, cleaned_text).
    """
    if not text or not isinstance(text, str):
        return True, text or ""
    
    violations = []
    
    # Check for currency symbols
    if re.search(r'[$€£]', text):
        violations.append("currency")
    
    # Check for percent sign
    if '%' in text:
        violations.append("percent")
    
    # Check for large numbers (2+ digits), but allow "30 days" and "90 days"
    # Pattern: \b\d{2,}\b but exclude when followed by " days" or "day"
    number_pattern = r'\b\d{2,}\b'
    numbers = re.findall(number_pattern, text)
    for num in numbers:
        # Check if it's in a whitelisted context
        num_context = re.search(rf'\b{num}\s+days?\b', text, re.IGNORECASE)
        if not num_context:
            violations.append("large_number")
            break
    
    if violations:
        # Clean the text
        cleaned = text
        # Remove currency symbols
        cleaned = re.sub(r'[$€£]', '', cleaned)
        # Remove percent signs
        cleaned = cleaned.replace('%', '')
        # Replace large numbers with [value]
        cleaned = re.sub(r'\b(\d{2,})\b', '[value]', cleaned)
        # But restore "30 days" and "90 days"
        cleaned = re.sub(r'\[value\]\s+days?', '30 days', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\[value\]\s+days?', '90 days', cleaned, flags=re.IGNORECASE)
        
        return False, cleaned
    
    return True, text


def apply_guardrails_with_retry(text: str, regenerate_fn) -> str:
    """
    Apply guardrails and regenerate once if needed.
    Returns cleaned text.
    """
    is_valid, cleaned = check_guardrails(text)
    
    if is_valid:
        return text
    
    # Try once more with regenerated content
    regenerated = regenerate_fn()
    is_valid_retry, cleaned_retry = check_guardrails(regenerated)
    
    if is_valid_retry:
        return regenerated
    
    # Return cleaned version of regenerated text
    return cleaned_retry
