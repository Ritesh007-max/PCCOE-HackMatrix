import { authenticatedFetch } from './authService';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000';

/**
 * Fetch submitted applications for the current user
 */
export async function fetchUserApplications() {
  try {
    const res = await authenticatedFetch(`${API_BASE}/api/applications`);
    if (!res.ok) {
      throw new Error(`Failed to fetch applications (${res.status})`);
    }
    const json = await res.json();
    return json?.data || [];
  } catch (err) {
    console.warn('Backend fetch applications failed, using local/cached applications:', err);
    return null;
  }
}

/**
 * Submit a new application for a scheme
 */
export async function submitApplication(applicationData) {
  try {
    const res = await authenticatedFetch(`${API_BASE}/api/applications`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(applicationData)
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.message || `Failed to submit application (${res.status})`);
    }

    const json = await res.json();
    return json?.data || null;
  } catch (err) {
    console.warn('Backend submit application failed:', err);
    throw err;
  }
}

/**
 * Analyze readiness / eligibility for a scheme before applying
 */
export async function analyzeApplicationReadiness(schemeId, profile = null) {
  try {
    const res = await authenticatedFetch(`${API_BASE}/api/applications/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schemeId, profile })
    });

    if (!res.ok) {
      throw new Error(`Failed to analyze application readiness (${res.status})`);
    }

    const json = await res.json();
    return json?.data || null;
  } catch (err) {
    console.warn('Backend application analyze failed:', err);
    return null;
  }
}
