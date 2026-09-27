import { authenticatedFetch, getStoredToken } from './authService';

const API_BASE = (import.meta.env.VITE_API_URL || 'https://pccoe-hackmatrix-backend.onrender.com').replace(/\/+$/, '');

/**
 * Fetch current user profile from GET /api/users/profile
 */
export async function fetchUserProfile() {
  try {
    const res = await authenticatedFetch(`${API_BASE}/api/users/profile`);
    if (!res.ok) {
      throw new Error(`Profile fetch failed: ${res.status}`);
    }
    const json = await res.json();
    return json?.data || null;
  } catch (err) {
    console.warn('Backend profile fetch failed, using stored local data:', err);
    try {
      const stored = localStorage.getItem('fin_user');
      return stored ? JSON.parse(stored) : null;
    } catch (_) {
      return null;
    }
  }
}

/**
 * Update current user profile via PUT /api/users/profile
 */
export async function updateUserProfile(updates) {
  try {
    const res = await authenticatedFetch(`${API_BASE}/api/users/profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.message || `Failed to update profile (${res.status})`);
    }

    const json = await res.json();
    const updatedData = json?.data || updates;

    // Synchronize local storage & trigger update events across components
    try {
      const stored = JSON.parse(localStorage.getItem('fin_user') || '{}');
      const merged = { ...stored, ...updatedData };
      localStorage.setItem('fin_user', JSON.stringify(merged));
      window.dispatchEvent(new CustomEvent('fin_user_updated', { detail: merged }));
    } catch (_) {}

    return updatedData;
  } catch (err) {
    console.warn('Backend profile update failed, updating locally:', err);
    // Graceful offline/local update
    try {
      const stored = JSON.parse(localStorage.getItem('fin_user') || '{}');
      const merged = { ...stored, ...updates };
      localStorage.setItem('fin_user', JSON.stringify(merged));
      window.dispatchEvent(new CustomEvent('fin_user_updated', { detail: merged }));
      return merged;
    } catch (_) {
      throw err;
    }
  }
}
