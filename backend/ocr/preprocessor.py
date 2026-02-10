"""
Image preprocessing pipeline optimized for seven-segment LCD displays.

Key steps:
1. Resize for consistent processing
2. Convert to grayscale
3. CLAHE contrast enhancement - crucial for uneven lighting on LCD displays
4. Noise reduction via median blur - removes salt-and-pepper noise common in photos
5. Adaptive thresholding - handles varying brightness across the image
6. Morphological operations - cleans up digit segments
7. Deskewing - corrects slight rotation from handheld photos
"""

import cv2
import numpy as np
from skimage import filters
import base64
import io
from PIL import Image


def load_image_from_upload(file_storage):
    """Load an image from a Flask file upload."""
    file_bytes = np.frombuffer(file_storage.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    file_storage.seek(0)
    return img


def load_image_from_base64(b64_string):
    """Load image from base64 string."""
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_bytes = base64.b64decode(b64_string)
    nparr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def image_to_base64(img):
    """Convert OpenCV image to base64 PNG string."""
    _, buffer = cv2.imencode(".png", img)
    return "data:image/png;base64," + base64.b64encode(buffer).decode("utf-8")


def resize_for_processing(img, max_width=1200):
    """Resize image to a consistent width for processing.

    Larger images take longer to process but too small loses detail.
    1200px width is a good balance for seven-segment displays.
    """
    h, w = img.shape[:2]
    if w > max_width:
        scale = max_width / w
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img


def to_grayscale(img):
    """Convert to grayscale, using the max channel to preserve colored digits.

    Standard grayscale conversion can lose contrast for colored segments
    (e.g., orange digits on black). Using the max of BGR channels ensures
    any bright color channel produces a bright grayscale value.
    """
    if len(img.shape) == 3:
        # Use max channel to preserve bright colored digits (orange, green, etc.)
        max_channel = np.max(img, axis=2)
        standard_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Blend: use max channel if it has better contrast
        if np.std(max_channel) > np.std(standard_gray):
            return max_channel
        return standard_gray
    return img


def enhance_contrast_clahe(gray, clip_limit=3.0, tile_size=8):
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

    CLAHE is particularly effective for odometer images because:
    - LCD displays often have uneven backlighting
    - Different parts of the display may have different brightness
    - It enhances local contrast without amplifying noise globally
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    return clahe.apply(gray)


def reduce_noise(gray, kernel_size=3):
    """Apply median blur for noise reduction.

    Median blur is preferred over Gaussian for seven-segment displays because:
    - It preserves sharp edges (important for segment boundaries)
    - It effectively removes salt-and-pepper noise from camera sensors
    - It doesn't blur the digit segments themselves
    """
    return cv2.medianBlur(gray, kernel_size)


def adaptive_threshold(gray, block_size=35, c=10):
    """Apply adaptive thresholding.

    Adaptive thresholding is critical for odometer images because:
    - The background brightness varies across the display
    - Fixed thresholds fail when lighting is uneven
    - Each local region gets its own optimal threshold
    """
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c
    )


def otsu_threshold(gray):
    """Apply Otsu's binarization for automatic threshold selection."""
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def morphological_cleanup(binary, kernel_size=2):
    """Apply morphological operations to clean up the binary image.

    For seven-segment displays:
    - Close operation fills small gaps in digit segments
    - Open operation removes small noise dots
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    # Close small gaps in segments
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    # Remove small noise
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
    return cleaned


def deskew(img):
    """Correct slight rotation in the image.

    Handheld photos are rarely perfectly aligned. Even a few degrees
    of rotation can significantly impact OCR accuracy. This detects
    the dominant angle and corrects it.
    """
    gray = to_grayscale(img) if len(img.shape) == 3 else img
    coords = np.column_stack(np.where(gray > 0))
    if len(coords) < 50:
        return img
    try:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        # Only correct small angles (< 15 degrees)
        if abs(angle) > 15 or abs(angle) < 0.5:
            return img
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        return img


def invert_if_needed(binary):
    """Ensure digits are dark on light background (standard for OCR).

    Some odometers show light digits on dark background (e.g., orange on black).
    OCR engines typically expect dark text on light background, so we invert
    if the majority of pixels are dark (suggesting dark background).
    """
    white_ratio = np.sum(binary == 255) / binary.size
    if white_ratio < 0.4:
        return cv2.bitwise_not(binary)
    return binary


def sharpen(gray):
    """Apply unsharp masking to enhance digit edges."""
    blurred = cv2.GaussianBlur(gray, (0, 0), 3)
    return cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)


def preprocess_pipeline(img, params=None):
    """Run the full preprocessing pipeline and return intermediate steps.

    Args:
        img: OpenCV BGR image
        params: Optional dict to override default parameters

    Returns:
        dict with 'final' processed image and 'steps' list of intermediate results
    """
    if params is None:
        params = {}

    steps = []

    # Step 1: Resize
    resized = resize_for_processing(img, params.get("max_width", 1200))
    steps.append({"name": "Original (resized)", "image": resized.copy()})

    # Step 2: Grayscale
    gray = to_grayscale(resized)
    steps.append({"name": "Grayscale", "image": gray.copy()})

    # Step 3: CLAHE contrast enhancement
    enhanced = enhance_contrast_clahe(
        gray,
        clip_limit=params.get("clahe_clip", 3.0),
        tile_size=params.get("clahe_tile", 8)
    )
    steps.append({"name": "CLAHE Enhanced", "image": enhanced.copy()})

    # Step 4: Sharpen
    sharpened = sharpen(enhanced)
    steps.append({"name": "Sharpened", "image": sharpened.copy()})

    # Step 5: Noise reduction
    denoised = reduce_noise(sharpened, params.get("blur_kernel", 3))
    steps.append({"name": "Noise Reduced", "image": denoised.copy()})

    # Step 6: Adaptive threshold
    binary_adaptive = adaptive_threshold(
        denoised,
        block_size=params.get("threshold_block", 35),
        c=params.get("threshold_c", 10)
    )
    steps.append({"name": "Adaptive Threshold", "image": binary_adaptive.copy()})

    # Step 7: Otsu threshold (alternative)
    binary_otsu = otsu_threshold(denoised)
    steps.append({"name": "Otsu Threshold", "image": binary_otsu.copy()})

    # Step 8: Morphological cleanup
    cleaned = morphological_cleanup(binary_adaptive, params.get("morph_kernel", 2))
    steps.append({"name": "Morphological Cleanup", "image": cleaned.copy()})

    # Step 9: Invert if needed
    final = invert_if_needed(cleaned)
    steps.append({"name": "Final (inverted if needed)", "image": final.copy()})

    # Step 10: Deskew
    deskewed = deskew(final)
    steps.append({"name": "Deskewed", "image": deskewed.copy()})

    return {
        "final": deskewed,
        "gray": gray,
        "enhanced": enhanced,
        "binary_adaptive": binary_adaptive,
        "binary_otsu": binary_otsu,
        "steps": steps
    }


def get_preprocessing_variants(img, params=None):
    """Generate multiple preprocessed variants for multi-method OCR.

    Different OCR methods work better with different preprocessing.
    This generates several variants to give each method the best chance.
    """
    pipeline = preprocess_pipeline(img, params)

    variants = {
        "adaptive": pipeline["final"],
        "otsu": invert_if_needed(pipeline["binary_otsu"]),
        "enhanced_gray": pipeline["enhanced"],
        "gray": pipeline["gray"],
    }

    # Additional variant: high contrast
    gray = pipeline["gray"]
    high_contrast = enhance_contrast_clahe(gray, clip_limit=5.0, tile_size=4)
    _, high_binary = cv2.threshold(high_contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants["high_contrast"] = invert_if_needed(high_binary)

    return variants, pipeline["steps"]
