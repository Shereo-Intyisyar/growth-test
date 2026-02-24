"""
Flask API server for odometer recognition.

Provides endpoints for single and batch image processing,
preprocessing visualization, and statistics tracking.
"""

import os
import time
import uuid
import json
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import cv2
import numpy as np

from ocr.preprocessor import load_image_from_upload, load_image_from_base64, image_to_base64
from ocr.ensemble import run_all_methods

app = Flask(__name__)
CORS(app)

# In-memory storage for processing results and stats
processing_results = {}
stats = {
    "total_processed": 0,
    "method_successes": {},
    "method_times": {},
    "confidence_sum": 0,
}

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    from ocr import easyocr_method, tesseract_method, pipeline_method, google_vision_method
    return jsonify({
        "status": "ok",
        "methods": {
            "google_vision": google_vision_method.is_available(),
            "pipeline": pipeline_method.is_available(),
            "easyocr": easyocr_method.is_available(),
            "tesseract": tesseract_method.is_available(),
            "template_matching": True,
            "contour": True,
        }
    })


@app.route("/api/process-odometer", methods=["POST"])
def process_odometer():
    """Process a single odometer image.

    Accepts either:
    - multipart/form-data with 'image' file
    - JSON with 'image' as base64 string

    Optional parameters:
    - methods: comma-separated list of methods to use
    - params: JSON preprocessing parameters
    """
    start_time = time.time()

    try:
        # Load image from request
        img = None
        if "image" in request.files:
            img = load_image_from_upload(request.files["image"])
        elif request.is_json and "image" in request.json:
            img = load_image_from_base64(request.json["image"])

        if img is None:
            return jsonify({"error": "No image provided"}), 400

        # Parse options
        enabled_methods = None
        if request.form.get("methods"):
            enabled_methods = request.form["methods"].split(",")
        elif request.is_json and request.json.get("methods"):
            enabled_methods = request.json["methods"]

        params = None
        if request.form.get("params"):
            params = json.loads(request.form["params"])
        elif request.is_json and request.json.get("params"):
            params = request.json["params"]

        # Run OCR pipeline
        result = run_all_methods(img, enabled_methods, params)

        # Generate result ID for later reference
        result_id = str(uuid.uuid4())[:8]
        total_time = round((time.time() - start_time) * 1000)

        # Store result
        result_data = {
            "id": result_id,
            "timestamp": datetime.now().isoformat(),
            "ensemble": result["ensemble"],
            "methods": result["methods"],
            "timings": result["timings"],
            "preprocessing_steps": result["preprocessing_steps"],
            "total_time_ms": total_time,
        }
        processing_results[result_id] = result_data

        # Update stats
        _update_stats(result)

        return jsonify(result_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/batch-process", methods=["POST"])
def batch_process():
    """Process multiple odometer images.

    Accepts multipart/form-data with multiple 'images' files.
    """
    if "images" not in request.files:
        return jsonify({"error": "No images provided"}), 400

    files = request.files.getlist("images")
    results = []

    for f in files:
        try:
            img = load_image_from_upload(f)
            if img is None:
                results.append({"filename": f.filename, "error": "Could not read image"})
                continue

            result = run_all_methods(img)
            result_id = str(uuid.uuid4())[:8]

            result_data = {
                "id": result_id,
                "filename": f.filename,
                "ensemble": result["ensemble"],
                "methods": result["methods"],
                "timings": result["timings"],
                "total_time_ms": result["total_time"],
            }
            processing_results[result_id] = result_data
            _update_stats(result)
            results.append(result_data)

        except Exception as e:
            results.append({"filename": f.filename, "error": str(e)})

    return jsonify({"results": results, "count": len(results)})


@app.route("/api/preprocessing-steps/<result_id>", methods=["GET"])
def get_preprocessing_steps(result_id):
    """Get preprocessing visualization steps for a processed image."""
    if result_id not in processing_results:
        return jsonify({"error": "Result not found"}), 404

    result = processing_results[result_id]
    return jsonify({
        "id": result_id,
        "steps": result.get("preprocessing_steps", [])
    })


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get processing statistics."""
    total = stats["total_processed"]
    avg_confidence = (
        round(stats["confidence_sum"] / total, 1) if total > 0 else 0
    )

    method_stats = {}
    for method, count in stats["method_successes"].items():
        times = stats["method_times"].get(method, [])
        avg_time = round(sum(times) / len(times)) if times else 0
        method_stats[method] = {
            "success_count": count,
            "average_time_ms": avg_time,
            "success_rate": round(count / total * 100, 1) if total > 0 else 0,
        }

    return jsonify({
        "total_processed": total,
        "average_confidence": avg_confidence,
        "methods": method_stats,
    })


@app.route("/api/results", methods=["GET"])
def get_results():
    """Get all processing results (history)."""
    results = sorted(
        processing_results.values(),
        key=lambda r: r.get("timestamp", ""),
        reverse=True
    )
    # Return without preprocessing steps to reduce payload
    slim_results = []
    for r in results:
        slim = {k: v for k, v in r.items() if k != "preprocessing_steps"}
        slim_results.append(slim)
    return jsonify({"results": slim_results})


@app.route("/api/correct/<result_id>", methods=["POST"])
def correct_result(result_id):
    """Submit a manual correction for an OCR result.

    Used for training mode - saves the correct value alongside
    the image for potential future model improvement.
    """
    if result_id not in processing_results:
        return jsonify({"error": "Result not found"}), 404

    data = request.json
    correct_reading = data.get("reading")
    if correct_reading is None:
        return jsonify({"error": "No reading provided"}), 400

    processing_results[result_id]["correction"] = {
        "reading": correct_reading,
        "timestamp": datetime.now().isoformat(),
    }

    return jsonify({"status": "ok", "id": result_id})


@app.route("/api/export-csv", methods=["GET"])
def export_csv():
    """Export all results as CSV."""
    import io
    output = io.StringIO()
    output.write("ID,Timestamp,Reading,Confidence,Method,Agreement,Total Time (ms)\n")

    for r in processing_results.values():
        ensemble = r.get("ensemble", {})
        output.write(
            f'{r.get("id", "")},'
            f'{r.get("timestamp", "")},'
            f'{ensemble.get("reading", "")},'
            f'{ensemble.get("confidence", "")},'
            f'{ensemble.get("method", "")},'
            f'{ensemble.get("agreement", "")},'
            f'{r.get("total_time_ms", "")}\n'
        )

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=odometer_results.csv"}
    )


def _update_stats(result):
    """Update global statistics with a new result."""
    stats["total_processed"] += 1

    ensemble = result.get("ensemble", {})
    if ensemble.get("is_valid"):
        stats["confidence_sum"] += ensemble.get("confidence", 0)

    for method_name, method_result in result.get("methods", {}).items():
        if method_result.get("is_valid"):
            stats["method_successes"][method_name] = (
                stats["method_successes"].get(method_name, 0) + 1
            )

    for method_name, time_ms in result.get("timings", {}).items():
        if method_name not in stats["method_times"]:
            stats["method_times"][method_name] = []
        stats["method_times"][method_name].append(time_ms)


if __name__ == "__main__":
    print("Starting Odometer Recognition API server...")
    print("Available endpoints:")
    print("  POST /api/process-odometer  - Process single image")
    print("  POST /api/batch-process     - Process multiple images")
    print("  GET  /api/preprocessing-steps/:id - View preprocessing steps")
    print("  GET  /api/stats             - View processing statistics")
    print("  GET  /api/results           - View all results")
    print("  GET  /api/export-csv        - Export results as CSV")
    print("  GET  /api/health            - Health check")
    app.run(host="0.0.0.0", port=5000, debug=True)
