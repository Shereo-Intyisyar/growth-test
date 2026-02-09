const STORAGE_KEY = 'odometer_readings';

export function getReadings() {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

export function saveReading(reading) {
  const readings = getReadings();
  readings.unshift({
    ...reading,
    id: Date.now(),
    timestamp: new Date().toISOString(),
  });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(readings));
  return readings;
}

export function deleteReading(id) {
  const readings = getReadings().filter((r) => r.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(readings));
  return readings;
}
