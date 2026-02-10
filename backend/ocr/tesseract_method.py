"""
Tesseract OCR method for odometer reading.

Uses pytesseract with digit-only whitelist and multiple
PSM (Page Segmentation Mode) configurations to find the best result.
"""

import cv2
import numpy as np
from .postprocessor import postprocess_result

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


def is_available():
    """Check if Tesseract is installed and accessible."""
    if not TESSERACT_AVAILABLE:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def recognize(variants):
    """Run Tesseract OCR with multiple configurations.

    Tries several PSM modes and preprocessing variants,
    then picks the result with the highest confidence.

    Args:
        variants: dict of preprocessed image variants

    Returns:
        dict with OCR result, or None if Tesseract unavailable
    """
    if not is_available():
        return None

    configs = [
        # PSM 7: Treat image as single text line
        "--psm 7 -c tessedit_char_whitelist=0123456789",
        # PSM 8: Treat image as single word
        "--psm 8 -c tessedit_char_whitelist=0123456789",
        # PSM 13: Raw line - treat as single text line, no Tesseract hacks
        "--psm 13 -c tessedit_char_whitelist=0123456789",
        # PSM 6: Assume uniform block of text
        "--psm 6 -c tessedit_char_whitelist=0123456789",
    ]

    best_result = None
    best_confidence = -1

    for variant_name, img in variants.items():
        # Ensure image is suitable for Tesseract
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        for config in configs:
            try:
                # Get detailed data including confidence per character
                data = pytesseract.image_to_data(
                    img, config=config, output_type=pytesseract.Output.DICT
                )

                # Also get simple text
                text = pytesseract.image_to_string(img, config=config).strip()

                # Calculate average confidence from character data
                confidences = [
                    int(c) for c, t in zip(data["conf"], data["text"])
                    if int(c) > 0 and t.strip()
                ]
                avg_conf = sum(confidences) / len(confidences) if confidences else 0

                result = postprocess_result(text, avg_conf)
                result["variant"] = variant_name
                result["config"] = config
                result["method"] = "tesseract"

                if result["is_valid"] and result["confidence"] > best_confidence:
                    best_confidence = result["confidence"]
                    best_result = result

            except Exception:
                continue

    # If no valid result found, try to return best invalid result
    if best_result is None:
        for variant_name, img in variants.items():
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            try:
                text = pytesseract.image_to_string(
                    img,
                    config="--psm 7 -c tessedit_char_whitelist=0123456789"
                ).strip()
                result = postprocess_result(text, 30)
                result["variant"] = variant_name
                result["method"] = "tesseract"
                if result["digits"] and len(result["digits"]) >= 3:
                    return result
            except Exception:
                continue

    return best_result
