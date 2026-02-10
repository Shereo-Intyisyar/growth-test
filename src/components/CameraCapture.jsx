import { useRef, useState, useCallback } from 'react';

export default function CameraCapture({ onCapture }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(null);
  const streamRef = useRef(null);

  const startCamera = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      videoRef.current.play();
      setStreaming(true);
    } catch {
      setError('Camera access denied. Please allow camera permissions or use file upload instead.');
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setStreaming(false);
  }, []);

  const capturePhoto = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/png');
    stopCamera();
    onCapture(dataUrl);
  }, [onCapture, stopCamera]);

  const handleFileUpload = useCallback(
    (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => onCapture(ev.target.result);
      reader.readAsDataURL(file);
    },
    [onCapture]
  );

  return (
    <div className="camera-capture">
      {streaming ? (
        <div className="camera-viewfinder">
          <video ref={videoRef} playsInline muted />
          <div className="viewfinder-overlay">
            <div className="viewfinder-guide">
              <span>Align odometer in this area</span>
            </div>
          </div>
          <div className="camera-controls">
            <button className="btn btn-secondary" onClick={stopCamera}>
              Cancel
            </button>
            <button className="btn btn-capture" onClick={capturePhoto}>
              <div className="capture-ring" />
            </button>
            <div style={{ width: 60 }} />
          </div>
        </div>
      ) : (
        <div className="capture-options">
          <button className="btn btn-primary" onClick={startCamera}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
            Open Camera
          </button>
          <label className="btn btn-secondary file-upload-btn">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Upload Photo
            <input type="file" accept="image/*" capture="environment" onChange={handleFileUpload} hidden />
          </label>
          {error && <p className="error-message">{error}</p>}
        </div>
      )}
      <canvas ref={canvasRef} hidden />
    </div>
  );
}
