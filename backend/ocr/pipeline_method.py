"""
Full pipeline OCR method inspired by umutkavakli/odometer-mileage-extraction.

Their approach:
  1. YOLO detects the odometer display bounding box
  2. Crop to just that region
  3. EasyOCR reads digits from the clean crop

Our implementation replaces YOLO with OpenCV-based display detection
(no trained model needed), then uses both EasyOCR and Tesseract on
the cropped region.

This is the primary method — it addresses the core failure mode of
running OCR on full dashboard photos instead of just the display.
"""

import cv2
import numpy as np
from .display_detector import detect_display_region
from .preprocessor import (
    to_grayscale, enhance_contrast_clahe, reduce_noise,
    adaptive_threshold, otsu_threshold, invert_if_needed,
    morphological_cleanup, sharpen, image_to_base64
)
from .postprocessor import postprocess_result

try:
    import easyocr
    _reader = None

    def _get_reader():
        global _reader
        if _reader is None:
            _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        return _reader

    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

    def _get_reader():
        return None

try:
    import pytesseract
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False


def _preprocess_display_crop(crop):
    """Preprocess a cropped display region for OCR.

    This is tuned for already-isolated display regions — much simpler
    than full-image preprocessing because we've already removed the
    dashboard background, text labels, etc.
    """
    gray = to_grayscale(crop)

    # Enhance contrast
    enhanced = enhance_contrast_clahe(gray, clip_limit=2.0, tile_size=4)

    # Light denoise
    denoised = reduce_noise(enhanced, 3)

    return {
        "gray": gray,
        "enhanced": enhanced,
        "denoised": denoised,
    }


def _run_easyocr(img_variants):
    """Run EasyOCR on display crop variants. Returns best result."""
    reader = _get_reader()
    if reader is None:
        return None

    best_result = None
    best_conf = -1

    for name, img in img_variants.items():
        try:
            detections = reader.readtext(
                img,
                allowlist="0123456789",
                paragraph=False,
                detail=1,
                min_size=5,
                text_threshold=0.3,
                low_text=0.3,
            )

            if not detections:
                continue

            # Sort detections left-to-right by x position
            detections.sort(key=lambda d: d[0][0][0])

            text = ""
            confs = []
            for bbox, det_text, conf in detections:
                text += det_text
                confs.append(conf * 100)

            avg_conf = sum(confs) / len(confs) if confs else 0
            result = postprocess_result(text, avg_conf)
            result["method"] = "pipeline_easyocr"
            result["variant"] = name
            result["sub_detections"] = len(detections)

            if result["is_valid"] and result["confidence"] > best_conf:
                best_conf = result["confidence"]
                best_result = result

        except Exception:
            continue

    return best_result


def _run_tesseract(img_variants):
    """Run Tesseract on display crop variants. Returns best result."""
    if not TESSERACT_AVAILABLE:
        return None

    configs = [
        "--psm 7 -c tessedit_char_whitelist=0123456789",
        "--psm 8 -c tessedit_char_whitelist=0123456789",
        "--psm 13 -c tessedit_char_whitelist=0123456789",
    ]

    best_result = None
    best_conf = -1

    for name, img in img_variants.items():
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Generate binary variants for Tesseract
        binary_variants = {}
        binary_variants[f"{name}_raw"] = img

        # Otsu
        _, otsu = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binary_variants[f"{name}_otsu"] = otsu
        binary_variants[f"{name}_otsu_inv"] = cv2.bitwise_not(otsu)

        # Adaptive
        block = max(11, (img.shape[1] // 10) | 1)
        adaptive = cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, 8
        )
        binary_variants[f"{name}_adaptive"] = adaptive
        binary_variants[f"{name}_adaptive_inv"] = cv2.bitwise_not(adaptive)

        for bname, bimg in binary_variants.items():
            for config in configs:
                try:
                    text = pytesseract.image_to_string(bimg, config=config).strip()
                    data = pytesseract.image_to_data(
                        bimg, config=config, output_type=pytesseract.Output.DICT
                    )
                    confidences = [
                        int(c) for c, t in zip(data["conf"], data["text"])
                        if int(c) > 0 and t.strip()
                    ]
                    avg_conf = sum(confidences) / len(confidences) if confidences else 0

                    result = postprocess_result(text, avg_conf)
                    result["method"] = "pipeline_tesseract"
                    result["variant"] = bname

                    if result["is_valid"] and result["confidence"] > best_conf:
                        best_conf = result["confidence"]
                        best_result = result
                except Exception:
                    continue

    return best_result


def recognize(variants):
    """Run the full pipeline: detect display → crop → OCR.

    This method receives the standard preprocessed variants dict but
    ignores it in favor of working from the original image. It needs
    the original because display detection works on the full color image,
    not a preprocessed binary.

    We store the original image in the variants dict under the key
    '_original' (set by the ensemble module).

    Args:
        variants: dict with '_original' key containing the BGR image

    Returns:
        dict with OCR result, or None
    """
    original = variants.get("_original")
    if original is None:
        # Fallback: try to use the enhanced gray variant with EasyOCR directly
        return _run_easyocr(variants)

    # Step 1: Detect display region
    display_crop, bbox = detect_display_region(original)

    if display_crop is None:
        # No display detected — fall back to running on full image
        display_crop = original

    # Step 2: Preprocess the cropped display
    crop_variants = _preprocess_display_crop(display_crop)

    # Step 3: Run EasyOCR (primary — matches reference repo approach)
    easyocr_result = _run_easyocr(crop_variants)

    # Step 4: Run Tesseract (secondary)
    tess_result = _run_tesseract(crop_variants)

    # Pick the best result
    candidates = [r for r in [easyocr_result, tess_result] if r is not None]

    if not candidates:
        return None

    # Prefer the one with higher confidence
    best = max(candidates, key=lambda r: r.get("confidence", 0))
    best["method"] = "pipeline"
    best["display_detected"] = bbox is not None
    if bbox is not None:
        best["display_bbox"] = list(bbox)

    # If both agree, boost confidence
    if len(candidates) == 2:
        if candidates[0].get("reading") == candidates[1].get("reading"):
            best["confidence"] = min(99, best["confidence"] + 10)
            best["pipeline_agreement"] = True
        else:
            best["pipeline_agreement"] = False

    return best


def is_available():
    """At least one OCR engine must be available."""
    return EASYOCR_AVAILABLE or TESSERACT_AVAILABLE
