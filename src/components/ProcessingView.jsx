import { useState, useEffect, useRef } from 'react';
import { processOdometer } from '../utils/api';

export default function ProcessingView({ file, onResult, onBack }) {
  const [status, setStatus] = useState('starting');
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const didRun = useRef(false);

  useEffect(() => {
    if (didRun.current) return;
    didRun.current = true;

    let cancelled = false;

    async function run() {
      try {
        setStatus('preprocessing');
        setProgress(10);

        // Simulate progress while waiting for backend
        const progressInterval = setInterval(() => {
          setProgress((p) => Math.min(p + 5, 85));
        }, 500);

        setStatus('running_ocr');
        setProgress(30);

        const result = await processOdometer(file);

        clearInterval(progressInterval);

        if (cancelled) return;
        setProgress(100);
        setStatus('done');

        // Brief pause to show 100% before transitioning
        setTimeout(() => {
          if (!cancelled) onResult(result);
        }, 300);
      } catch (err) {
        if (cancelled) return;
        setError(err.message || 'Processing failed');
        setStatus('error');
      }
    }

    run();

    return () => { cancelled = true; };
  }, [file, onResult]);

  const statusMessages = {
    starting: 'Initializing...',
    preprocessing: 'Preprocessing image...',
    running_ocr: 'Running OCR methods...',
    done: 'Complete!',
    error: 'Error',
  };

  return (
    <div className="max-w-lg mx-auto text-center space-y-8 py-12">
      {status !== 'error' ? (
        <>
          {/* Spinner */}
          <div className="flex justify-center">
            <div className="w-16 h-16 border-4 border-gray-700 border-t-blue-500 rounded-full animate-spin" />
          </div>

          <div>
            <h2 className="text-xl font-semibold mb-2">Processing Odometer</h2>
            <p className="text-gray-400">{statusMessages[status]}</p>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          <p className="text-sm text-gray-500">
            Running EasyOCR, Tesseract, template matching, and contour analysis...
          </p>
        </>
      ) : (
        <>
          <div className="w-16 h-16 mx-auto rounded-full bg-red-900/30 flex items-center justify-center">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-red-400">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-2">Processing Failed</h2>
            <p className="text-red-400">{error}</p>
          </div>
          <div className="flex gap-3 justify-center">
            <button
              onClick={onBack}
              className="px-6 py-2.5 bg-gray-800 rounded-xl text-gray-300 hover:bg-gray-700"
            >
              Go Back
            </button>
            <button
              onClick={() => {
                didRun.current = false;
                setError(null);
                setStatus('starting');
                setProgress(0);
                // Force re-run
                setTimeout(() => {
                  didRun.current = false;
                  setStatus('starting');
                }, 0);
              }}
              className="px-6 py-2.5 bg-blue-600 rounded-xl text-white hover:bg-blue-500"
            >
              Retry
            </button>
          </div>
        </>
      )}
    </div>
  );
}
