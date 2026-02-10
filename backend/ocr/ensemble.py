"""
Ensemble voting system for combining results from multiple OCR methods.

When multiple methods agree on a reading, confidence is boosted.
When they disagree, the system picks the result with the highest
individual confidence and notes the disagreement.
"""

import time
from . import easyocr_method, tesseract_method, template_matching, contour_method
from .preprocessor import get_preprocessing_variants, image_to_base64


def run_all_methods(img, enabled_methods=None, params=None):
    """Run all enabled OCR methods and return individual results.

    Args:
        img: OpenCV BGR image
        enabled_methods: list of method names to run (default: all)
        params: preprocessing parameters

    Returns:
        dict with individual results and ensemble result
    """
    if enabled_methods is None:
        enabled_methods = ["easyocr", "tesseract", "template_matching", "contour"]

    # Get preprocessed variants
    variants, preprocessing_steps = get_preprocessing_variants(img, params)

    # Convert preprocessing steps to base64 for visualization
    steps_b64 = []
    for step in preprocessing_steps:
        steps_b64.append({
            "name": step["name"],
            "image": image_to_base64(step["image"])
        })

    methods = {
        "easyocr": easyocr_method,
        "tesseract": tesseract_method,
        "template_matching": template_matching,
        "contour": contour_method,
    }

    results = {}
    timings = {}

    for method_name in enabled_methods:
        if method_name not in methods:
            continue

        method = methods[method_name]
        start_time = time.time()

        try:
            result = method.recognize(variants)
            elapsed = round((time.time() - start_time) * 1000)  # ms
            timings[method_name] = elapsed

            if result:
                results[method_name] = result
            else:
                results[method_name] = {
                    "method": method_name,
                    "digits": None,
                    "reading": None,
                    "confidence": 0,
                    "is_valid": False,
                    "error": "Method returned no result"
                }
        except Exception as e:
            elapsed = round((time.time() - start_time) * 1000)
            timings[method_name] = elapsed
            results[method_name] = {
                "method": method_name,
                "digits": None,
                "reading": None,
                "confidence": 0,
                "is_valid": False,
                "error": str(e)
            }

    # Ensemble voting
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
