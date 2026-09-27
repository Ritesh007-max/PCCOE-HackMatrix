import { authenticatedFetch } from './authService';

const API_BASE = (import.meta.env.VITE_API_URL || 'https://pccoe-hackmatrix-backend.onrender.com').replace(/\/+$/, '');

/**
 * Fetch list of uploaded documents
 */
export async function fetchUserDocuments() {
  try {
    const res = await authenticatedFetch(`${API_BASE}/api/documents`);
    if (!res.ok) {
      throw new Error(`Documents fetch failed (${res.status})`);
    }
    const json = await res.json();
    return json?.data || [];
  } catch (err) {
    console.warn('Backend documents fetch failed, using local/cached documents:', err);
    return null;
  }
}

/**
 * Upload a document file (PDF, PNG, JPG, etc.)
 */
export async function uploadDocumentFile(file, documentType, applicationId = null) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    if (documentType) formData.append('documentType', documentType);
    if (applicationId) formData.append('applicationId', applicationId);

    const token = localStorage.getItem('fin_auth_token');

    const res = await fetch(`${API_BASE}/api/documents/process`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: formData
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.message || `Document upload failed with status ${res.status}`);
    }

    const json = await res.json();
    return json?.data || null;
  } catch (err) {
    console.warn('Backend document upload failed:', err);
    throw err;
  }
}

/**
 * Extract data from document using AI OCR
 */
export async function extractDocumentData(documentId) {
  try {
    const res = await authenticatedFetch(`${API_BASE}/api/documents/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ documentId })
    });

    if (!res.ok) {
      throw new Error(`Document extraction failed (${res.status})`);
    }

    const json = await res.json();
    return json?.data || null;
  } catch (err) {
    console.warn('Backend document extraction failed:', err);
    throw err;
  }
}

/**
 * Delete a document
 */
export async function deleteDocument(documentId) {
  try {
    const res = await authenticatedFetch(`${API_BASE}/api/documents/${documentId}`, {
      method: 'DELETE'
    });

    if (!res.ok) {
      throw new Error(`Failed to delete document (${res.status})`);
    }

    return true;
  } catch (err) {
    console.warn('Backend document delete failed:', err);
    throw err;
  }
}
