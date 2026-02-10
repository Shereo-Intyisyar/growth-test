"""
Contour-based digit extraction and classification.

Finds digit contours in the binary image, extracts each digit as a
separate image, and classifies using a simple pixel-based approach
combined with seven-segment pattern matching.
"""

import cv2
import numpy as np
from .postprocessor import postprocess_result


# Seven-segment region analysis
# Divide digit bounding box into 7 regions and check density
def analyze_segments(digit_img):
    """Analyze which seven-segment regions are active in a digit image.

    Divides the image into 7 zones corresponding to the 7 segments
    and checks the pixel density in each zone.

    Returns a 7-element list of booleans (segment on/off).
    """
    h, w = digit_img.shape[:2]
    if h < 6 or w < 4:
        return [0] * 7

    # Define regions for each segment
    seg_thickness_h = max(h // 8, 2)
    seg_thickness_w = max(w // 4, 2)

    third_h = h // 3
    mid_y = h // 2

    regions = {
        # Segment a: top horizontal
        "a": digit_img[0:seg_thickness_h, w // 4:3 * w // 4],
        # Segment b: top-right vertical
        "b": digit_img[seg_thickness_h:mid_y - seg_thickness_h // 2, w - seg_thickness_w:w],
        # Segment c: bottom-right vertical
        "c": digit_img[mid_y + seg_thickness_h // 2:h - seg_thickness_h, w - seg_thickness_w:w],
        # Segment d: bottom horizontal
        "d": digit_img[h - seg_thickness_h:h, w // 4:3 * w // 4],
        # Segment e: bottom-left vertical
        "e": digit_img[mid_y + seg_thickness_h // 2:h - seg_thickness_h, 0:seg_thickness_w],
        # Segment f: top-left vertical
        "f": digit_img[seg_thickness_h:mid_y - seg_thickness_h // 2, 0:seg_thickness_w],
        # Segment g: middle horizontal
        "g": digit_img[mid_y - seg_thickness_h // 2:mid_y + seg_thickness_h // 2, w // 4:3 * w // 4],
    }

    threshold = 0.3  # 30% of pixels need to be white for segment to be "on"
    segments = []
    for seg_name in ["a", "b", "c", "d", "e", "f", "g"]:
        region = regions[seg_name]
        if region.size == 0:
            segments.append(0)
            continue
        density = np.sum(region > 127) / region.size
        segments.append(1 if density > threshold else 0)

    return segments


# Mapping from segment pattern to digit
SEGMENT_TO_DIGIT = {
    (1, 1, 1, 1, 1, 1, 0): "0",
    (0, 1, 1, 0, 0, 0, 0): "1",
    (1, 1, 0, 1, 1, 0, 1): "2",
    (1, 1, 1, 1, 0, 0, 1): "3",
    (0, 1, 1, 0, 0, 1, 1): "4",
    (1, 0, 1, 1, 0, 1, 1): "5",
    (1, 0, 1, 1, 1, 1, 1): "6",
    (1, 1, 1, 0, 0, 0, 0): "7",
    (1, 1, 1, 1, 1, 1, 1): "8",
    (1, 1, 1, 1, 0, 1, 1): "9",
}


def classify_digit_by_segments(digit_img):
    """Classify a digit image by analyzing its seven-segment pattern.

    Returns (digit_string, confidence).
    """
    h, w = digit_img.shape[:2]
    # Special case: very narrow digits are almost certainly "1"
    # The digit "1" only uses right-side vertical segments, making it much narrower
    if h > 0 and w / h < 0.35:
        return "1", 90.0

    segments = analyze_segments(digit_img)
    pattern = tuple(segments)

    # Exact match
    if pattern in SEGMENT_TO_DIGIT:
        return SEGMENT_TO_DIGIT[pattern], 85.0

    # Find closest match (hamming distance)
    best_digit = "0"
    best_distance = 8
    for seg_pattern, digit in SEGMENT_TO_DIGIT.items():
        distance = sum(a != b for a, b in zip(pattern, seg_pattern))
        if distance < best_distance:
            best_distance = distance
            best_digit = digit

    # Confidence decreases with distance
    confidence = max(20, 85 - best_distance * 15)
    return best_digit, confidence


def find_and_extract_digits(binary_img):
    """Find digit contours and extract individual digit images.

    Returns list of (x_position, digit_image) tuples sorted left to right.
    """
    # Ensure binary
    if len(binary_img.shape) == 3:
        binary_img = cv2.cvtColor(binary_img, cv2.COLOR_BGR2GRAY)

    # Try to get white digits on black background
    if np.mean(binary_img) > 127:
        working = cv2.bitwise_not(binary_img)
    else:
        working = binary_img.copy()

    # Find contours
    contours, _ = cv2.findContours(working, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return []

    img_h, img_w = binary_img.shape[:2]
    min_h = img_h * 0.15
    max_h = img_h * 0.98

    digit_images = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = h / max(w, 1)

        if h >= min_h and h <= max_h and w >= 2 and 0.5 < aspect < 8.0:
            # Extract with small padding
            pad = 2
            y1 = max(0, y - pad)
            y2 = min(img_h, y + h + pad)
            x1 = max(0, x - pad)
            x2 = min(img_w, x + w + pad)

            digit_roi = working[y1:y2, x1:x2]

            # Resize to standard size for classification
            digit_resized = cv2.resize(digit_roi, (30, 50))

            digit_images.append((x, digit_resized))

    # Sort left to right
    digit_images.sort(key=lambda d: d[0])

    # Remove duplicates (overlapping detections)
    filtered = []
    prev_x = -100
    for x, img in digit_images:
        if x - prev_x > 5:  # Minimum spacing between digits
            filtered.append((x, img))
            prev_x = x

    return filtered


def recognize(variants):
    """Recognize odometer digits using contour-based extraction.

    Args:
        variants: dict of preprocessed image variants

    Returns:
        dict with OCR result
    """
    best_result = None
    best_confidence = -1

    for variant_name, img in variants.items():
        digit_images = find_and_extract_digits(img)

        if len(digit_images) < 4:
            continue

        digits = ""
        confidences = []

        for _, digit_img in digit_images:
            digit_char, conf = classify_digit_by_segments(digit_img)
            digits += digit_char
            confidences.append(conf)

        if not digits:
            continue

        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        result = postprocess_result(digits, avg_conf)
        result["variant"] = variant_name
        result["method"] = "contour"
        result["digit_count"] = len(digit_images)

        if result["is_valid"] and result["confidence"] > best_confidence:
            best_confidence = result["confidence"]
            best_result = result

    return best_result
