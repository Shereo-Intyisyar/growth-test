import { useState } from 'react';

export default function PreprocessingViewer({ steps }) {
  const [expanded, setExpanded] = useState(false);
  const [selectedStep, setSelectedStep] = useState(null);

  if (!steps || steps.length === 0) return null;

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between text-left"
      >
        <h3 className="text-sm font-medium text-gray-300">
          Preprocessing Pipeline ({steps.length} steps)
        </h3>
        <svg
          width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          className={`text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          {/* Step thumbnails */}
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 mb-4">
            {steps.map((step, i) => (
              <button
                key={i}
                onClick={() => setSelectedStep(i === selectedStep ? null : i)}
                className={`rounded-lg overflow-hidden border-2 transition-colors ${
                  i === selectedStep ? 'border-blue-500' : 'border-gray-700 hover:border-gray-500'
                }`}
              >
                <img
                  src={step.image}
                  alt={step.name}
                  className="w-full h-16 object-cover"
                />
                <p className="text-[10px] text-gray-400 p-1 truncate">{step.name}</p>
              </button>
            ))}
          </div>

          {/* Selected step detail */}
          {selectedStep !== null && steps[selectedStep] && (
            <div className="bg-gray-800 rounded-lg p-3">
              <p className="text-sm font-medium text-gray-300 mb-2">
                Step {selectedStep + 1}: {steps[selectedStep].name}
              </p>
              <img
                src={steps[selectedStep].image}
                alt={steps[selectedStep].name}
                className="max-w-full max-h-64 mx-auto rounded"
              />
            </div>
          )}

          {/* Side-by-side first and last */}
          {selectedStep === null && (
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-800 rounded-lg p-3">
                <p className="text-xs text-gray-400 mb-2">Original</p>
                <img src={steps[0].image} alt="Original" className="w-full rounded" />
              </div>
              <div className="bg-gray-800 rounded-lg p-3">
                <p className="text-xs text-gray-400 mb-2">Final</p>
                <img src={steps[steps.length - 1].image} alt="Final" className="w-full rounded" />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
