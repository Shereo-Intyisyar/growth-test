import { useState, useRef, useCallback } from 'react';
import { recognizeOdometer, preprocessImage } from '../utils/ocr';

export default function OdometerReader({ image, onResult, onRetake }) {
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [editedMileage, setEditedMileage] = useState('');
  const [useCrop, setUseCrop] = useState(false);

  // Crop state
  const [cropArea, setCropArea] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState(null);
  const imgContainerRef = useRef(null);

  const getRelativePos = (e) => {
    const rect = imgContainerRef.current.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: Math.max(0, Math.min(1, (clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (clientY - rect.top) / rect.height)),
    };
  };

  const handlePointerDown = (e) => {
    if (!useCrop) return;
    const pos = getRelativePos(e);
    setDragStart(pos);
    setDragging(true);
    setCropArea(null);
  };

  const handlePointerMove = (e) => {
    if (!dragging || !dragStart) return;
    const pos = getRelativePos(e);
    setCropArea({
      x: Math.min(dragStart.x, pos.x),
      y: Math.min(dragStart.y, pos.y),
      w: Math.abs(pos.x - dragStart.x),
      h: Math.abs(pos.y - dragStart.y),
    });
  };

  const handlePointerUp = () => {
    setDragging(false);
  };

  const getCroppedImage = useCallback(() => {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        if (cropArea && cropArea.w > 0.01 && cropArea.h > 0.01) {
          const canvas = document.createElement('canvas');
          const sx = cropArea.x * img.width;
          const sy = cropArea.y * img.height;
          const sw = cropArea.w * img.width;
          const sh = cropArea.h * img.height;
          canvas.width = sw;
          canvas.height = sh;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
          resolve(canvas.toDataURL('image/png'));
        } else {
          resolve(image);
        }
      };
      img.src = image;
    });
  }, [image, cropArea]);

  const processImage = useCallback(async () => {
    setProcessing(true);
    setProgress(0);
    setResult(null);
    try {
      let src = image;
      if (useCrop && cropArea) {
        src = await getCroppedImage();
      }

      // Pre-process for better OCR
      const img = new Image();
      img.src = src;
      await new Promise((resolve) => { img.onload = resolve; });
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      const processedSrc = preprocessImage(canvas, ctx, img);

      const ocrResult = await recognizeOdometer(processedSrc, setProgress);
      setResult(ocrResult);
      setEditedMileage(ocrResult.cleaned || '');
    } catch {
      setResult({ error: 'Failed to process image. Try again or use a clearer photo.' });
    }
    setProcessing(false);
  }, [image, useCrop, cropArea, getCroppedImage]);

  const handleConfirm = () => {
    const mileage = parseFloat(editedMileage);
    if (!isNaN(mileage) && mileage > 0) {
      onResult({ mileage, confidence: result?.confidence || 0, image });
    }
  };

  return (
    <div className="odometer-reader">
      <div
        className="image-preview"
        ref={imgContainerRef}
        onMouseDown={handlePointerDown}
        onMouseMove={handlePointerMove}
        onMouseUp={handlePointerUp}
        onTouchStart={handlePointerDown}
        onTouchMove={handlePointerMove}
        onTouchEnd={handlePointerUp}
      >
        <img src={image} alt="Captured dashboard" draggable={false} />
        {useCrop && cropArea && (
          <div
            className="crop-overlay"
            style={{
              left: `${cropArea.x * 100}%`,
              top: `${cropArea.y * 100}%`,
              width: `${cropArea.w * 100}%`,
              height: `${cropArea.h * 100}%`,
            }}
          />
        )}
      </div>

      <div className="reader-controls">
        <label className="crop-toggle">
          <input type="checkbox" checked={useCrop} onChange={(e) => setUseCrop(e.target.checked)} />
          Crop to odometer area {useCrop && '(drag on image)'}
        </label>

        {!processing && !result && (
          <div className="action-buttons">
            <button className="btn btn-secondary" onClick={onRetake}>
              Retake
            </button>
            <button className="btn btn-primary" onClick={processImage}>
              Read Odometer
            </button>
          </div>
        )}

        {processing && (
          <div className="progress-section">
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <p className="progress-text">Reading odometer... {progress}%</p>
          </div>
        )}

        {result && !result.error && (
          <div className="result-section">
            <div className="result-card">
              <label className="result-label">Detected Mileage</label>
              <div className="result-input-row">
                <input
                  type="number"
                  className="mileage-input"
                  value={editedMileage}
                  onChange={(e) => setEditedMileage(e.target.value)}
                  step="0.1"
                  min="0"
                />
                <span className="unit">mi</span>
              </div>
              {result.confidence < 60 && (
                <p className="low-confidence">Low confidence ({result.confidence}%) — please verify the reading</p>
              )}
              <p className="raw-text">Raw OCR: "{result.raw}"</p>
            </div>
            <div className="action-buttons">
              <button className="btn btn-secondary" onClick={onRetake}>
                Retake
              </button>
              <button
                className="btn btn-primary"
                onClick={handleConfirm}
                disabled={!editedMileage || parseFloat(editedMileage) <= 0}
              >
                Save Reading
              </button>
            </div>
          </div>
        )}

        {result?.error && (
          <div className="error-section">
            <p className="error-message">{result.error}</p>
            <div className="action-buttons">
              <button className="btn btn-secondary" onClick={onRetake}>
                Retake
              </button>
              <button className="btn btn-primary" onClick={processImage}>
                Try Again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
