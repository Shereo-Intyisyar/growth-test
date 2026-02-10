#!/usr/bin/env python3
"""
Test script for the odometer OCR pipeline.

Generates synthetic seven-segment display images matching the 5 sample readings,
then runs all OCR methods and produces an accuracy report.

Expected readings:
  1. 294355
  2. 239526  (originally noted as 232526 but image shows 239526)
  3. 151312
  4. 170496
  5. 283462
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from ocr.template_matching import create_segment_template, SEGMENTS
from ocr.ensemble import run_all_methods


def create_odometer_image(reading, style="white_on_dark", width=400, height=80):
    """Generate a synthetic seven-segment odometer display image.

    Args:
        reading: string of digits to display
        style: visual style preset
        width: image width
        height: image height

    Returns:
        OpenCV BGR image
    """
    digit_w = width // (len(reading) + 1)
    digit_h = int(height * 0.75)
    padding = digit_w // 2

    # Create base image based on style
    if style == "white_on_dark":
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:] = (20, 20, 20)  # Near-black background
        seg_color = (220, 220, 220)  # White segments
    elif style == "orange_on_dark":
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:] = (10, 10, 10)
        seg_color = (0, 140, 255)  # Orange (BGR)
    elif style == "dark_on_light":
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:] = (200, 210, 200)  # Light gray-green background
        seg_color = (40, 40, 40)  # Dark segments
    elif style == "gray_lcd":
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:] = (180, 190, 180)
        seg_color = (60, 60, 60)
    else:
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:] = (30, 30, 30)
        seg_color = (200, 200, 200)

    # Draw each digit
    for i, char in enumerate(reading):
        if not char.isdigit():
            continue
        x_offset = padding + i * digit_w
        y_offset = (height - digit_h) // 2

        segments = SEGMENTS[char]
        thickness = max(3, digit_h // 12)
        dw = digit_w - 8
        dh = digit_h

        pad = 3
        mid_y = dh // 2

        # Draw segments
        def rect(x1, y1, x2, y2):
            cv2.rectangle(
                img,
                (x_offset + x1, y_offset + y1),
                (x_offset + x2, y_offset + y2),
                seg_color, -1
            )

        seg_len_h = dw - 2 * pad - thickness
        seg_len_v = dh // 2 - pad - thickness // 2

        # a: top horizontal
        if segments[0]:
            rect(pad + thickness // 2, pad,
                 pad + thickness // 2 + seg_len_h, pad + thickness)
        # b: top-right vertical
        if segments[1]:
            rect(dw - pad - thickness, pad + thickness // 2,
                 dw - pad, pad + thickness // 2 + seg_len_v)
        # c: bottom-right vertical
        if segments[2]:
            rect(dw - pad - thickness, mid_y + thickness // 2,
                 dw - pad, mid_y + thickness // 2 + seg_len_v)
        # d: bottom horizontal
        if segments[3]:
            rect(pad + thickness // 2, dh - pad - thickness,
                 pad + thickness // 2 + seg_len_h, dh - pad)
        # e: bottom-left vertical
        if segments[4]:
            rect(pad, mid_y + thickness // 2,
                 pad + thickness, mid_y + thickness // 2 + seg_len_v)
        # f: top-left vertical
        if segments[5]:
            rect(pad, pad + thickness // 2,
                 pad + thickness, pad + thickness // 2 + seg_len_v)
        # g: middle horizontal
        if segments[6]:
            rect(pad + thickness // 2, mid_y - thickness // 2,
                 pad + thickness // 2 + seg_len_h, mid_y + thickness // 2)

    # Add some noise to simulate real camera conditions
    noise = np.random.normal(0, 5, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return img


def run_tests():
    """Run OCR on test images and produce accuracy report."""
    test_cases = [
        {"reading": "294355", "style": "white_on_dark", "label": "Sample 1 (white on dark)"},
        {"reading": "239526", "style": "dark_on_light", "label": "Sample 2 (dark on light LCD)"},
        {"reading": "151312", "style": "orange_on_dark", "label": "Sample 3 (orange on dark)"},
        {"reading": "170496", "style": "gray_lcd", "label": "Sample 4 (gray LCD)"},
        {"reading": "283462", "style": "dark_on_light", "label": "Sample 5 (dark on light)"},
    ]

    # Create sample images directory
    sample_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_images")
    os.makedirs(sample_dir, exist_ok=True)

    print("=" * 70)
    print("ODOMETER OCR TEST SUITE")
    print("=" * 70)
    print()

    total_correct = 0
    total_tests = len(test_cases)
    method_scores = {}

    for tc in test_cases:
        print(f"Test: {tc['label']}")
        print(f"  Expected reading: {tc['reading']}")

        # Generate test image
        img = create_odometer_image(tc["reading"], tc["style"])
        img_path = os.path.join(sample_dir, f"test_{tc['reading']}.png")
        cv2.imwrite(img_path, img)
        print(f"  Image saved: {img_path}")

        # Run OCR
        start = time.time()
        # Only use methods that don't require external binaries
        enabled = ["template_matching", "contour"]
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            enabled.append("tesseract")
        except Exception:
            pass

        try:
            import easyocr
            enabled.append("easyocr")
        except ImportError:
            pass

        result = run_all_methods(img, enabled)
        elapsed = round((time.time() - start) * 1000)

        # Ensemble result
        ensemble = result["ensemble"]
        detected = str(ensemble.get("reading", ""))
        expected = tc["reading"]
        is_correct = detected == expected
        if is_correct:
            total_correct += 1

        print(f"  Detected: {detected} ({'CORRECT' if is_correct else 'WRONG'})")
        print(f"  Confidence: {ensemble.get('confidence', 0)}%")
        print(f"  Best method: {ensemble.get('method', 'none')}")
        print(f"  Agreement: {ensemble.get('agreement', 0)}/{ensemble.get('total_methods', 0)}")
        print(f"  Total time: {elapsed}ms")

        # Per-method results
        print(f"  Method results:")
        for method_name, method_result in result["methods"].items():
            m_reading = str(method_result.get("reading", ""))
            m_conf = method_result.get("confidence", 0)
            m_time = result["timings"].get(method_name, 0)
            m_correct = m_reading == expected

            if method_name not in method_scores:
                method_scores[method_name] = {"correct": 0, "total": 0, "times": []}
            method_scores[method_name]["total"] += 1
            if m_correct:
                method_scores[method_name]["correct"] += 1
            method_scores[method_name]["times"].append(m_time)

            status = "OK" if m_correct else "FAIL"
            print(f"    {method_name:20s}: {m_reading:>10s} ({m_conf:5.1f}%) [{m_time}ms] {status}")

        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Overall accuracy: {total_correct}/{total_tests} ({total_correct/total_tests*100:.0f}%)")
    print()
    print("Per-method accuracy:")
    for method, scores in sorted(method_scores.items()):
        acc = scores["correct"] / scores["total"] * 100 if scores["total"] > 0 else 0
        avg_time = sum(scores["times"]) / len(scores["times"]) if scores["times"] else 0
        print(f"  {method:20s}: {scores['correct']}/{scores['total']} ({acc:.0f}%)  avg {avg_time:.0f}ms")

    print()
    return total_correct == total_tests


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
