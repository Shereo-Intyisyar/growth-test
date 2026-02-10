import { useState, useEffect } from 'react';
import { getStats } from '../utils/api';

export default function AnalyticsDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="text-center py-16 text-gray-400">
        Loading analytics...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-red-400">{error}</p>
        <p className="text-sm text-gray-500 mt-2">Make sure the backend API is running</p>
      </div>
    );
  }

  if (!stats || stats.total_processed === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-400">No data yet</p>
        <p className="text-sm text-gray-500 mt-2">Process some images to see analytics</p>
      </div>
    );
  }

  const methodEntries = Object.entries(stats.methods || {});

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-lg font-semibold">Analytics Dashboard</h2>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Total Processed"
          value={stats.total_processed}
        />
        <StatCard
          label="Avg Confidence"
          value={`${stats.average_confidence}%`}
          color={stats.average_confidence >= 80 ? 'text-green-400' : 'text-yellow-400'}
        />
        <StatCard
          label="Methods Active"
          value={methodEntries.length}
        />
      </div>

      {/* Method breakdown */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h3 className="text-sm font-medium text-gray-300 mb-4">Method Performance</h3>
        <div className="space-y-4">
          {methodEntries.map(([name, data]) => (
            <div key={name}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm capitalize">{name.replace(/_/g, ' ')}</span>
                <div className="flex gap-4 text-xs text-gray-400">
                  <span>{data.success_count} successes</span>
                  <span>{data.average_time_ms}ms avg</span>
                  <span className={
                    data.success_rate >= 80 ? 'text-green-400' :
                    data.success_rate >= 50 ? 'text-yellow-400' : 'text-red-400'
                  }>
                    {data.success_rate}% rate
                  </span>
                </div>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2">
                <div
                  className={`h-full rounded-full ${
                    data.success_rate >= 80 ? 'bg-green-500' :
                    data.success_rate >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${data.success_rate}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color = 'text-white' }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-bold tabular-nums ${color}`}>{value}</p>
    </div>
  );
}
