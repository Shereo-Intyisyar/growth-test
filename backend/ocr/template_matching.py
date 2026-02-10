"""
Template matching method for seven-segment digit recognition.

Creates synthetic templates for each digit (0-9) as they appear
on a seven-segment display, then matches them against digit regions
found in the image.

This is the most reliable method for clean seven-segment displays
because it directly models the expected digit shapes.
"""

import cv2
import numpy as np
from .postprocessor import postprocess_result


# Seven-segment display encoding
# Each digit is defined by which segments are ON
# Segments labeled: top, top-right, bottom-right, bottom, bottom-left, top-left, middle
#
#  _aaa_
# |     |
# f     b
# |     |
#  _ggg_
# |     |
# e     c
# |     |
#  _ddd_
#
SEGMENTS = {
    "0": [1, 1, 1, 1, 1, 1, 0],  # a,b,c,d,e,f on; g off
    "1": [0, 1, 1, 0, 0, 0, 0],
    "2": [1, 1, 0, 1, 1, 0, 1],
    "3": [1, 1, 1, 1, 0, 0, 1],
    "4": [0, 1, 1, 0, 0, 1, 1],
    "5": [1, 0, 1, 1, 0, 1, 1],
    "6": [1, 0, 1, 1, 1, 1, 1],
    "7": [1, 1, 1, 0, 0, 0, 0],
    "8": [1, 1, 1, 1, 1, 1, 1],
    "9": [1, 1, 1, 1, 0, 1, 1],
}


def create_segment_template(digit, width=40, height=70, thickness=6):
    """Create a synthetic seven-segment digit template.

    Draws the segments that are ON for the given digit on a black background
    with white segments, matching the typical appearance of LCD odometers.
    """
    img = np.zeros((height, width), dtype=np.uint8)
    segs = SEGMENTS[str(digit)]

    # Segment coordinates (adjusted for template size)
    pad = 4
    mid_y = height // 2
    seg_len_h = width - 2 * pad - thickness
    seg_len_v = height // 2 - pad - thickness // 2

    # Segment a (top horizontal)
    if segs[0]:
        cv2.rectangle(img, (pad + thickness // 2, pad),
                      (pad + thickness // 2 + seg_len_h, pad + thickness), 255, -1)

    # Segment b (top-right vertical)
    if segs[1]:
        cv2.rectangle(img, (width - pad - thickness, pad + thickness // 2),
                      (width - pad, pad + thickness // 2 + seg_len_v), 255, -1)

    # Segment c (bottom-right vertical)
    if segs[2]:
        cv2.rectangle(img, (width - pad - thickness, mid_y + thickness // 2),
                      (width - pad, mid_y + thickness // 2 + seg_len_v), 255, -1)

    # Segment d (bottom horizontal)
    if segs[3]:
        cv2.rectangle(img, (pad + thickness // 2, height - pad - thickness),
                      (pad + thickness // 2 + seg_len_h, height - pad), 255, -1)

    # Segment e (bottom-left vertical)
    if segs[4]:
        cv2.rectangle(img, (pad, mid_y + thickness // 2),
                      (pad + thickness, mid_y + thickness // 2 + seg_len_v), 255, -1)

    # Segment f (top-left vertical)
    if segs[5]:
        cv2.rectangle(img, (pad, pad + thickness // 2),
                      (pad + thickness, pad + thickness // 2 + seg_len_v), 255, -1)

    # Segment g (middle horizontal)
    if segs[6]:
        cv2.rectangle(img, (pad + thickness // 2, mid_y - thickness // 2),
                      (pad + thickness // 2 + seg_len_h, mid_y + thickness // 2), 255, -1)

    return img


def generate_templates(sizes=None):
    """Generate digit templates at multiple scales.

    Returns dict mapping digit -> list of template images at different sizes.
    """
    if sizes is None:
        sizes = [(30, 50), (40, 70), (50, 90), (60, 110)]

    templates = {}
    for digit in range(10):
        templates[str(digit)] = []
        for w, h in sizes:
            for thickness in [4, 6, 8]:
                tmpl = create_segment_template(digit, w, h, thickness)
                templates[str(digit)].append(tmpl)
    return templates


def find_digit_regions(binary_img):
    """Find regions in the image that likely contain individual digits.

    Uses contour detection to find connected components that have
    digit-like aspect ratios and sizes.
    """
    # Ensure white digits on black background for contour finding
    if np.mean(binary_img) > 127:
        working = cv2.bitwise_not(binary_img)
    else:
        working = binary_img.copy()

    contours, _ = cv2.findContours(working, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return []

    # Filter contours by size and aspect ratio
    img_h, img_w = binary_img.shape[:2]
    min_h = img_h * 0.2
    max_h = img_h * 0.95
    min_w = 2

    regions = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = h / max(w, 1)

        # Seven-segment digits: "1" is very narrow (aspect up to 8+)
        if h >= min_h and h <= max_h and w >= min_w and 0.8 < aspect < 10.0:
            regions.append((x, y, w, h))

    # Sort by x position (left to right)
    regions.sort(key=lambda r: r[0])

    # Remove overlapping regions
    filtered = []
    for region in regions:
        x, y, w, h = region
        overlap = False
        for fx, fy, fw, fh in filtered:
            if abs(x - fx) < min(w, fw) * 0.5:
                overlap = True
                break
        if not overlap:
            filtered.append(region)

    return filtered


def match_digit(digit_img, templates):
    """Match a single digit image against all digit templates.

    Returns the best matching digit and its confidence score.
    """
    h, w = digit_img.shape[:2]
    # Very narrow contours are almost certainly "1"
    if h > 0 and w / h < 0.3:
        return "1", 90.0

    best_digit = "0"
    best_score = -1

    for digit, tmpls in templates.items():
        for tmpl in tmpls:
            # Resize template to match digit region
            resized_tmpl = cv2.resize(tmpl, (digit_img.shape[1], digit_img.shape[0]))

            # Template matching
            result = cv2.matchTemplate(digit_img, resized_tmpl, cv2.TM_CCOEFF_NORMED)
            score = result[0][0] if result.size > 0 else 0

            if score > best_score:
                best_score = score
                best_digit = digit

    return best_digit, max(0, best_score * 100)


def recognize(variants):
    """Recognize odometer digits using template matching.

    Args:
        variants: dict of preprocessed image variants

    Returns:
        dict with OCR result
    """
    templates = generate_templates()

    best_result = None
    best_confidence = -1

    for variant_name, img in variants.items():
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Try both normal and inverted
        for inverted in [False, True]:
            working = cv2.bitwise_not(img) if inverted else img

            regions = find_digit_regions(working)

            if len(regions) < 4:  # Need at least 4 digits for an odometer
                continue

            digits = ""
            confidences = []

            for x, y, w, h in regions:
                digit_roi = working[y:y + h, x:x + w]

                # Ensure white digits on black for matching
                if np.mean(digit_roi) > 127:
                    digit_roi = cv2.bitwise_not(digit_roi)

                matched_digit, conf = match_digit(digit_roi, templates)
                digits += matched_digit
                confidences.append(conf)

            if not digits:
                continue

            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            result = postprocess_result(digits, avg_conf)
            result["variant"] = variant_name
            result["inverted"] = inverted
            result["method"] = "template_matching"
            result["digit_count"] = len(regions)

            if result["is_valid"] and result["confidence"] > best_confidence:
                best_confidence = result["confidence"]
                best_result = result

    return best_result
