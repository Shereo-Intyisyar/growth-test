import { useState, useEffect, useCallback } from 'react';
import ImageUpload from './components/ImageUpload';
import ProcessingView from './components/ProcessingView';
import PreprocessingViewer from './components/PreprocessingViewer';
import HistoryPanel from './components/HistoryPanel';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import BatchProcessor from './components/BatchProcessor';
import MethodComparison from './components/MethodComparison';
import ImageAdjust from './components/ImageAdjust';
import { getHealth } from './utils/api';

const TABS = {
  UPLOAD: 'upload',
  ADJUST: 'adjust',
  PROCESSING: 'processing',
  RESULTS: 'results',
  HISTORY: 'history',
  BATCH: 'batch',
  ANALYTICS: 'analytics',
};

export default function App() {
  const [tab, setTab] = useState(TABS.UPLOAD);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [adjustedFile, setAdjustedFile] = useState(null);
  const [result, setResult] = useState(null);
  const [backendOk, setBackendOk] = useState(null);
  const [history, setHistory] = useState(() => {
    try {
      const stored = localStorage.getItem('odo_history');
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });

  useEffect(() => {
    getHealth()
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  const saveHistory = useCallback((entry) => {
    setHistory((prev) => {
      const next = [entry, ...prev].slice(0, 100);
      localStorage.setItem('odo_history', JSON.stringify(next));
      return next;
    });
  }, []);

  const handleFileDrop = useCallback((accepted) => {
    const f = accepted[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setAdjustedFile(null);
    setTab(TABS.ADJUST);
  }, []);

  const handleAdjusted = useCallback((blob) => {
    setAdjustedFile(blob);
  }, []);

  const handleProcess = useCallback(() => {
    setTab(TABS.PROCESSING);
  }, []);

  const handleResult = useCallback((res) => {
    setResult(res);
    saveHistory({
      id: res.id,
      timestamp: res.timestamp,
      reading: res.ensemble?.reading,
      confidence: res.ensemble?.confidence,
      method: res.ensemble?.method,
      agreement: res.ensemble?.agreement,
      totalTime: res.total_time_ms,
      preview: preview,
    });
    setTab(TABS.RESULTS);
  }, [saveHistory, preview]);

  const handleReset = useCallback(() => {
    setFile(null);
    setPreview(null);
    setAdjustedFile(null);
    setResult(null);
    setTab(TABS.UPLOAD);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === 'u') { e.preventDefault(); handleReset(); }
        if (e.key === 'h') { e.preventDefault(); setTab(TABS.HISTORY); }
        if (e.key === 'b') { e.preventDefault(); setTab(TABS.BATCH); }
        if (e.key === 'd') { e.preventDefault(); setTab(TABS.ANALYTICS); }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleReset]);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
            </div>
            <h1 className="text-lg font-semibold">Odometer Reader</h1>
            {backendOk === true && (
              <span className="text-xs bg-green-900/50 text-green-400 px-2 py-0.5 rounded-full">
                API Connected
              </span>
            )}
            {backendOk === false && (
              <span className="text-xs bg-red-900/50 text-red-400 px-2 py-0.5 rounded-full">
                API Offline
              </span>
            )}
          </div>
          <div className="text-xs text-gray-500 hidden sm:block">
            Ctrl+U Upload | Ctrl+H History | Ctrl+B Batch | Ctrl+D Dashboard
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-4 flex gap-1 overflow-x-auto">
          {[
            { key: TABS.UPLOAD, label: 'Upload' },
            { key: TABS.HISTORY, label: 'History', badge: history.length || null },
            { key: TABS.BATCH, label: 'Batch' },
            { key: TABS.ANALYTICS, label: 'Analytics' },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                tab === t.key || (t.key === TABS.UPLOAD && [TABS.ADJUST, TABS.PROCESSING, TABS.RESULTS].includes(tab))
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              {t.label}
              {t.badge ? (
                <span className="ml-1.5 bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded-full">
                  {t.badge}
                </span>
              ) : null}
            </button>
          ))}
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {tab === TABS.UPLOAD && (
          <ImageUpload onDrop={handleFileDrop} backendOk={backendOk} />
        )}

        {tab === TABS.ADJUST && file && (
          <ImageAdjust
            preview={preview}
            onAdjusted={handleAdjusted}
            onProcess={handleProcess}
            onBack={handleReset}
          />
        )}

        {tab === TABS.PROCESSING && file && (
          <ProcessingView
            file={adjustedFile || file}
            onResult={handleResult}
            onBack={() => setTab(TABS.ADJUST)}
          />
        )}

        {tab === TABS.RESULTS && result && (
          <div className="space-y-6">
            {/* Main result card */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">OCR Result</h2>
                <button
                  onClick={handleReset}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  Process Another
                </button>
              </div>

              <div className="flex items-baseline gap-4 mb-4">
                <span className="text-5xl font-bold tabular-nums tracking-wide">
                  {result.ensemble?.reading != null
                    ? Number(result.ensemble.reading).toLocaleString()
                    : '---'}
                </span>
                <span className="text-gray-400 text-lg">km/mi</span>
              </div>

              {/* Confidence badge */}
              <div className="flex flex-wrap gap-3 mb-4">
                <ConfidenceBadge value={result.ensemble?.confidence} />
                <span className="text-sm text-gray-400">
                  via {result.ensemble?.method || 'unknown'}
                </span>
                <span className="text-sm text-gray-400">
                  {result.ensemble?.agreement}/{result.ensemble?.total_methods} methods agree
                </span>
                <span className="text-sm text-gray-400">
                  {result.total_time_ms}ms total
                </span>
              </div>

              {/* Manual correction */}
              <ManualCorrection resultId={result.id} currentReading={result.ensemble?.reading} />
            </div>

            {/* Method comparison */}
            <MethodComparison methods={result.methods} timings={result.timings} />

            {/* Preprocessing steps */}
            <PreprocessingViewer steps={result.preprocessing_steps} />

            {/* Image preview */}
            {preview && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
                <h3 className="text-sm font-medium text-gray-400 mb-3">Original Image</h3>
                <img src={preview} alt="Uploaded" className="rounded-lg max-h-64 mx-auto" />
              </div>
            )}
          </div>
        )}

        {tab === TABS.HISTORY && (
          <HistoryPanel history={history} onClear={() => {
            setHistory([]);
            localStorage.removeItem('odo_history');
          }} />
        )}

        {tab === TABS.BATCH && <BatchProcessor />}
        {tab === TABS.ANALYTICS && <AnalyticsDashboard />}
      </main>
    </div>
  );
}

function ConfidenceBadge({ value }) {
  if (value == null) return null;
  let color = 'bg-red-900/50 text-red-400';
  if (value >= 90) color = 'bg-green-900/50 text-green-400';
  else if (value >= 70) color = 'bg-yellow-900/50 text-yellow-400';

  return (
    <span className={`text-sm px-2.5 py-1 rounded-full font-medium ${color}`}>
      {value}% confidence
    </span>
  );
}

function ManualCorrection({ resultId, currentReading }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(currentReading?.toString() || '');
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    try {
      const { correctResult } = await import('./utils/api');
      await correctResult(resultId, parseInt(value, 10));
      setSaved(true);
      setEditing(false);
    } catch {
      // ignore
    }
  };

  if (saved) {
    return <p className="text-sm text-green-400">Correction saved for training data.</p>;
  }

  if (!editing) {
    return (
      <button
        onClick={() => setEditing(true)}
        className="text-sm text-gray-500 hover:text-gray-300"
      >
        Incorrect reading? Click to correct
      </button>
    );
  }

  return (
    <div className="flex gap-2 items-center">
      <input
        type="number"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-lg font-mono w-40"
        autoFocus
      />
      <button
        onClick={handleSave}
        className="px-3 py-1.5 bg-blue-600 rounded-lg text-sm font-medium hover:bg-blue-500"
      >
        Save
      </button>
      <button
        onClick={() => setEditing(false)}
        className="px-3 py-1.5 bg-gray-800 rounded-lg text-sm hover:bg-gray-700"
      >
        Cancel
      </button>
    </div>
  );
}
