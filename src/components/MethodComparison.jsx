export default function MethodComparison({ methods, timings }) {
  if (!methods) return null;

  const entries = Object.entries(methods);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
      <h3 className="text-sm font-medium text-gray-300 mb-4">Method Comparison</h3>

      <div className="space-y-3">
        {entries.map(([name, result]) => {
          const time = timings?.[name] || 0;
          const confidence = result.confidence || 0;
          let confColor = 'text-red-400';
          if (confidence >= 90) confColor = 'text-green-400';
          else if (confidence >= 70) confColor = 'text-yellow-400';

          return (
            <div
              key={name}
              className="bg-gray-800 rounded-lg p-3 flex items-center gap-4"
            >
              {/* Method name */}
              <div className="flex-shrink-0 w-32">
                <p className="text-sm font-medium capitalize">
                  {name.replace(/_/g, ' ')}
                </p>
                <p className="text-xs text-gray-500">{time}ms</p>
              </div>

              {/* Reading */}
              <div className="flex-1">
                {result.reading != null ? (
                  <span className="text-lg font-mono tabular-nums">
                    {Number(result.reading).toLocaleString()}
                  </span>
                ) : (
                  <span className="text-gray-600 text-sm">
                    {result.error || 'No result'}
                  </span>
                )}
              </div>

              {/* Confidence bar */}
              <div className="flex-shrink-0 w-28">
                <div className="flex justify-between text-xs mb-1">
                  <span className={confColor}>{confidence}%</span>
                  <span className="text-gray-600">
                    {result.is_valid ? 'Valid' : 'Invalid'}
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-1.5">
                  <div
                    className={`h-full rounded-full ${
                      confidence >= 90 ? 'bg-green-500' :
                      confidence >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${Math.min(100, confidence)}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Timing summary */}
      {timings && (
        <div className="mt-3 text-xs text-gray-500 text-right">
          Total: {Object.values(timings).reduce((a, b) => a + b, 0)}ms
        </div>
      )}
    </div>
  );
}
