"""
Ensemble voting system for combining results from multiple OCR methods.

Uses a fast-first strategy: runs lightweight methods (template matching,
contour) first. If they produce a confident result, returns immediately
without invoking slow methods (EasyOCR, Tesseract). Slow methods are only
used as fallback when fast methods fail or disagree.

Typical fast-path: ~50ms vs 10-30s with EasyOCR.
"""

import time
from . import easyocr_method, tesseract_method, template_matching, contour_method
from .preprocessor import get_preprocessing_variants, image_to_base64

# Methods ordered from fastest to slowest
FAST_METHODS = ["template_matching", "contour"]
SLOW_METHODS = ["tesseract", "easyocr"]

# If fast methods produce a result at or above this confidence, skip slow methods
FAST_CONFIDENCE_THRESHOLD = 60


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
    """Run OCR methods using a fast-first strategy.

    1. Run fast methods (template matching + contour) first (~50ms).
    2. If at least one produces a valid, confident reading, return immediately.
    3. Only fall back to slow methods (Tesseract, EasyOCR) when fast methods
       fail or produce low-confidence results.

    To force all methods (for benchmarking/comparison), pass
    enabled_methods=["all"].
    """
    force_all = enabled_methods is not None and "all" in enabled_methods

    if enabled_methods is None or force_all:
        enabled_methods = FAST_METHODS + SLOW_METHODS

    all_methods = {
        "easyocr": easyocr_method,
        "tesseract": tesseract_method,
        "template_matching": template_matching,
        "contour": contour_method,
    }

    # Preprocessing (shared across all methods)
    variants, preprocessing_steps = get_preprocessing_variants(img, params)
    steps_b64 = [
        {"name": s["name"], "image": image_to_base64(s["image"])}
        for s in preprocessing_steps
    ]

    results = {}
    timings = {}

    # --- Phase 1: Run fast methods ---
    fast_to_run = [m for m in FAST_METHODS if m in enabled_methods and m in all_methods]
    for method_name in fast_to_run:
        result, elapsed = _run_method(all_methods[method_name], method_name, variants)
        results[method_name] = result
        timings[method_name] = elapsed

    # Early exit: if fast methods give a confident answer, skip slow ones
    if not force_all and fast_to_run:
        fast_vote = _vote(results)
        if (fast_vote.get("is_valid")
                and fast_vote.get("confidence", 0) >= FAST_CONFIDENCE_THRESHOLD):
            fast_vote["skipped_slow"] = True
            return {
                "methods": results,
                "ensemble": fast_vote,
                "timings": timings,
                "preprocessing_steps": steps_b64,
                "total_time": sum(timings.values()),
            }

    # --- Phase 2: Fall back to slow methods ---
    slow_to_run = [m for m in SLOW_METHODS if m in enabled_methods and m in all_methods]
    for method_name in slow_to_run:
        result, elapsed = _run_method(all_methods[method_name], method_name, variants)
        results[method_name] = result
        timings[method_name] = elapsed

    ensemble = _vote(results)

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
        # No valid results - return the best invalid one
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

    # Find the reading with most votes (tiebreak by confidence)
    best_reading = max(
        reading_votes.items(),
        key=lambda x: (x[1]["count"], x[1]["max_confidence"])
    )

    reading_value = best_reading[0]
    vote_info = best_reading[1]

    # Boost confidence based on agreement
    agreement_count = vote_info["count"]
    total_methods = len(valid_results)
    base_confidence = vote_info["max_confidence"]

    if agreement_count >= 3:
        boosted_confidence = min(99, base_confidence + 20)
    elif agreement_count >= 2:
        boosted_confidence = min(95, base_confidence + 10)
    else:
        boosted_confidence = base_confidence

    # Find which specific method gave the best result
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
