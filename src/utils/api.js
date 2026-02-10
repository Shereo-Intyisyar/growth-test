/**
 * API client for the Flask backend.
 */

const API_BASE = '/api';

export async function processOdometer(file, options = {}) {
  const formData = new FormData();
  formData.append('image', file);

  if (options.methods) {
    formData.append('methods', options.methods.join(','));
  }
  if (options.params) {
    formData.append('params', JSON.stringify(options.params));
  }

  const res = await fetch(`${API_BASE}/process-odometer`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(err.error || 'Processing failed');
  }

  return res.json();
}

export async function processOdometerBase64(base64Image, options = {}) {
  const res = await fetch(`${API_BASE}/process-odometer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image: base64Image,
      methods: options.methods,
      params: options.params,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(err.error || 'Processing failed');
  }

  return res.json();
}

export async function batchProcess(files) {
  const formData = new FormData();
  files.forEach((f) => formData.append('images', f));

  const res = await fetch(`${API_BASE}/batch-process`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    throw new Error('Batch processing failed');
  }

  return res.json();
}

export async function getPreprocessingSteps(resultId) {
  const res = await fetch(`${API_BASE}/preprocessing-steps/${resultId}`);
  if (!res.ok) throw new Error('Not found');
  return res.json();
}

export async function getStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function getResults() {
  const res = await fetch(`${API_BASE}/results`);
  if (!res.ok) throw new Error('Failed to fetch results');
  return res.json();
}

export async function correctResult(resultId, reading) {
  const res = await fetch(`${API_BASE}/correct/${resultId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reading }),
  });
  if (!res.ok) throw new Error('Correction failed');
  return res.json();
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export function getExportCsvUrl() {
  return `${API_BASE}/export-csv`;
}
