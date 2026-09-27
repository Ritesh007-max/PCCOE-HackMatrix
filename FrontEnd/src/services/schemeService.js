import { authenticatedFetch, safeApiFetch } from './authService';

const API_BASE = (import.meta.env.VITE_API_URL || 'https://pccoe-hackmatrix-backend.onrender.com').replace(/\/+$/, '');

/**
 * Search schemes from the database
 */
export async function searchSchemes({ query = '', filters = {}, limit = 50 } = {}) {
  try {
    const res = await safeApiFetch(`${API_BASE}/api/schemes/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, filters, limit })
    });

    if (!res.ok) {
      throw new Error(`Schemes search failed (${res.status})`);
    }

    const json = await res.json();
    return json?.schemes || [];
  } catch (err) {
    console.warn('Backend scheme search failed, using local schemes data:', err);
    return null;
  }
}

/**
 * Fetch scheme by ID
 */
export async function fetchSchemeById(schemeId) {
  try {
    const res = await safeApiFetch(`${API_BASE}/api/schemes/${schemeId}`);
    if (!res.ok) {
      throw new Error(`Scheme fetch failed (${res.status})`);
    }
    const json = await res.json();
    return json?.scheme || null;
  } catch (err) {
    console.warn(`Backend scheme fetch for ${schemeId} failed, using local schemes:`, err);
    return null;
  }
}

/**
 * Check user eligibility for a specific scheme
 */
export async function checkSchemeEligibility(schemeId, profileOverride = null) {
  try {
    const res = await authenticatedFetch(`${API_BASE}/api/eligibility/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schemeId, profileOverride })
    });

    if (!res.ok) {
      throw new Error(`Eligibility check failed (${res.status})`);
    }

    const json = await res.json();
    return json?.data || null;
  } catch (err) {
    console.warn(`Backend eligibility check failed:`, err);
    return null;
  }
}
