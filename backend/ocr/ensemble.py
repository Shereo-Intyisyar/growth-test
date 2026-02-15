"""
Ensemble voting system for combining results from multiple OCR methods.

Strategy:
  1. Run the pipeline method first (display detection → crop → EasyOCR/Tesseract).
     This mirrors the approach from umutkavakli/odometer-mileage-extraction
     (YOLO detect → crop → EasyOCR) using OpenCV detection instead of YOLO.
  2. If pipeline produces a confident result, return immediately.
  3. Fall back to template matching + contour on preprocessed full image.
  4. Only run raw EasyOCR/Tesseract on full image as last resort.

Pipeline method handles real photos well because it isolates the display
region first. Template matching handles clean seven-segment images well.
"""

import time
from . import easyocr_method, tesseract_method, template_matching, contour_method
from . import pipeline_method
from .preprocessor import get_preprocessing_variants, image_to_base64

# Pipeline is the primary method — runs display detection + OCR on crop
PRIMARY_METHODS = ["pipeline"]
# Template matching + contour work on preprocessed full images
SECONDARY_METHODS = ["template_matching", "contour"]
# Raw EasyOCR/Tesseract on full image as last resort
FALLBACK_METHODS = ["tesseract", "easyocr"]

# Confidence thresholds for early exit
PRIMARY_CONFIDENCE_THRESHOLD = 65
SECONDARY_CONFIDENCE_THRESHOLD = 80


def _run_method(method, method_name, variants):
    """Run a single OCR method with timing."""
    start_time = time.time()
    try:
        result = method.recognize(variants)
        elapsed = round((time.time() - start_time) * 1000)
        if result:
            return result, elapsed
        return {
            "method": method_name, "digits": None, "reading": None,
            "confidence": 0, "is_valid": False,
            "error": "Method returned no result"
        }, elapsed
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000)
        return {
            "method": method_name, "digits": None, "reading": None,
            "confidence": 0, "is_valid": False, "error": str(e)
        }, elapsed


def run_all_methods(img, enabled_methods=None, params=None):
    """Run OCR methods in priority order with early exit.

    Priority:
      1. Pipeline (display detect → crop → EasyOCR+Tesseract) — best for real photos
      2. Template matching + contour — best for clean seven-segment images
      3. Raw EasyOCR + Tesseract on full image — last resort

    Pass enabled_methods=["all"] to force running every method.
    """
    force_all = enabled_methods is not None and "all" in enabled_methods

    if enabled_methods is None or force_all:
        enabled_methods = PRIMARY_METHODS + SECONDARY_METHODS + FALLBACK_METHODS

    all_methods = {
        "pipeline": pipeline_method,
        "easyocr": easyocr_method,
        "tesseract": tesseract_method,
        "template_matching": template_matching,
        "contour": contour_method,
    }

    # Preprocessing for template matching / contour methods
    variants, preprocessing_steps = get_preprocessing_variants(img, params)
    steps_b64 = [
        {"name": s["name"], "image": image_to_base64(s["image"])}
        for s in preprocessing_steps
    ]

    # Pass the original color image for display detection
    variants["_original"] = img

    results = {}
    timings = {}

    # --- Phase 1: Pipeline method (display detection → crop → OCR) ---
    if "pipeline" in enabled_methods and "pipeline" in all_methods:
        result, elapsed = _run_method(all_methods["pipeline"], "pipeline", variants)
        results["pipeline"] = result
        timings["pipeline"] = elapsed

        if not force_all and result.get("is_valid") and result.get("confidence", 0) >= PRIMARY_CONFIDENCE_THRESHOLD:
            ensemble = _vote(results)
            ensemble["phase"] = "primary"
            return {
                "methods": results,
                "ensemble": ensemble,
                "timings": timings,
                "preprocessing_steps": steps_b64,
                "total_time": sum(timings.values()),
            }

    # --- Phase 2: Template matching + contour on preprocessed image ---
    secondary_to_run = [m for m in SECONDARY_METHODS if m in enabled_methods and m in all_methods]
    for method_name in secondary_to_run:
        result, elapsed = _run_method(all_methods[method_name], method_name, variants)
        results[method_name] = result
        timings[method_name] = elapsed

    if not force_all and secondary_to_run:
        vote = _vote(results)
        if vote.get("is_valid") and vote.get("confidence", 0) >= SECONDARY_CONFIDENCE_THRESHOLD:
            vote["phase"] = "secondary"
            return {
                "methods": results,
                "ensemble": vote,
                "timings": timings,
                "preprocessing_steps": steps_b64,
                "total_time": sum(timings.values()),
            }

    # --- Phase 3: Fallback — raw EasyOCR/Tesseract on full image ---
    fallback_to_run = [m for m in FALLBACK_METHODS if m in enabled_methods and m in all_methods]
    for method_name in fallback_to_run:
        result, elapsed = _run_method(all_methods[method_name], method_name, variants)
        results[method_name] = result
        timings[method_name] = elapsed

    ensemble = _vote(results)
    ensemble["phase"] = "fallback"

    return {
        "methods": results,
        "ensemble": ensemble,
        "timings": timings,
        "preprocessing_steps": steps_b64,
        "total_time": sum(timings.values()),
    }


def _vote(results):
    """Ensemble voting to pick the best result.

    Strategy:
    1. Collect all valid readings
    2. If multiple methods agree on a reading, boost confidence
    3. Pick the result with the highest (potentially boosted) confidence
    """
    valid_results = {
        name: r for name, r in results.items()
        if r.get("is_valid") and r.get("reading") is not None
    }

    if not valid_results:
        best = max(results.values(), key=lambda r: r.get("confidence", 0))
        return {
            "reading": best.get("reading"),
            "digits": best.get("digits", ""),
            "confidence": best.get("confidence", 0),
            "method": best.get("method", "none"),
            "agreement": 0,
            "is_valid": False,
            "reason": "No valid readings from any method"
        }

    # Count how many methods agree on each reading
    reading_votes = {}
    for name, r in valid_results.items():
        reading = r["reading"]
        if reading not in reading_votes:
            reading_votes[reading] = {"count": 0, "methods": [], "max_confidence": 0}
        reading_votes[reading]["count"] += 1
        reading_votes[reading]["methods"].append(name)
        reading_votes[reading]["max_confidence"] = max(
            reading_votes[reading]["max_confidence"], r["confidence"]
        )

    best_reading = max(
        reading_votes.items(),
        key=lambda x: (x[1]["count"], x[1]["max_confidence"])
    )

    reading_value = best_reading[0]
    vote_info = best_reading[1]

    agreement_count = vote_info["count"]
    total_methods = len(valid_results)
    base_confidence = vote_info["max_confidence"]

    if agreement_count >= 3:
        boosted_confidence = min(99, base_confidence + 20)
    elif agreement_count >= 2:
        boosted_confidence = min(95, base_confidence + 10)
    else:
        boosted_confidence = base_confidence

    best_method = max(
        vote_info["methods"],
        key=lambda m: valid_results[m]["confidence"]
    )

    return {
        "reading": reading_value,
        "digits": str(reading_value),
        "confidence": round(boosted_confidence, 1),
        "method": best_method,
        "agreement": agreement_count,
        "total_methods": total_methods,
        "agreeing_methods": vote_info["methods"],
        "is_valid": True,
        "reason": f"{agreement_count}/{total_methods} methods agree"
    }
