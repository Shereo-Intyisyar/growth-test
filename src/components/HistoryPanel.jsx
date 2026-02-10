import { getExportCsvUrl } from '../utils/api';

export default function HistoryPanel({ history, onClear }) {
  if (history.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-800 flex items-center justify-center">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-gray-600">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        </div>
        <p className="text-gray-400">No readings yet</p>
        <p className="text-sm text-gray-600 mt-1">Upload an odometer image to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          Reading History
          <span className="ml-2 text-sm text-gray-500 font-normal">{history.length} readings</span>
        </h2>
        <div className="flex gap-2">
          <a
            href={getExportCsvUrl()}
            className="px-3 py-1.5 text-xs bg-gray-800 rounded-lg text-gray-300 hover:bg-gray-700"
            download
          >
            Export CSV
          </a>
          <button
            onClick={onClear}
            className="px-3 py-1.5 text-xs bg-red-900/30 rounded-lg text-red-400 hover:bg-red-900/50"
          >
            Clear All
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {history.map((entry, i) => {
          const conf = entry.confidence || 0;
          let confColor = 'text-red-400';
          let confBg = 'bg-red-900/30';
          if (conf >= 90) { confColor = 'text-green-400'; confBg = 'bg-green-900/30'; }
          else if (conf >= 70) { confColor = 'text-yellow-400'; confBg = 'bg-yellow-900/30'; }

          // Trip distance from previous
          const next = history[i + 1];
          const trip = next && entry.reading && next.reading
            ? entry.reading - next.reading
            : null;

          return (
            <div key={entry.id || i} className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <div className="flex items-center gap-4">
                {/* Thumbnail */}
                {entry.preview && (
                  <img
                    src={entry.preview}
                    alt=""
                    className="w-14 h-10 rounded object-cover flex-shrink-0"
                  />
                )}

                {/* Reading */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-3">
                    <span className="text-xl font-bold tabular-nums">
                      {entry.reading != null ? Number(entry.reading).toLocaleString() : '---'}
                    </span>
                    {trip != null && trip > 0 && (
                      <span className="text-xs text-green-400 bg-green-900/30 px-2 py-0.5 rounded-full">
                        +{trip.toLocaleString()}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-3 text-xs text-gray-500 mt-1">
                    <span>
                      {entry.timestamp
                        ? new Date(entry.timestamp).toLocaleDateString(undefined, {
                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                          })
                        : ''}
                    </span>
                    <span>via {entry.method || '?'}</span>
                    {entry.totalTime && <span>{entry.totalTime}ms</span>}
                  </div>
                </div>

                {/* Confidence */}
                <span className={`text-sm px-2.5 py-1 rounded-full ${confBg} ${confColor} flex-shrink-0`}>
                  {conf}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
