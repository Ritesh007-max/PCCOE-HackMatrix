import { authenticatedFetch } from './authService.js';

const API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) || 'http://localhost:5000';

/**
 * Fetch list of prior FIN AI conversations for authenticated user.
 * Returns array of { id, title, createdAt, updatedAt, messageCount, lastMessage }.
 */
export async function fetchChatHistory() {
  const res = await authenticatedFetch(`${API_BASE_URL}/api/chat/history`);
  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    throw new Error(errJson.message || `Failed to fetch chat history (${res.status})`);
  }
  const json = await res.json();
  return Array.isArray(json?.data) ? json.data : [];
}

/**
 * Reopen a specific conversation with all historical messages by ID.
 */
export async function fetchConversationById(conversationId) {
  if (!conversationId) throw new Error('Conversation ID is required');

  const res = await authenticatedFetch(`${API_BASE_URL}/api/chat/history/${encodeURIComponent(conversationId)}`);
  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    throw new Error(errJson.message || `Failed to load conversation (${res.status})`);
  }
  const json = await res.json();
  return json?.data || null;
}

/**
 * Delete a specific conversation.
 */
export async function deleteConversationById(conversationId) {
  if (!conversationId) return false;

  const res = await authenticatedFetch(`${API_BASE_URL}/api/chat/history/${encodeURIComponent(conversationId)}`, {
    method: 'DELETE'
  });
  return res.ok;
}
