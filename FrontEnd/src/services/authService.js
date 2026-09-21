/**
 * Authentication Service connecting FrontEnd to BackEnd Express API
 * Endpoints:
 *   - POST /api/users/register : Register a new citizen account
 *   - POST /api/users/login    : Login existing user & obtain JWT tokens
 *   - POST /api/users/logout   : Sign out current session
 *   - GET  /api/users/me       : Get current authenticated user profile
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000';

/**
 * Register a new user
 * @param {Object} params - { email, password, fullName, phone }
 */
export async function registerUser({ email, password, fullName, phone }) {
  try {
    const res = await fetch(`${API_BASE}/api/users/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email.trim(),
        password,
        fullName: fullName.trim(),
        phone: phone ? phone.trim() : undefined,
      }),
    });

    const data = await res.json().catch(() => null);

    if (!res.ok || (data && !data.success)) {
      return {
        success: false,
        message: data?.message || `Registration failed with status ${res.status}`,
      };
    }

    return {
      success: true,
      data,
    };
  } catch (error) {
    return {
      success: false,
      message: 'Unable to connect to backend server. Please verify backend is running on port 5000.',
      isNetworkError: true,
    };
  }
}

/**
 * Login user with email & password
 * @param {Object} params - { email, password }
 */
export async function loginUser({ email, password }) {
  try {
    const res = await fetch(`${API_BASE}/api/users/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email.trim(),
        password,
      }),
    });

    const data = await res.json().catch(() => null);

    if (!res.ok || (data && !data.success)) {
      return {
        success: false,
        message: data?.message || `Login failed with status ${res.status}`,
      };
    }

    return {
      success: true,
      data,
    };
  } catch (error) {
    return {
      success: false,
      message: 'Unable to connect to backend server. Please verify backend is running on port 5000.',
      isNetworkError: true,
    };
  }
}

/**
 * Store user session in localStorage and dispatch reactive update events
 */
export function storeAuthSession({ user, accessToken, refreshToken, fallbackName }) {
  const meta = user?.user_metadata || {};
  const resolvedName = meta.full_name || meta.fullName || user?.fullName || fallbackName || user?.email?.split('@')[0] || 'Citizen';

  const userData = {
    id: user?.id,
    fullName: resolvedName,
    email: user?.email,
    phone: meta.phone || user?.phone || '',
  };

  localStorage.setItem('fin_user', JSON.stringify(userData));
  if (accessToken) localStorage.setItem('fin_token', accessToken);
  if (refreshToken) localStorage.setItem('fin_refresh_token', refreshToken);

  window.dispatchEvent(new CustomEvent('fin_user_updated', { detail: userData }));
  window.dispatchEvent(new Event('storage'));

  return userData;
}

/**
 * Logout user session
 */
export async function logoutUser() {
  const token = localStorage.getItem('fin_token');
  if (token) {
    try {
      await fetch(`${API_BASE}/api/users/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (e) {
      // Continue client logout even if backend call fails
    }
  }

  localStorage.removeItem('fin_user');
  localStorage.removeItem('fin_token');
  localStorage.removeItem('fin_refresh_token');

  window.dispatchEvent(new CustomEvent('fin_user_updated', { detail: null }));
  window.dispatchEvent(new Event('storage'));
}

/**
 * Get stored user profile from localStorage
 */
export function getStoredUser() {
  try {
    const raw = localStorage.getItem('fin_user');
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

/**
 * Get stored auth access token
 */
export function getStoredToken() {
  return localStorage.getItem('fin_token') || null;
}
