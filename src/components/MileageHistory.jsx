import { deleteReading } from '../utils/storage';

export default function MileageHistory({ readings, onUpdate }) {
  const handleDelete = (id) => {
    const updated = deleteReading(id);
    onUpdate(updated);
  };

  if (readings.length === 0) {
    return (
      <div className="history-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.4">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        <p>No readings yet</p>
        <p className="hint">Capture your odometer to get started</p>
      </div>
    );
  }

  // Calculate trip distances between consecutive readings
  const withTrips = readings.map((r, i) => {
    const next = readings[i + 1];
    const trip = next ? r.mileage - next.mileage : null;
    return { ...r, trip };
  });

  return (
    <div className="history-list">
      <div className="history-header">
        <h3>Reading History</h3>
        <span className="reading-count">{readings.length} reading{readings.length !== 1 ? 's' : ''}</span>
      </div>
      {withTrips.map((r) => (
        <div key={r.id} className="history-card">
          <div className="history-card-main">
            <div className="history-mileage">
              <span className="mileage-value">{r.mileage.toLocaleString()}</span>
              <span className="mileage-unit">miles</span>
            </div>
            {r.trip !== null && r.trip > 0 && (
              <div className="trip-badge">+{r.trip.toLocaleString()} mi</div>
            )}
          </div>
          <div className="history-card-meta">
            <span className="history-date">
              {new Date(r.timestamp).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
            <span className="history-confidence">
              {r.confidence >= 60 ? 'High' : 'Low'} confidence
            </span>
          </div>
          <button className="btn-delete" onClick={() => handleDelete(r.id)} title="Delete reading">
            &times;
          </button>
        </div>
      ))}
    </div>
  );
}
