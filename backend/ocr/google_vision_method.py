"""
Google Cloud Vision API method for odometer reading.

Uses Google's OCR to extract text from odometer images.
Sends the original color image and enhanced grayscale variants to the API.

Authentication (pick one):
  - Set GOOGLE_APPLICATION_CREDENTIALS to the path of a service account JSON key
  - Set GOOGLE_VISION_API_KEY to a Google Cloud API key with Vision API enabled
"""

import os
import cv2
import numpy as np
from .postprocessor import postprocess_result

try:
    from google.cloud import vision as _vision_lib
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    if not GOOGLE_VISION_AVAILABLE:
        return None

    try:
        api_key = os.environ.get("GOOGLE_VISION_API_KEY")
        if api_key:
            from google.api_core.client_options import ClientOptions
            opts = ClientOptions(api_key=api_key)
            _client = _vision_lib.ImageAnnotatorClient(client_options=opts)
        else:
            # Application Default Credentials (service account key file, etc.)
            _client = _vision_lib.ImageAnnotatorClient()
        return _client
    except Exception:
        return None


def is_available():
    """Return True if the library is installed and credentials are configured."""
    if not GOOGLE_VISION_AVAILABLE:
        return False
    has_creds = bool(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("GOOGLE_VISION_API_KEY")
    )
    return has_creds


def _encode_image(img):
    """Encode a numpy image array to JPEG bytes for the Vision API."""
    if img is None:
        return None
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    success, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not success:
        return None
    return buf.tobytes()


def _avg_word_confidence(full_text_annotation):
    """Extract average word-level confidence from a FullTextAnnotation."""
    confidences = []
    if not full_text_annotation:
        return None
    for page in full_text_annotation.pages:
        for block in page.blocks:
            for para in block.paragraphs:
                for word in para.words:
                    if hasattr(word, "confidence") and word.confidence is not None:
                        confidences.append(word.confidence * 100)
    return sum(confidences) / len(confidences) if confidences else None


def recognize(variants):
    """Run Google Cloud Vision OCR on the best available image variant.

    Tries variants in priority order:
      1. _original  — full-color photo; best for real-world odometer shots
      2. enhanced_gray — CLAHE-enhanced grayscale; good contrast boost
      3. gray — plain grayscale fallback

    Returns the highest-confidence valid result, or None if unavailable.
    """
    client = _get_client()
    if client is None:
        return None

    best_result = None
    best_confidence = -1

    priority_variants = ["_original", "enhanced_gray", "gray"]

    for variant_name in priority_variants:
        if variant_name not in variants:
            continue

        content = _encode_image(variants[variant_name])
        if content is None:
            continue

        try:
            image = _vision_lib.Image(content=content)

            # DOCUMENT_TEXT_DETECTION is better for dense / structured text
            response = client.document_text_detection(image=image)

            if response.error.message:
                continue

            full_text = ""
            if response.full_text_annotation:
                full_text = response.full_text_annotation.text
            elif response.text_annotations:
                full_text = response.text_annotations[0].description

            if not full_text:
                continue

            api_confidence = _avg_word_confidence(response.full_text_annotation)
            # Default to 70 if Vision API doesn't provide confidence scores
            if api_confidence is None:
                api_confidence = 70.0

            result = postprocess_result(full_text, api_confidence)
            result["variant"] = variant_name
            result["method"] = "google_vision"

            if result["is_valid"] and result["confidence"] > best_confidence:
                best_confidence = result["confidence"]
                best_result = result

        except Exception:
            continue

    return best_result
