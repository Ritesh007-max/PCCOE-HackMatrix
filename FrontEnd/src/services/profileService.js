import { authenticatedFetch } from './authService';

const API_BASE = (import.meta.env.VITE_API_URL || 'https://pccoe-hackmatrix-backend.onrender.com').replace(/\/+$/, '');

/**
 * Fetch current user profile from GET /api/users/profile
 */
export async function fetchUserProfile() {
  const res = await authenticatedFetch(`${API_BASE}/api/users/profile`);
  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Profile fetch failed: ${res.status}`);
    error.status = res.status;
    throw error;
  }
  const json = await res.json();
  return json?.data || null;
}

/**
 * Update current user profile via PUT /api/users/profile
 */
export async function updateUserProfile(updates) {
  const res = await authenticatedFetch(`${API_BASE}/api/users/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates)
  });

  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Failed to update profile (${res.status})`);
    error.status = res.status;
    throw error;
  }

  const json = await res.json();
  const updatedData = json?.data || updates;

  // Synchronize local storage & trigger update events across components
  try {
    const stored = JSON.parse(localStorage.getItem('fin_user') || '{}');
    const merged = { ...stored, ...updatedData };
    localStorage.setItem('fin_user', JSON.stringify(merged));
    window.dispatchEvent(new CustomEvent('fin_user_updated', { detail: merged }));
  } catch (e) {
    console.debug('Local storage update skipped:', e);
  }

  return updatedData;
}

