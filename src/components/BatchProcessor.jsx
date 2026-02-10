import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { batchProcess } from '../utils/api';

export default function BatchProcessor() {
  const [files, setFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: useCallback((accepted) => setFiles((prev) => [...prev, ...accepted]), []),
    accept: { 'image/*': ['.png', '.jpg', '.jpeg', '.webp', '.bmp'] },
    multiple: true,
  });

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleProcess = async () => {
    if (files.length === 0) return;
    setProcessing(true);
    setError(null);
    setResults(null);

    try {
      const data = await batchProcess(files);
      setResults(data.results);
    } catch (err) {
      setError(err.message || 'Batch processing failed');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-lg font-semibold">Batch Processing</h2>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-blue-500 bg-blue-500/10' : 'border-gray-700 hover:border-gray-500'
        }`}
      >
        <input {...getInputProps()} />
        <p className="text-gray-400">Drop multiple odometer images here, or click to select</p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-400">{files.length} file(s) selected</p>
            <button
              onClick={() => setFiles([])}
              className="text-xs text-gray-500 hover:text-gray-300"
            >
              Clear all
            </button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {files.map((f, i) => (
              <div key={i} className="bg-gray-900 rounded-lg border border-gray-800 p-2 relative">
                <img
                  src={URL.createObjectURL(f)}
                  alt={f.name}
                  className="w-full h-20 object-cover rounded"
                />
                <p className="text-xs text-gray-500 mt-1 truncate">{f.name}</p>
                <button
                  onClick={() => removeFile(i)}
                  className="absolute top-1 right-1 w-5 h-5 bg-gray-800 rounded-full text-gray-400 text-xs hover:bg-red-900 hover:text-red-400"
                >
                  x
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={handleProcess}
            disabled={processing}
            className="w-full py-3 rounded-xl bg-blue-600 text-white font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {processing ? 'Processing...' : `Process ${files.length} Image(s)`}
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-300">Results</h3>
          {results.map((r, i) => (
            <div key={i} className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex items-center gap-4">
              <span className="text-xs text-gray-500 w-8">{i + 1}.</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-400 truncate">{r.filename}</p>
              </div>
              {r.error ? (
                <span className="text-sm text-red-400">{r.error}</span>
              ) : (
                <>
                  <span className="text-lg font-bold tabular-nums">
                    {r.ensemble?.reading != null
                      ? Number(r.ensemble.reading).toLocaleString()
                      : '---'}
                  </span>
                  <span className={`text-sm px-2 py-0.5 rounded-full ${
                    (r.ensemble?.confidence || 0) >= 90 ? 'bg-green-900/30 text-green-400' :
                    (r.ensemble?.confidence || 0) >= 70 ? 'bg-yellow-900/30 text-yellow-400' :
                    'bg-red-900/30 text-red-400'
                  }`}>
                    {r.ensemble?.confidence || 0}%
                  </span>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
