import { authenticatedFetch } from './authService';

const API_BASE = (import.meta.env.VITE_API_URL || 'https://pccoe-hackmatrix-backend.onrender.com').replace(/\/+$/, '');

/**
 * Fetch submitted applications for the current user
 */
export async function fetchUserApplications() {
  const res = await authenticatedFetch(`${API_BASE}/api/applications`);
  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Failed to fetch applications (${res.status})`);
    error.status = res.status;
    throw error;
  }
  const json = await res.json();
  return json?.data || [];
}

/**
 * Submit a new application for a scheme
 */
export async function submitApplication(applicationData) {
  const res = await authenticatedFetch(`${API_BASE}/api/applications`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(applicationData)
  });

  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Failed to submit application (${res.status})`);
    error.status = res.status;
    throw error;
  }

  const json = await res.json();
  return json?.data || null;
}

/**
 * Analyze readiness / eligibility for a scheme before applying
 */
export async function analyzeApplicationReadiness(schemeId, profile = null) {
  if (!schemeId) throw new Error('Scheme ID is required');

  const res = await authenticatedFetch(`${API_BASE}/api/applications/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ schemeId, profile })
  });

  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Failed to analyze application readiness (${res.status})`);
    error.status = res.status;
    throw error;
  }

  const json = await res.json();
  return json?.data || null;
}

