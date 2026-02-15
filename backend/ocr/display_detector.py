"""
Display region detector for odometer images.

This replaces the YOLO object detection step from the reference pipeline
(umutkavakli/odometer-mileage-extraction). Instead of a trained neural network,
we use classical computer vision to find the bright rectangular LCD display
region in a dashboard photo.

Strategy:
1. Find bright/high-contrast rectangular regions (LCD displays are backlit)
2. Score candidates by aspect ratio, size, and internal contrast
3. Apply perspective correction to straighten the detected region
4. Return the cropped, corrected display image

This is the critical missing step — without it, OCR runs on the full
dashboard photo and gets confused by surrounding text, textures, and glare.
"""

import cv2
import numpy as np


def detect_display_region(img):
    """Detect the odometer LCD display rectangle in a dashboard photo.

    Tries multiple detection strategies and returns the best candidate.

    Args:
        img: BGR OpenCV image

    Returns:
        Cropped display region (BGR), or None if no display found.
        Also returns the bounding box (x, y, w, h) for visualization.
    """
    results = []

    # Strategy 1: Edge-based rectangle detection
    result = _detect_by_edges(img)
    if result is not None:
        results.append(result)

    # Strategy 2: Brightness-based region detection
    result = _detect_by_brightness(img)
    if result is not None:
        results.append(result)

    # Strategy 3: Color saturation-based (LCD displays often have distinct color)
    result = _detect_by_saturation(img)
    if result is not None:
        results.append(result)

    if not results:
        return None, None

    # Pick the best candidate based on scoring
    best = max(results, key=lambda r: r["score"])
    return best["crop"], best["bbox"]


def _score_candidate(img, x, y, w, h):
    """Score a candidate display region.

    Higher score = more likely to be an odometer display.
    Considers aspect ratio, size relative to image, and internal contrast.
    """
    img_h, img_w = img.shape[:2]
    score = 0.0

    # Aspect ratio: odometer displays are wider than tall (typically 2:1 to 6:1)
    aspect = w / max(h, 1)
    if 1.5 <= aspect <= 8.0:
        score += 30
    elif 1.0 <= aspect <= 10.0:
        score += 15

    # Size: display should be a meaningful portion of the image but not all of it
    area_ratio = (w * h) / (img_w * img_h)
    if 0.02 <= area_ratio <= 0.5:
        score += 25
    elif 0.01 <= area_ratio <= 0.7:
        score += 10

    # Internal contrast: display region should have good contrast (digits vs background)
    roi = img[y:y + h, x:x + w]
    if roi.size > 0:
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        std = np.std(gray_roi)
        if std > 40:
            score += 25
        elif std > 20:
            score += 15

    # Minimum absolute size
    if w >= 50 and h >= 15:
        score += 10

    return score


def _detect_by_edges(img):
    """Detect display by finding rectangular contours via edge detection."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Canny edge detection
    edges = cv2.Canny(blurred, 50, 150)

    # Dilate to connect broken edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    img_h, img_w = img.shape[:2]
    best_candidate = None
    best_score = 0

    for cnt in contours:
        # Approximate the contour to a polygon
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        # Look for rectangles (4 vertices) or near-rectangles
        if len(approx) >= 4 and len(approx) <= 8:
            x, y, w, h = cv2.boundingRect(cnt)

            # Skip tiny regions
            if w < 30 or h < 10:
                continue

            score = _score_candidate(img, x, y, w, h)

            # Bonus for being close to a rectangle (4 vertices)
            if len(approx) == 4:
                score += 15

            if score > best_score:
                best_score = score
                crop = _extract_and_correct(img, cnt, x, y, w, h)
                best_candidate = {
                    "crop": crop,
                    "bbox": (x, y, w, h),
                    "score": score,
                    "method": "edges",
                }

    return best_candidate


def _detect_by_brightness(img):
    """Detect display by finding bright rectangular regions.

    LCD odometer displays are typically brighter than the surrounding dashboard.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Try multiple brightness thresholds
    best_candidate = None
    best_score = 0

    for thresh_val in [180, 150, 120, 100]:
        _, binary = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)

        # Close gaps and clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 30 or h < 10:
                continue

            score = _score_candidate(img, x, y, w, h)

            if score > best_score:
                best_score = score
                crop = img[y:y + h, x:x + w].copy()
                best_candidate = {
                    "crop": crop,
                    "bbox": (x, y, w, h),
                    "score": score,
                    "method": "brightness",
                }

    return best_candidate


def _detect_by_saturation(img):
    """Detect display by finding regions with distinct color (orange, green, white digits)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    _, s, v = cv2.split(hsv)

    # High value (bright) areas with either high or low saturation
    # LCD displays: bright and either colorful (orange/green) or desaturated (white/gray)
    bright_mask = v > 100

    # Also check for colored regions (orange, green LED displays)
    colored_mask = (s > 80) & bright_mask
    neutral_mask = (s < 40) & bright_mask

    best_candidate = None
    best_score = 0

    for mask in [colored_mask, neutral_mask]:
        mask_uint8 = mask.astype(np.uint8) * 255

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        mask_uint8 = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 30 or h < 10:
                continue

            score = _score_candidate(img, x, y, w, h)

            if score > best_score:
                best_score = score
                crop = img[y:y + h, x:x + w].copy()
                best_candidate = {
                    "crop": crop,
                    "bbox": (x, y, w, h),
                    "score": score,
                    "method": "saturation",
                }

    return best_candidate


def _extract_and_correct(img, contour, x, y, w, h):
    """Extract and optionally perspective-correct a display region.

    If the contour has 4 clear corners, apply perspective transform
    to produce a straight rectangular crop. Otherwise, just crop.
    """
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

    if len(approx) == 4:
        # Sort corners: top-left, top-right, bottom-right, bottom-left
        pts = approx.reshape(4, 2).astype(np.float32)
        rect = _order_points(pts)

        # Compute output dimensions
        width = max(
            np.linalg.norm(rect[0] - rect[1]),
            np.linalg.norm(rect[2] - rect[3])
        )
        height = max(
            np.linalg.norm(rect[0] - rect[3]),
            np.linalg.norm(rect[1] - rect[2])
        )

        if width > 30 and height > 10:
            dst = np.array([
                [0, 0],
                [width - 1, 0],
                [width - 1, height - 1],
                [0, height - 1],
            ], dtype=np.float32)

            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(img, M, (int(width), int(height)))
            return warped

    # Fallback: simple crop
    return img[y:y + h, x:x + w].copy()


def _order_points(pts):
    """Order 4 points as: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # Top-left has smallest sum
    rect[2] = pts[np.argmax(s)]  # Bottom-right has largest sum
    d = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(d)]  # Top-right has smallest difference
    rect[3] = pts[np.argmax(d)]  # Bottom-left has largest difference
    return rect
