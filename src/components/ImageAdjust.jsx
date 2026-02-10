import { useState, useRef, useEffect, useCallback } from 'react';

export default function ImageAdjust({ preview, onAdjusted, onProcess, onBack }) {
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [zoom, setZoom] = useState(1);
  const canvasRef = useRef(null);
  const imgRef = useRef(null);

  // Load image
  useEffect(() => {
    const img = new Image();
    img.onload = () => { imgRef.current = img; };
    img.src = preview;
  }, [preview]);

  // Render adjusted image to canvas
  const renderCanvas = useCallback(() => {
    const img = imgRef.current;
    const canvas = canvasRef.current;
    if (!img || !canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = img.width;
    canvas.height = img.height;

    ctx.save();
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate((rotation * Math.PI) / 180);
    ctx.scale(zoom, zoom);
    ctx.filter = `brightness(${brightness}%) contrast(${contrast}%)`;
    ctx.drawImage(img, -img.width / 2, -img.height / 2);
    ctx.restore();
  }, [brightness, contrast, rotation, zoom]);

  useEffect(() => {
    renderCanvas();
  }, [renderCanvas]);

  const handleProcess = () => {
    const canvas = canvasRef.current;
    if (!canvas) { onProcess(); return; }

    // If no adjustments made, use original file
    if (brightness === 100 && contrast === 100 && rotation === 0 && zoom === 1) {
      onProcess();
      return;
    }

    canvas.toBlob((blob) => {
      if (blob) onAdjusted(blob);
      onProcess();
    }, 'image/png');
  };

  const resetAdjustments = () => {
    setBrightness(100);
    setContrast(100);
    setRotation(0);
    setZoom(1);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Adjust Image</h2>
        <button onClick={onBack} className="text-sm text-gray-400 hover:text-gray-200">
          Back
        </button>
      </div>

      {/* Preview */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 overflow-hidden">
        <canvas
          ref={canvasRef}
          className="max-w-full max-h-80 mx-auto rounded-lg"
          style={{ imageRendering: 'auto' }}
        />
      </div>

      {/* Controls */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-sm font-medium text-gray-300">Adjustments</h3>
          <button
            onClick={resetAdjustments}
            className="text-xs text-gray-500 hover:text-gray-300"
          >
            Reset
          </button>
        </div>

        <Slider label="Brightness" value={brightness} onChange={setBrightness} min={20} max={200} unit="%" />
        <Slider label="Contrast" value={contrast} onChange={setContrast} min={20} max={200} unit="%" />
        <Slider label="Rotation" value={rotation} onChange={setRotation} min={-45} max={45} unit="deg" />
        <Slider label="Zoom" value={zoom * 100} onChange={(v) => setZoom(v / 100)} min={50} max={200} unit="%" />
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="flex-1 py-3 rounded-xl bg-gray-800 text-gray-300 font-medium hover:bg-gray-700 transition-colors"
        >
          Choose Different Image
        </button>
        <button
          onClick={handleProcess}
          className="flex-1 py-3 rounded-xl bg-blue-600 text-white font-medium hover:bg-blue-500 transition-colors"
        >
          Process Image
        </button>
      </div>
    </div>
  );
}

function Slider({ label, value, onChange, min, max, unit }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="text-gray-500 tabular-nums">{Math.round(value)}{unit}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-blue-500 h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer"
      />
    </div>
  );
}
