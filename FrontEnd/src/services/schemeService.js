import { authenticatedFetch, safeApiFetch } from './authService.js';

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) || 'http://localhost:5000';

/**
 * Fetch scheme stats & live category counts from the backend database
 */
export async function fetchSchemeStats() {
  const res = await safeApiFetch(`${API_BASE}/api/schemes/stats`);
  if (!res.ok) {
    return { total: 0, categoryCounts: {} };
  }
  const json = await res.json();
  return {
    total: json?.total ?? 0,
    categoryCounts: json?.categoryCounts || {}
  };
}

/**
 * Fetch schemes directly from the database with pagination and optional filters
 */
export async function fetchSchemes({ limit = 50, offset = 0, category, state, type, query = '' } = {}) {
  const params = new URLSearchParams();
  if (limit) params.set('limit', String(limit));
  if (offset) params.set('offset', String(offset));
  if (category) params.set('category', category);
  if (state) params.set('state', state);
  if (type) params.set('type', type);
  if (query) params.set('q', query);

  const res = await safeApiFetch(`${API_BASE}/api/schemes?${params.toString()}`);
  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    throw new Error(errJson.message || `Failed to fetch schemes (${res.status})`);
  }
  const json = await res.json();
  return {
    source: json?.source || 'database',
    total: json?.total ?? (json?.schemes?.length || 0),
    offset: json?.offset || offset,
    limit: json?.limit || limit,
    schemes: json?.schemes || []
  };
}

/**
 * Search schemes from the database/Intelligence hybrid search
 */
export async function searchSchemes({ query = '', filters = {}, limit = 50, offset = 0 } = {}) {
  const res = await safeApiFetch(`${API_BASE}/api/schemes/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, filters, limit, offset })
  });

  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    throw new Error(errJson.message || `Schemes search failed (${res.status})`);
  }

  const json = await res.json();
  return {
    source: json?.source || 'database',
    degraded: Boolean(json?.degraded),
    total: json?.total ?? (json?.schemes?.length || 0),
    offset: json?.offset || offset,
    limit: json?.limit || limit,
    schemes: json?.schemes || []
  };
}

/**
 * Fetch scheme by ID
 */
export async function fetchSchemeById(schemeId) {
  if (!schemeId) throw new Error('Scheme ID is required');

  const res = await safeApiFetch(`${API_BASE}/api/schemes/${schemeId}`);
  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Scheme fetch failed (${res.status})`);
    error.status = res.status;
    throw error;
  }
  const json = await res.json();
  return json?.scheme || null;
}

/**
 * Check user eligibility for a specific scheme
 */
export async function checkSchemeEligibility(schemeId, profile = null) {
  if (!schemeId) throw new Error('Scheme ID is required');

  const res = await authenticatedFetch(`${API_BASE}/api/eligibility/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ schemeId, profile })
  });

  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Eligibility check failed (${res.status})`);
    error.status = res.status;
    throw error;
  }

  return await res.json();
}

/**
 * Fetch personalized scheme recommendations for authenticated applicant
 */
export async function fetchRecommendedSchemes({ query = 'schemes matching my profile and state', top_k = 12, state_override, category_override } = {}) {
  const res = await authenticatedFetch(`${API_BASE}/api/schemes/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k, state_override, category_override })
  });

  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Failed to fetch recommended schemes (${res.status})`);
    error.status = res.status;
    throw error;
  }

  return await res.json();
}

/**
 * Fetch FAQs for a specific scheme by slug from the database
 */
export async function fetchSchemeFaqs(schemeSlug) {
  if (!schemeSlug) return [];

  const res = await safeApiFetch(`${API_BASE}/api/schemes/${encodeURIComponent(schemeSlug)}/faqs`);
  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Failed to fetch scheme FAQs (${res.status})`);
    error.status = res.status;
    throw error;
  }

  const json = await res.json();
  return json?.faqs || json?.data || [];
}

/**
 * Fetch unified canonical catalog of applicable schemes for citizen's state and Central jurisdiction
 */
export async function fetchApplicableSchemesCatalog(state = 'Gujarat') {
  const params = new URLSearchParams();
  if (state) params.set('state', state);

  const res = await safeApiFetch(`${API_BASE}/api/schemes/applicable?${params.toString()}`);
  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    throw new Error(errJson.message || `Failed to fetch applicable schemes (${res.status})`);
  }
  const json = await res.json();
  return {
    state: json?.state || state,
    totalApplicable: json?.totalApplicable ?? 0,
    applicableStateCount: json?.applicableStateCount ?? 0,
    applicableCentralCount: json?.applicableCentralCount ?? 0,
    schemes: json?.schemes || []
  };
}

