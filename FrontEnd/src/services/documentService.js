import { authenticatedFetch } from './authService';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000';

/**
 * Fetch list of uploaded documents
 */
export async function fetchUserDocuments() {
  const res = await authenticatedFetch(`${API_BASE}/api/documents`);
  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Documents fetch failed (${res.status})`);
    error.status = res.status;
    throw error;
  }
  const json = await res.json();
  return json?.data || [];
}

/**
 * Upload a document file (PDF, PNG, JPG, etc.)
 */
export async function uploadDocumentFile(file, documentType, applicationId = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (documentType) formData.append('documentType', documentType);
  if (applicationId) formData.append('applicationId', applicationId);

  const res = await authenticatedFetch(`${API_BASE}/api/documents/process`, {
    method: 'POST',
    body: formData
  });

  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Document upload failed with status ${res.status}`);
    error.status = res.status;
    throw error;
  }

  const json = await res.json();
  return json?.data || null;
}

/**
 * Extract data from document using AI OCR
 */
export async function extractDocumentData(documentId) {
  if (!documentId) throw new Error('Document ID is required');

  const res = await authenticatedFetch(`${API_BASE}/api/documents/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ documentId })
  });

  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Document extraction failed (${res.status})`);
    error.status = res.status;
    throw error;
  }

  const json = await res.json();
  return json?.data || null;
}

/**
 * Delete a document
 */
export async function deleteDocument(documentId) {
  if (!documentId) throw new Error('Document ID is required');

  const res = await authenticatedFetch(`${API_BASE}/api/documents/${documentId}`, {
    method: 'DELETE'
  });

  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Failed to delete document (${res.status})`);
    error.status = res.status;
    throw error;
  }

  return true;
}

/**
 * Get details and signed download URL for a single document
 */
export async function getDocumentDetails(documentId) {
  if (!documentId) throw new Error('Document ID is required');

  const res = await authenticatedFetch(`${API_BASE}/api/documents/${documentId}`);
  if (!res.ok) {
    const errJson = await res.json().catch(() => ({}));
    const error = new Error(errJson.message || `Failed to fetch document details (${res.status})`);
    error.status = res.status;
    throw error;
  }

  const json = await res.json();
  return json?.data || null;
}

