import { safeApiFetch, getStoredToken } from './authService';

const getAuthHeaders = () => {
  const token = getStoredToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
};

/**
 * Fetch tenant-isolated notifications for the active user
 */
export async function fetchNotifications() {
  const res = await safeApiFetch('/api/notifications', {
    headers: getAuthHeaders()
  });

  const json = await res.json().catch(() => null);
  if (!res.ok || !json?.success) {
    throw new Error(json?.message || `Failed to fetch notifications (${res.status})`);
  }
  return {
    notifications: json.data || [],
    unreadCount: json.unreadCount || 0
  };
}

/**
 * Mark a single notification as read
 */
export async function markNotificationAsRead(id) {
  const res = await safeApiFetch(`/api/notifications/${id}/read`, {
    method: 'PATCH',
    headers: getAuthHeaders()
  });

  const json = await res.json().catch(() => null);
  if (!res.ok || !json?.success) {
    throw new Error(json?.message || `Failed to mark notification as read (${res.status})`);
  }
  return json.data;
}

/**
 * Mark all notifications as read
 */
export async function markAllNotificationsAsRead() {
  const res = await safeApiFetch('/api/notifications/read-all', {
    method: 'POST',
    headers: getAuthHeaders()
  });

  const json = await res.json().catch(() => null);
  if (!res.ok || !json?.success) {
    throw new Error(json?.message || `Failed to mark all as read (${res.status})`);
  }
  return json;
}
