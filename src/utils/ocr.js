import Tesseract from 'tesseract.js';

/**
 * Pre-process an image canvas for better OCR on odometer digits.
 * Converts to grayscale, increases contrast, and applies threshold.
 */
export function preprocessImage(canvas, ctx, img) {
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const data = imageData.data;

  for (let i = 0; i < data.length; i += 4) {
    // Grayscale
    const avg = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
    // High contrast threshold for digit recognition
    const val = avg > 128 ? 255 : 0;
    data[i] = val;
    data[i + 1] = val;
    data[i + 2] = val;
  }

  ctx.putImageData(imageData, 0, 0);
  return canvas.toDataURL('image/png');
}

/**
 * Run Tesseract OCR on an image source and extract numeric odometer reading.
 */
export async function recognizeOdometer(imageSource, onProgress) {
  const result = await Tesseract.recognize(imageSource, 'eng', {
    logger: (m) => {
      if (m.status === 'recognizing text' && onProgress) {
        onProgress(Math.round(m.progress * 100));
      }
    },
    tessedit_char_whitelist: '0123456789.',
    tessedit_pageseg_mode: '7', // treat as single line of text
  });

  const raw = result.data.text.trim();
  // Strip non-numeric characters except decimal point
  const cleaned = raw.replace(/[^0-9.]/g, '');
  const confidence = result.data.confidence;

  return {
    raw,
    cleaned,
    mileage: cleaned ? parseFloat(cleaned) : null,
    confidence,
  };
}
