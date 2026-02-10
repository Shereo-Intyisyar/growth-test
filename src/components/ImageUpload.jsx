import { useDropzone } from 'react-dropzone';

export default function ImageUpload({ onDrop, backendOk }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.png', '.jpg', '.jpeg', '.webp', '.bmp'] },
    maxFiles: 1,
    multiple: false,
  });

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold mb-2">Odometer Recognition</h2>
        <p className="text-gray-400">
          Upload a photo of your odometer to extract the reading using multi-method OCR
        </p>
      </div>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all ${
          isDragActive
            ? 'border-blue-500 bg-blue-500/10'
            : 'border-gray-700 hover:border-gray-500 hover:bg-gray-900/50'
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gray-800 flex items-center justify-center">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-gray-400">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          {isDragActive ? (
            <p className="text-blue-400 text-lg">Drop image here...</p>
          ) : (
            <>
              <p className="text-gray-300 text-lg">
                Drag & drop an odometer image here
              </p>
              <p className="text-gray-500 text-sm">
                or click to browse (PNG, JPG, WebP, BMP)
              </p>
            </>
          )}
        </div>
      </div>

      {backendOk === false && (
        <div className="mt-6 bg-red-900/20 border border-red-800 rounded-xl p-4 text-sm">
          <p className="text-red-400 font-medium mb-1">Backend API is not running</p>
          <p className="text-red-400/70">
            Start the Flask server with: <code className="bg-red-900/30 px-1.5 py-0.5 rounded">cd backend && python3 app.py</code>
          </p>
        </div>
      )}

      {/* Feature highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
        {[
          { title: 'Multi-Method OCR', desc: 'EasyOCR, Tesseract, template matching, and contour analysis' },
          { title: 'Smart Preprocessing', desc: 'CLAHE, adaptive thresholding, noise reduction, deskewing' },
          { title: 'Ensemble Voting', desc: 'Multiple methods vote on the final reading for higher accuracy' },
        ].map((f) => (
          <div key={f.title} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <h3 className="text-sm font-medium text-gray-200 mb-1">{f.title}</h3>
            <p className="text-xs text-gray-500">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
