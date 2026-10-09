import { safeApiFetch, getStoredToken } from './authService';

const getAuthHeaders = () => {
  const token = getStoredToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
};

/**
 * Fetch dynamic reviewer dashboard statistics
 */
export async function fetchReviewerDashboardStats() {
  const res = await safeApiFetch('/api/reviewer/dashboard', {
    headers: getAuthHeaders()
  });

  const json = await res.json().catch(() => null);
  if (!res.ok || !json?.success) {
    throw new Error(json?.message || `Failed to fetch dashboard stats (${res.status})`);
  }
  return json.data;
}

/**
 * Fetch review applications queue
 */
export async function fetchReviewerApplicationsQueue(status = 'all') {
  const url = status && status !== 'all'
    ? `/api/reviewer/applications?status=${encodeURIComponent(status)}`
    : '/api/reviewer/applications';

  const res = await safeApiFetch(url, {
    headers: getAuthHeaders()
  });

  const json = await res.json().catch(() => null);
  if (!res.ok || !json?.success) {
    throw new Error(json?.message || `Failed to fetch review queue (${res.status})`);
  }
  return json.data || [];
}

/**
 * Fetch detailed application facts, OCR documents, and review history
 */
export async function fetchApplicationReviewDetails(applicationId) {
  const res = await safeApiFetch(`/api/reviewer/applications/${applicationId}`, {
    headers: getAuthHeaders()
  });

  const json = await res.json().catch(() => null);
  if (!res.ok || !json?.success) {
    throw new Error(json?.message || `Failed to fetch application details (${res.status})`);
  }
  return json.data;
}

/**
 * Submit official review decision
 * @param {string} applicationId
 * @param {string} decision - 'approve' | 'request_changes' | 'reject'
 * @param {string} remark - Mandatory for reject / request_changes
 */
export async function submitReviewDecision(applicationId, { decision, remark }) {
  const res = await safeApiFetch(`/api/reviewer/applications/${applicationId}/decision`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ decision, remark })
  });

  const json = await res.json().catch(() => null);
  if (!res.ok || !json?.success) {
    throw new Error(json?.message || `Review decision submission failed (${res.status})`);
  }
  return json;
}
