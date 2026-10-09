/**
 * FIN — Scheme to Document Readiness Navigation Helper
 *
 * Provides a canonical, deep-linkable URL generator and navigation helper:
 * - Directs from Scheme Details / Cards to My Documents Scheme Readiness Checker
 * - Preserves canonical scheme identifier (slug or UUID) without hardcoded names
 * - Handles navigation safely with browser history preservation
 */

/**
 * Validates whether a scheme identifier is non-empty and well-formed.
 *
 * @param {*} schemeId
 * @returns {boolean}
 */
export function isValidSchemeIdentifier(schemeId) {
  if (!schemeId || typeof schemeId !== 'string') return false;
  const clean = schemeId.trim();
  if (clean === '' || clean === 'null' || clean === 'undefined' || clean === 'auto') return false;
  return true;
}

/**
 * Extracts canonical scheme identifier from a scheme object or string.
 *
 * @param {string|Object} schemeOrId
 * @returns {string} Clean canonical identifier or empty string
 */
export function extractCanonicalSchemeId(schemeOrId) {
  if (!schemeOrId) return '';
  if (typeof schemeOrId === 'string') {
    return schemeOrId.trim();
  }
  if (typeof schemeOrId === 'object') {
    return (
      schemeOrId.slug ||
      schemeOrId.scheme_slug ||
      schemeOrId.id ||
      schemeOrId.scheme_id ||
      ''
    ).trim();
  }
  return '';
}

/**
 * Builds the canonical deep link URL to My Documents for a specific scheme's readiness check.
 *
 * @param {string|Object} schemeOrId - Canonical scheme ID, slug, or scheme object
 * @returns {string} The canonical documents URL, e.g. "/documents?schemeId=example-id"
 */
export function getSchemeDocumentsUrl(schemeOrId) {
  const id = extractCanonicalSchemeId(schemeOrId);
  if (!isValidSchemeIdentifier(id)) {
    return '/documents';
  }
  return `/documents?schemeId=${encodeURIComponent(id)}`;
}

/**
 * Navigates to My Documents with the specified scheme selected for document readiness.
 *
 * @param {Function} navigate - React Router navigate function
 * @param {string|Object} schemeOrId - Canonical scheme ID, slug, or scheme object
 * @param {Object} [options] - Navigation options (e.g. { replace: false })
 */
export function navigateToSchemeDocuments(navigate, schemeOrId, options = {}) {
  const url = getSchemeDocumentsUrl(schemeOrId);
  if (typeof navigate === 'function') {
    navigate(url, options);
  } else if (typeof window !== 'undefined') {
    window.location.href = url;
  }
}
