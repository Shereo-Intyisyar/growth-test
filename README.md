# Odometer Reader - Multi-Method OCR Application

A React + Python Flask application that recognizes odometer readings from images of seven-segment LCD displays using multiple OCR approaches with ensemble voting.

## Architecture

```
├── backend/                  # Python Flask API server
│   ├── app.py                # Flask application with REST endpoints
│   ├── requirements.txt      # Python dependencies
│   ├── test_ocr.py           # Test script with synthetic images
│   ├── ocr/
│   │   ├── preprocessor.py   # Image preprocessing pipeline (CLAHE, thresholding, etc.)
│   │   ├── easyocr_method.py # EasyOCR-based recognition
│   │   ├── tesseract_method.py # Tesseract with digit-only config
│   │   ├── template_matching.py # Seven-segment template matching
│   │   ├── contour_method.py # Contour-based digit extraction
│   │   ├── ensemble.py       # Ensemble voting system
│   │   └── postprocessor.py  # Post-processing and validation
│   └── sample_images/        # Generated test images
├── src/                      # React frontend (Vite + Tailwind CSS)
│   ├── App.jsx               # Main application with tab navigation
│   ├── components/
│   │   ├── ImageUpload.jsx   # Drag-and-drop image upload
│   │   ├── ImageAdjust.jsx   # Brightness/contrast/rotation controls
│   │   ├── ProcessingView.jsx # Real-time processing status
│   │   ├── PreprocessingViewer.jsx # Visual preprocessing pipeline
│   │   ├── MethodComparison.jsx # Side-by-side OCR method results
│   │   ├── HistoryPanel.jsx  # Reading history with CSV export
│   │   ├── BatchProcessor.jsx # Multi-image batch processing
│   │   └── AnalyticsDashboard.jsx # Performance statistics
│   └── utils/
│       ├── api.js            # Backend API client
│       └── storage.js        # Local storage utilities
└── vite.config.js            # Vite config with Tailwind + API proxy
```

## Quick Start

### 1. Install dependencies

```bash
# Frontend
npm install

# Backend
pip3 install -r backend/requirements.txt
```

### 2. Start the backend

```bash
cd backend
python3 app.py
```

The API server starts on `http://localhost:5000`.

### 3. Start the frontend

```bash
npm run dev
```

The frontend starts on `http://localhost:5173` with API proxy to the backend.

### 4. Run tests

```bash
cd backend
python3 test_ocr.py
```

## OCR Methods

The application runs multiple OCR methods in parallel and uses ensemble voting to pick the best result:

### Method 1: EasyOCR
Deep learning-based OCR optimized for English digits. Works well with varied lighting and display styles. Requires the `easyocr` package (downloads models on first run).

### Method 2: Tesseract
Classic OCR engine with digit-only whitelist (`--psm 7 -c tessedit_char_whitelist=0123456789`). Tries multiple Page Segmentation Modes. Requires the `tesseract-ocr` system package.

### Method 3: Template Matching
Creates synthetic seven-segment digit templates and matches them against detected digit regions. Most reliable for clean seven-segment displays since it directly models the expected shapes. No external dependencies.

### Method 4: Contour-Based Extraction
Finds digit contours, extracts each digit individually, and classifies by analyzing which of the 7 segments are active. Uses pixel density analysis in each segment zone. No external dependencies.

## Preprocessing Pipeline

Each image goes through these steps (viewable in the UI):

1. **Resize** - Normalize to consistent width (1200px)
2. **Grayscale** - Convert to single channel
3. **CLAHE** - Contrast Limited Adaptive Histogram Equalization for uneven lighting
4. **Sharpen** - Unsharp masking to enhance segment edges
5. **Noise Reduction** - Median blur (preserves edges better than Gaussian)
6. **Adaptive Threshold** - Local thresholding for varying brightness
7. **Otsu Threshold** - Automatic global threshold (alternative)
8. **Morphological Cleanup** - Close gaps in segments, remove noise dots
9. **Invert if needed** - Ensure dark-on-light for OCR engines
10. **Deskew** - Correct slight rotation

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/process-odometer` | POST | Process single image (file upload or base64) |
| `/api/batch-process` | POST | Process multiple images |
| `/api/preprocessing-steps/:id` | GET | Get preprocessing step images |
| `/api/stats` | GET | Processing statistics |
| `/api/results` | GET | All processing results |
| `/api/correct/:id` | POST | Submit manual correction |
| `/api/export-csv` | GET | Export results as CSV |
| `/api/health` | GET | Health check with available methods |

## Configuration

### Preprocessing Parameters

Pass via `params` in the API request:

```json
{
  "max_width": 1200,
  "clahe_clip": 3.0,
  "clahe_tile": 8,
  "blur_kernel": 3,
  "threshold_block": 35,
  "threshold_c": 10,
  "morph_kernel": 2
}
```

### Method Selection

Toggle methods via the `methods` parameter:

```json
["easyocr", "tesseract", "template_matching", "contour"]
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+U | Upload new image |
| Ctrl+H | View history |
| Ctrl+B | Batch processing |
| Ctrl+D | Analytics dashboard |

## Tech Stack

- **Frontend**: React 19, Vite 7, Tailwind CSS 4, React Dropzone
- **Backend**: Python Flask, OpenCV, EasyOCR, pytesseract, scikit-image
- **Image Processing**: OpenCV for all preprocessing operations
