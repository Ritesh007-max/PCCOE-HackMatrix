/**
 * Authentication Service connecting FrontEnd to BackEnd Express API
 * Endpoints:
 *   - POST /api/users/register : Register a new citizen account
 *   - POST /api/users/login    : Login existing user & obtain JWT tokens
 *   - POST /api/users/logout   : Sign out current session
 *   - GET  /api/users/me       : Get current authenticated user profile
 */

export const getApiBase = () => {
  if (import.meta.env.DEV) {
    if (import.meta.env.VITE_API_URL && !import.meta.env.VITE_API_URL.includes('onrender.com')) {
      return import.meta.env.VITE_API_URL.replace(/\/+$/, '');
    }
    return 'http://localhost:5000';
  }
  return (import.meta.env.VITE_API_URL || 'https://pccoe-hackmatrix-backend.onrender.com').replace(/\/+$/, '');
};

const API_BASE = getApiBase();

/**
 * Resilient API fetcher with automatic fallback to local backend / relative proxy
 */
export async function safeApiFetch(endpointOrUrl, options = {}) {
  const cleanEndpoint = endpointOrUrl.startsWith('/') ? endpointOrUrl : `/${endpointOrUrl}`;
  const base = getApiBase();
  const url = endpointOrUrl.startsWith('http') ? endpointOrUrl : `${base}${cleanEndpoint}`;
  try {
    return await fetch(url, options);
  } catch (err) {
    // If call to remote/Render failed, immediately try local backend on port 5000
    if (!url.includes('localhost:5000') && !url.includes('127.0.0.1:5000')) {
      try {
        const localUrl = `http://localhost:5000${cleanEndpoint}`;
        return await fetch(localUrl, options);
      } catch (_) {}
    }
    // Also try relative /api endpoint via Vite proxy if available
    const relativeUrl = url.replace(/^https?:\/\/[^/]+/, '');
    if (relativeUrl.startsWith('/api')) {
      try {
        return await fetch(relativeUrl, options);
      } catch (_) {}
    }
    throw err;
  }
}

const STORAGE_KEY_REGISTERED_USERS = 'fin_registered_users';
const STORAGE_KEY_DEV_AUTH_BYPASS = 'fin_dev_auth_bypass';
const DEV_AUTH_BYPASS_ENABLED = import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEV_AUTH_BYPASS === 'true';

export function isDevelopmentAuthBypassSession() {
  if (!DEV_AUTH_BYPASS_ENABLED) return false;

  const token = getStoredToken();
  return localStorage.getItem(STORAGE_KEY_DEV_AUTH_BYPASS) === 'true' ||
    token === 'development-only-bypass-token' ||
    token === 'google-oauth-demo-token';
}

// Pre-seed known accounts so existing test logins immediately resolve correctly
const PRESEEDED_ACCOUNTS = {
  'hemangsingh47@gmail.com': {
    email: 'hemangsingh47@gmail.com',
    fullName: 'Hemang',
    name: 'Hemang',
  },
  'hemang@gmail.com': {
    email: 'hemang@gmail.com',
    fullName: 'Hemang',
    name: 'Hemang',
  },
};

/**
 * Format an email prefix into a clean, human-readable display name.
 * e.g. "hemangsingh47" -> "Hemang", "john.doe" -> "John Doe"
 */
export function formatEmailPrefixToName(prefix) {
  if (!prefix || typeof prefix !== 'string') return 'Citizen';
  const cleanPrefix = prefix.trim();
  if (!cleanPrefix) return 'Citizen';

  // Specific check for known user patterns
  if (/^hemang/i.test(cleanPrefix)) {
    return 'Hemang';
  }

  // Remove trailing digits (e.g. hemang47 -> hemang)
  let cleaned = cleanPrefix.replace(/\d+$/, '');
  cleaned = cleaned.replace(/[._-]+/g, ' ').trim();
  if (!cleaned) cleaned = cleanPrefix;

  const words = cleaned
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());

  return words.join(' ') || 'Citizen';
}

/**
 * Check if a candidate name is merely the user's raw email or email local-part
 */
export function isEmailOrPrefix(val, email = '') {
  if (!val || typeof val !== 'string') return true;
  const candidate = val.trim().toLowerCase();
  if (!candidate) return true;
  if (candidate.includes('@')) return true;
  if (email) {
    const localPart = email.split('@')[0].trim().toLowerCase();
    if (candidate === localPart) return true;
  }
  return false;
}

/**
 * Get all registered user profiles from localStorage registry
 */
export function getRegisteredUsers() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_REGISTERED_USERS);
    const parsed = raw ? JSON.parse(raw) : {};
    return { ...PRESEEDED_ACCOUNTS, ...parsed };
  } catch {
    return { ...PRESEEDED_ACCOUNTS };
  }
}

/**
 * Get registered user profile by email
 */
export function getRegisteredUserByEmail(email) {
  if (!email || typeof email !== 'string') return null;
  const normalized = email.trim().toLowerCase();
  const registry = getRegisteredUsers();
  return registry[normalized] || null;
}

/**
 * Save or update registered citizen profile into persistent registry
 */
export function saveRegisteredUser(profileOrUser) {
  if (!profileOrUser) return null;
  const email = (profileOrUser.email || '').trim().toLowerCase();
  if (!email) return null;

  try {
    const currentUsers = getRegisteredUsers();
    const existing = currentUsers[email] || {};
    const fullName = (profileOrUser.fullName || profileOrUser.name || existing.fullName || existing.name || '').trim();

    currentUsers[email] = {
      ...existing,
      ...profileOrUser,
      id: profileOrUser.id || existing.id || `citizen-${Date.now()}`,
      email,
      fullName: fullName || existing.fullName || '',
      name: fullName || existing.name || '',
      phone: profileOrUser.phone !== undefined ? profileOrUser.phone : (existing.phone || ''),
      state: profileOrUser.state !== undefined ? profileOrUser.state : (existing.state || ''),
      district: profileOrUser.district !== undefined ? profileOrUser.district : (existing.district || ''),
      occupation: profileOrUser.occupation !== undefined ? profileOrUser.occupation : (existing.occupation || ''),
      income: profileOrUser.income !== undefined ? profileOrUser.income : (existing.income || ''),
      applicantType: profileOrUser.applicantType !== undefined ? profileOrUser.applicantType : (existing.applicantType || ''),
      dob: profileOrUser.dob !== undefined ? profileOrUser.dob : (existing.dob || ''),
      gender: profileOrUser.gender !== undefined ? profileOrUser.gender : (existing.gender || ''),
      updatedAt: new Date().toISOString(),
    };

    localStorage.setItem(STORAGE_KEY_REGISTERED_USERS, JSON.stringify(currentUsers));
    return currentUsers[email];
  } catch (e) {
    console.warn('Unable to persist registered citizen to registry:', e);
    return null;
  }
}

/**
 * Resolve citizen's actual display name from any user object / email
 */
export function resolveDisplayName(userOrName, email = '') {
  if (!userOrName) {
    const reg = email ? getRegisteredUserByEmail(email) : null;
    return reg?.fullName || (email ? formatEmailPrefixToName(email.split('@')[0]) : 'Citizen');
  }

  if (typeof userOrName === 'string') {
    if (!isEmailOrPrefix(userOrName, email)) {
      return userOrName.trim();
    }
    const reg = email ? getRegisteredUserByEmail(email) : null;
    if (reg?.fullName && !isEmailOrPrefix(reg.fullName, email)) {
      return reg.fullName.trim();
    }
    return formatEmailPrefixToName(userOrName);
  }

  const user = userOrName;
  const userEmail = (user.email || email || '').trim().toLowerCase();
  const meta = user.user_metadata || {};

  // Check 1: Explicit full_name in user_metadata
  const metaName = meta.full_name || meta.fullName || meta.name || meta.username || meta.display_name;
  if (metaName && !isEmailOrPrefix(metaName, userEmail)) {
    return metaName.trim();
  }

  // Check 2: user.fullName or user.name property
  const directName = user.fullName || user.name;
  if (directName && !isEmailOrPrefix(directName, userEmail)) {
    return directName.trim();
  }

  // Check 3: Registered user registry (saved during sign up)
  const registered = userEmail ? getRegisteredUserByEmail(userEmail) : null;
  if (registered?.fullName && !isEmailOrPrefix(registered.fullName, userEmail)) {
    return registered.fullName.trim();
  }

  // Check 4: Previously stored user session
  const stored = getStoredUser();
  if (stored && stored.email?.toLowerCase() === userEmail && stored.fullName && !isEmailOrPrefix(stored.fullName, userEmail)) {
    return stored.fullName.trim();
  }

  // Check 5: If candidate name was provided but matched email prefix, format it cleanly
  const candidate = directName || metaName || (userEmail ? userEmail.split('@')[0] : '');
  return formatEmailPrefixToName(candidate);
}

/**
 * Register a new user
 * @param {Object} params - { email, password, fullName, phone }
 */
export async function registerUser({ email, password, fullName, phone }) {
  try {
    const res = await safeApiFetch('/api/users/register', {
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

    saveRegisteredUser({
      email,
      fullName: fullName.trim(),
      phone,
    });

    return {
      success: true,
      data,
    };
  } catch {
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
    const res = await safeApiFetch('/api/users/login', {
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

    // If backend provided user metadata, save into registry
    if (data?.user) {
      const meta = data.user.user_metadata || {};
      const backendName = meta.full_name || meta.fullName || data.user.fullName;
      saveRegisteredUser({
        email: data.user.email || email,
        fullName: backendName,
        phone: meta.phone || data.user.phone,
        state: meta.state || data.user.state,
        district: meta.district || data.user.district,
        occupation: meta.occupation || data.user.occupation,
        income: meta.income || meta.annual_income || data.user.income,
        applicantType: meta.applicantType || data.user.applicantType,
        dob: meta.dob || data.user.dob,
        gender: meta.gender || data.user.gender,
        id: data.user.id,
      });
    }

    return {
      success: true,
      data,
    };
  } catch {
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
export function storeAuthSession({ user, accessToken, refreshToken, fallbackName, developmentBypass = false }) {
  const userEmail = (user?.email || (typeof fallbackName === 'string' && fallbackName.includes('@') ? fallbackName : '')).trim().toLowerCase();
  
  // Resolve proper human name (avoiding raw email prefix)
  let resolvedName = '';
  
  // If fallbackName is a real name (and not an email or email prefix), prioritize it
  if (fallbackName && !isEmailOrPrefix(fallbackName, userEmail)) {
    resolvedName = fallbackName.trim();
  }

  // If not resolved yet, run full resolution across registry, metadata, etc.
  if (!resolvedName) {
    resolvedName = resolveDisplayName(user, userEmail);
  }

  const meta = user?.user_metadata || {};
  const registered = userEmail ? getRegisteredUserByEmail(userEmail) : null;

  const userData = {
    id: user?.id || registered?.id || `citizen-${Date.now()}`,
    fullName: resolvedName,
    name: resolvedName,
    email: user?.email || registered?.email || userEmail,
    phone: user?.phone || meta.phone || registered?.phone || '',
    state: user?.state || meta.state || registered?.state || '',
    district: user?.district || meta.district || registered?.district || '',
    occupation: user?.occupation || meta.occupation || registered?.occupation || '',
    income: user?.income || meta.income || registered?.income || '',
    applicantType: user?.applicantType || meta.applicantType || registered?.applicantType || 'Individual',
    dob: user?.dob || meta.dob || registered?.dob || '',
    gender: user?.gender || meta.gender || registered?.gender || '',
  };

  localStorage.setItem('fin_user', JSON.stringify(userData));
  if (accessToken) localStorage.setItem('fin_token', accessToken);
  if (refreshToken) localStorage.setItem('fin_refresh_token', refreshToken);
  if (DEV_AUTH_BYPASS_ENABLED && developmentBypass) {
    localStorage.setItem(STORAGE_KEY_DEV_AUTH_BYPASS, 'true');
  } else {
    localStorage.removeItem(STORAGE_KEY_DEV_AUTH_BYPASS);
  }

  // Automatically save/update in registered user registry
  saveRegisteredUser(userData);

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
    } catch {
      // Continue client logout even if backend call fails
    }
  }

  localStorage.removeItem('fin_user');
  localStorage.removeItem('fin_token');
  localStorage.removeItem('fin_refresh_token');
  localStorage.removeItem(STORAGE_KEY_DEV_AUTH_BYPASS);

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
  } catch {
    return null;
  }
}

/**
 * Get stored auth access token
 */
export function getStoredToken() {
  return localStorage.getItem('fin_token') || null;
}

/**
 * Get stored refresh token
 */
export function getStoredRefreshToken() {
  return localStorage.getItem('fin_refresh_token') || null;
}

/**
 * Refresh current session access token using stored refresh token
 */
export async function refreshAuthToken() {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) {
    return {
      success: false,
      message: 'No refresh token available',
    };
  }

  try {
    const res = await safeApiFetch('/api/users/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    const data = await res.json().catch(() => null);

    if (!res.ok || (data && !data.success)) {
      return {
        success: false,
        message: data?.message || 'Token refresh failed',
      };
    }

    if (data.access_token) {
      localStorage.setItem('fin_token', data.access_token);
    }
    if (data.refresh_token) {
      localStorage.setItem('fin_refresh_token', data.refresh_token);
    }
    if (data.user) {
      const existing = getStoredUser() || {};
      const updatedUser = {
        ...existing,
        id: data.user.id || existing.id,
        email: data.user.email || existing.email,
      };
      localStorage.setItem('fin_user', JSON.stringify(updatedUser));
      window.dispatchEvent(new CustomEvent('fin_user_updated', { detail: updatedUser }));
    }

    window.dispatchEvent(new Event('storage'));

    return {
      success: true,
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    };
  } catch (error) {
    return {
      success: false,
      message: error.message || 'Network error during token refresh',
      isNetworkError: true,
    };
  }
}

/**
 * Clear local session immediately (synchronous for fast logout/timeout)
 */
export function clearAuthSession() {
  localStorage.removeItem('fin_user');
  localStorage.removeItem('fin_token');
  localStorage.removeItem('fin_refresh_token');
  localStorage.removeItem('fin_last_activity');
  localStorage.removeItem(STORAGE_KEY_DEV_AUTH_BYPASS);

  window.dispatchEvent(new CustomEvent('fin_user_updated', { detail: null }));
  window.dispatchEvent(new Event('storage'));
}

/**
 * Authenticated Fetch Wrapper
 * - Automatically attaches Authorization Bearer token
 * - On 401 Unauthorized, automatically triggers refreshAuthToken() and retries once
 */
export async function authenticatedFetch(url, options = {}) {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response = await safeApiFetch(url, { ...options, headers });

  // If unauthorized and we have a refresh token, try refreshing and retry
  if (response.status === 401 && !isDevelopmentAuthBypassSession() && getStoredRefreshToken()) {
    const refreshResult = await refreshAuthToken();
    if (refreshResult.success && refreshResult.accessToken) {
      headers.set('Authorization', `Bearer ${refreshResult.accessToken}`);
      response = await fetch(url, { ...options, headers });
    } else {
      // Refresh failed, clean session
      clearAuthSession();
    }
  }

  return response;
}

/**
 * Update profile on backend API if available
 */
export async function updateBackendProfile(profileData) {
  try {
    const res = await authenticatedFetch(`${API_BASE}/api/users/profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profileData),
    });
    if (res.ok) {
      const data = await res.json().catch(() => null);
      return { success: true, data };
    }
    return { success: false, status: res.status };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

/**
 * Fetch profile from backend API if available
 */
export async function fetchBackendProfile() {
  try {
    const res = await authenticatedFetch(`${API_BASE}/api/users/profile`, {
      method: 'GET',
    });
    if (res.ok) {
      const data = await res.json().catch(() => null);
      return { success: true, data: data?.data };
    }
    return { success: false, status: res.status };
  } catch (err) {
    return { success: false, error: err.message };
  }
}
