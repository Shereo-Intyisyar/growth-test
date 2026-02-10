"""
EasyOCR method for odometer reading.

EasyOCR uses deep learning models and can be more robust than
Tesseract for certain image conditions. Optimized here for
digit-only recognition.
"""

import cv2
import numpy as np
from .postprocessor import postprocess_result

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# Lazy-load the reader to avoid slow startup
_reader = None


def _get_reader():
    global _reader
    if _reader is None and EASYOCR_AVAILABLE:
        try:
            _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        except Exception:
            return None
    return _reader


def is_available():
    return EASYOCR_AVAILABLE


def recognize(variants):
    """Run EasyOCR on preprocessed image variants.

    Args:
        variants: dict of preprocessed image variants

    Returns:
        dict with OCR result, or None if EasyOCR unavailable
    """
    reader = _get_reader()
    if reader is None:
        return None

    best_result = None
    best_confidence = -1

    # EasyOCR works best with the enhanced grayscale or original
    priority_variants = ["enhanced_gray", "gray", "adaptive", "otsu", "high_contrast"]

    for variant_name in priority_variants:
        if variant_name not in variants:
            continue
        img = variants[variant_name]

        try:
            # EasyOCR expects either path, numpy array, or bytes
            results = reader.readtext(
                img,
                allowlist="0123456789",
                paragraph=True,
                detail=1,
                min_size=10,
            )

            if not results:
                continue

            # Combine all detected text
            all_text = ""
            all_conf = []
            for detection in results:
                bbox, text, conf = detection
                all_text += text
                all_conf.append(conf * 100)  # Convert to 0-100 scale

            avg_conf = sum(all_conf) / len(all_conf) if all_conf else 0

            result = postprocess_result(all_text, avg_conf)
            result["variant"] = variant_name
            result["method"] = "easyocr"
            result["detections"] = len(results)

            if result["is_valid"] and result["confidence"] > best_confidence:
                best_confidence = result["confidence"]
                best_result = result

        except Exception:
            continue

    return best_result
