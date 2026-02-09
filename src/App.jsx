import { useState, useEffect } from 'react';
import CameraCapture from './components/CameraCapture';
import OdometerReader from './components/OdometerReader';
import MileageHistory from './components/MileageHistory';
import { getReadings, saveReading } from './utils/storage';
import './App.css';

const VIEWS = { CAPTURE: 'capture', READER: 'reader', HISTORY: 'history' };

export default function App() {
  const [view, setView] = useState(VIEWS.CAPTURE);
  const [capturedImage, setCapturedImage] = useState(null);
  const [readings, setReadings] = useState([]);

  useEffect(() => {
    setReadings(getReadings());
  }, []);

  const handleCapture = (imageDataUrl) => {
    setCapturedImage(imageDataUrl);
    setView(VIEWS.READER);
  };

  const handleResult = (result) => {
    const updated = saveReading(result);
    setReadings(updated);
    setCapturedImage(null);
    setView(VIEWS.HISTORY);
  };

  const handleRetake = () => {
    setCapturedImage(null);
    setView(VIEWS.CAPTURE);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v6l4 2" />
          </svg>
          Odometer Reader
        </h1>
      </header>

      <nav className="tab-bar">
        <button
          className={`tab ${view === VIEWS.CAPTURE || view === VIEWS.READER ? 'active' : ''}`}
          onClick={() => { setCapturedImage(null); setView(VIEWS.CAPTURE); }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
            <circle cx="12" cy="13" r="4" />
          </svg>
          Capture
        </button>
        <button
          className={`tab ${view === VIEWS.HISTORY ? 'active' : ''}`}
          onClick={() => setView(VIEWS.HISTORY)}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          History
          {readings.length > 0 && <span className="badge">{readings.length}</span>}
        </button>
      </nav>

      <main className="app-content">
        {view === VIEWS.CAPTURE && <CameraCapture onCapture={handleCapture} />}
        {view === VIEWS.READER && capturedImage && (
          <OdometerReader image={capturedImage} onResult={handleResult} onRetake={handleRetake} />
        )}
        {view === VIEWS.HISTORY && <MileageHistory readings={readings} onUpdate={setReadings} />}
      </main>
    </div>
  );
}
