"""
Post-processing and validation for OCR results.

Handles common OCR errors specific to seven-segment displays and
validates that results look like plausible odometer readings.
"""

import re

# Common OCR misreadings for seven-segment displays
CHAR_CORRECTIONS = {
    "O": "0", "o": "0",
    "I": "1", "l": "1", "i": "1", "|": "1",
    "S": "5", "s": "5",
    "B": "8", "b": "8",
    "G": "6", "g": "6",
    "Z": "2", "z": "2",
    "T": "7", "t": "7",
    "q": "9", "Q": "9",
    "D": "0", "d": "0",
    " ": "", ".": "", ",": "", "-": "",
    "A": "4", "a": "4",
}


def correct_common_errors(text):
    """Fix common OCR misreadings for seven-segment digits."""
    corrected = ""
    for char in text:
        if char in CHAR_CORRECTIONS:
            corrected += CHAR_CORRECTIONS[char]
        elif char.isdigit():
            corrected += char
        # Skip any other non-digit characters
    return corrected


def extract_digits(text):
    """Extract only digit characters from text."""
    return re.sub(r"[^0-9]", "", text)


def validate_odometer_reading(digits):
    """Validate that a digit string looks like a plausible odometer reading.

    Returns:
        tuple: (is_valid, reason)
    """
    if not digits:
        return False, "No digits found"

    length = len(digits)
    if length < 3:
        return False, f"Too few digits ({length}), expected 3-8"
    if length > 8:
        return False, f"Too many digits ({length}), expected 3-8"

    return True, "OK"


def calculate_confidence(raw_text, cleaned_digits, method_confidence=None):
    """Calculate overall confidence score for an OCR result.

    Factors:
    - Method's own confidence score
    - How many characters needed correction
    - Whether digit count is in expected range (5-7)
    - Character clarity (ratio of digits to total characters)
    """
    score = 50.0  # Base score

    # Factor 1: Method confidence (if provided)
    if method_confidence is not None:
        score = method_confidence * 0.5 + score * 0.5

    # Factor 2: Digit count in expected range
    if cleaned_digits:
        length = len(cleaned_digits)
        if 5 <= length <= 7:
            score += 15
        elif 4 <= length <= 8:
            score += 5
        else:
            score -= 20

    # Factor 3: Ratio of clean digits to raw text
    if raw_text and len(raw_text) > 0:
        raw_digits = sum(1 for c in raw_text if c.isdigit())
        ratio = raw_digits / len(raw_text)
        score += ratio * 20

    # Factor 4: Validation
    is_valid, _ = validate_odometer_reading(cleaned_digits)
    if is_valid:
        score += 10
    else:
        score -= 15

    return max(0, min(100, round(score, 1)))


def postprocess_result(raw_text, method_confidence=None):
    """Full post-processing pipeline for an OCR result.

    Args:
        raw_text: Raw text from OCR engine
        method_confidence: Confidence score from OCR engine (0-100)

    Returns:
        dict with cleaned result and metadata
    """
    # Step 1: Correct common seven-segment misreadings
    corrected = correct_common_errors(raw_text)

    # Step 2: Extract only digits
    digits = extract_digits(corrected)

    # Step 3: Validate
    is_valid, validation_msg = validate_odometer_reading(digits)

    # Step 4: Calculate confidence
    confidence = calculate_confidence(raw_text, digits, method_confidence)

    return {
        "raw": raw_text,
        "corrected": corrected,
        "digits": digits,
        "reading": int(digits) if digits else None,
        "is_valid": is_valid,
        "validation": validation_msg,
        "confidence": confidence,
    }
