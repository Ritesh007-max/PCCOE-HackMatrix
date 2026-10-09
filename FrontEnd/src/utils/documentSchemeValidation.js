/**
 * Canonical Scheme Validation & Resolution for Documents Page
 * FIN — Financial Policy Intelligence
 *
 * Enforces strict validation against authoritative scheme records:
 * - Prevents fabricated/hardcoded fallback scheme injection
 * - Guards application submission against empty catalog, missing selection, or invalid/stale scheme IDs
 * - Resolves verified scheme metadata and authentic benefit amounts
 */

import { buildDynamicSchemeChecklist, normalizeDocRequirementId } from '../data/documentsData.js';
import { matchDocumentStatus } from './schemeDetailsHelpers.js';

/**
 * Filters and validates active schemes returned from the canonical catalog API.
 * Never silently substitutes mock/fabricated scheme objects on empty or failure.
 *
 * @param {Object|Array} apiResponse
 * @returns {Array} Array of canonical scheme records, or empty array
 */
export function filterActiveSchemesForCatalog(apiResponse) {
  if (!apiResponse) return [];
  if (Array.isArray(apiResponse.schemes)) {
    return apiResponse.schemes.filter(s => s && (s.id || s.scheme_id));
  }
  if (Array.isArray(apiResponse)) {
    return apiResponse.filter(s => s && (s.id || s.scheme_id));
  }
  return [];
}

/**
 * Strictly derives the dynamic scheme checklist from loaded catalog records.
 * Returns an empty array if the catalog is empty or unavailable (no fallback schemes).
 *
 * @param {Array} availableSchemesList
 * @returns {Array} Checklist items or empty array
 */
export function deriveDynamicSchemeChecklist(availableSchemesList) {
  if (!Array.isArray(availableSchemesList) || availableSchemesList.length === 0) {
    return [];
  }
  return buildDynamicSchemeChecklist(availableSchemesList);
}

/**
 * Validates a user's scheme selection against the active catalog.
 *
 * @param {string} selectedSchemeId - ID to validate
 * @param {Array} availableSchemesList - Current catalog schemes loaded from API
 * @returns {{ valid: boolean, error?: string, message?: string, matchingScheme?: Object }}
 */
export function validateSchemeSelection(selectedSchemeId, availableSchemesList) {
  // 1. Guard against empty or unavailable catalog
  if (!Array.isArray(availableSchemesList) || availableSchemesList.length === 0) {
    return {
      valid: false,
      error: 'CATALOG_UNAVAILABLE',
      message: 'Official scheme catalog is currently unavailable. Applications cannot be submitted without an authentic scheme.'
    };
  }

  // 2. Validate scheme ID is specified
  if (!selectedSchemeId || typeof selectedSchemeId !== 'string' || selectedSchemeId.trim() === '' || selectedSchemeId === 'auto') {
    return {
      valid: false,
      error: 'NO_SCHEME_SELECTED',
      message: 'Please select a valid government scheme from the catalog before submitting.'
    };
  }

  const cleanId = selectedSchemeId.trim();

  // 3. Reject known fabricated/stale legacy identifiers if they do not exist in the active catalog
  const matchingScheme = availableSchemesList.find(
    (s) => (s.id && s.id === cleanId) || (s.scheme_id && s.scheme_id === cleanId)
  );

  if (!matchingScheme) {
    return {
      valid: false,
      error: 'INVALID_OR_STALE_SCHEME',
      message: 'Selected scheme is invalid, outdated, or not found in the official catalog.'
    };
  }

  return {
    valid: true,
    matchingScheme
  };
}

/**
 * Resolves full scheme metadata using the direct API lookup,
 * falling back ONLY to the verified canonical record in availableSchemesList if network lookup fails.
 * Never fabricates scheme metadata or benefit amounts.
 *
 * @param {Object} matchingCatalogScheme
 * @param {Function} [fetchSchemeByIdFn]
 * @returns {Promise<Object|null>}
 */
export async function resolveCanonicalSchemeDetails(matchingCatalogScheme, fetchSchemeByIdFn) {
  if (!matchingCatalogScheme) return null;

  let targetScheme = null;

  if (typeof fetchSchemeByIdFn === 'function') {
    try {
      const fetchedScheme = await fetchSchemeByIdFn(matchingCatalogScheme.id || matchingCatalogScheme.scheme_id);
      if (fetchedScheme) {
        targetScheme = {
          id: fetchedScheme.id || matchingCatalogScheme.id,
          name: fetchedScheme.scheme_name || fetchedScheme.name || fetchedScheme.title || matchingCatalogScheme.name,
          ministry: fetchedScheme.department || fetchedScheme.ministry || fetchedScheme.source_authority || 'Government of India',
          benefit: fetchedScheme.benefit_summary || fetchedScheme.brief_description || (fetchedScheme.max_benefit ? `Up to ₹${Number(fetchedScheme.max_benefit).toLocaleString('en-IN')}` : (fetchedScheme.benefit_type || 'Benefit Details in Guidelines')),
          max_benefit: fetchedScheme.max_benefit || null,
          matchScore: 95,
          reason: fetchedScheme.eligibility_summary || `Selected statutory policy under ${fetchedScheme.department || fetchedScheme.ministry || 'Government of India'}.`
        };
      }
    } catch (lookupErr) {
      // Lookup error handled cleanly without crash
    }
  }

  // Fallback to verified catalog item itself
  if (!targetScheme && matchingCatalogScheme) {
    targetScheme = {
      id: matchingCatalogScheme.id || matchingCatalogScheme.scheme_id,
      name: matchingCatalogScheme.name || matchingCatalogScheme.scheme_name || matchingCatalogScheme.title || 'Government Scheme',
      ministry: matchingCatalogScheme.department || matchingCatalogScheme.ministry || matchingCatalogScheme.source_authority || 'Government of India',
      benefit: matchingCatalogScheme.benefit_summary || matchingCatalogScheme.brief_description || (matchingCatalogScheme.max_benefit ? `Up to ₹${Number(matchingCatalogScheme.max_benefit).toLocaleString('en-IN')}` : (matchingCatalogScheme.benefit_type || 'Benefit Details in Guidelines')),
      max_benefit: matchingCatalogScheme.max_benefit || null,
      matchScore: 95,
      reason: matchingCatalogScheme.eligibility_summary || `Selected statutory policy under ${matchingCatalogScheme.department || matchingCatalogScheme.ministry || 'Government of India'}.`
    };
  }

  return targetScheme;
}

/**
 * Checks whether a scheme is a Central/National scheme based on canonical metadata.
 * Strictly does NOT treat missing jurisdiction metadata as confirmed applicability.
 *
 * @param {Object} scheme
 * @returns {boolean}
 */
export function isCentralScheme(scheme) {
  if (!scheme) return false;
  const level = String(scheme.level || '').toLowerCase().trim();
  const state = String(scheme.state || '').toLowerCase().trim();

  // If level is explicitly 'State', it is definitely not Central
  if (level === 'state') return false;

  // Explicit Central / National level designation
  if (level === 'central' || level === 'national') return true;

  // Explicit pan-India state designations
  if (state && (state === 'all india' || state === 'central' || state === 'national' || state === 'pan india' || state === 'india')) {
    return true;
  }

  // Missing or uncertain jurisdiction metadata is strictly NOT assumed Central
  return false;
}

/**
 * Filters scheme catalog to those relevant to the logged-in applicant:
 * - Central schemes applicable across India (excluding territory-restricted central schemes)
 * - State schemes matching the applicant's state
 * - Strictly excludes unrelated other-state schemes
 * - Rejects unannotated/uncertain jurisdiction entries rather than assuming applicability
 *
 * @param {Array} schemesList
 * @param {string} applicantState
 * @returns {Array} Filtered schemes list
 */
export function filterApplicantRelevantSchemes(schemesList, applicantState) {
  if (!Array.isArray(schemesList)) return [];
  const cleanApplicantState = applicantState ? String(applicantState).toLowerCase().trim() : '';

  return schemesList.filter(s => {
    if (!s) return false;

    const schemeState = String(s.state || '').toLowerCase().trim();

    // 1. Direct state match for applicant's state (via state field or tags)
    if (cleanApplicantState) {
      if (schemeState === cleanApplicantState) return true;
      if (Array.isArray(s.tags) && s.tags.some(t => String(t).toLowerCase().trim() === cleanApplicantState)) {
        return true;
      }
    }

    // 2. Explicit other-state scheme is strictly excluded
    if (cleanApplicantState && schemeState && schemeState !== cleanApplicantState && schemeState !== 'all india' && schemeState !== 'central') {
      return false;
    }

    // 3. Central / National schemes:
    if (isCentralScheme(s)) {
      // Check if Central scheme is restricted to specific other territories
      const schemeName = String(s.name || s.scheme_name || s.title || '').toLowerCase();
      const specificOtherTerritories = [
        'jammu & kashmir', 'jammu and kashmir', 'ladakh', 'north eastern', 'northeast',
        'andaman and nicobar', 'puducherry', 'lakshadweep', 'chandigarh'
      ];
      if (cleanApplicantState) {
        const matchesOtherTerritory = specificOtherTerritories.some(t => schemeName.includes(t));
        if (matchesOtherTerritory && !schemeName.includes(cleanApplicantState)) {
          return false;
        }
      }
      return true;
    }

    // 4. Missing or uncertain jurisdiction is NOT assumed applicable
    return false;
  });
}

/**
 * Evaluates the status of a specific document requirement against the applicant's uploaded documents.
 * Returns a structured evaluation object:
 * { status, isVerified, isPending, isReviewRequired, isMissing, matchedDoc, notes }
 *
 * Strict Rules:
 * - OCR extraction does NOT count as Verified.
 * - Uploaded or under_review documents return 'Pending Verification'.
 * - Only genuine 'verified' status returns 'Verified'.
 *
 * @param {Object|string} reqItem - Requirement item ({ id, label } or string ID)
 * @param {Array} userDocuments - List of vault documents
 * @param {string|null} currentUserId - Active applicant ID for isolation
 * @returns {Object} Structured requirement status object
 */
export function evaluateRequirementStatus(reqItem, userDocuments = [], currentUserId = null) {
  if (!reqItem) {
    return {
      status: 'Missing',
      isVerified: false,
      isPending: false,
      isMissing: true,
      isReviewRequired: false,
      matchedDoc: null,
      notes: 'No requirement specified'
    };
  }

  const reqId = typeof reqItem === 'object' ? reqItem.id : reqItem;
  const reqLabel = typeof reqItem === 'object' ? reqItem.label : reqItem;

  if (!Array.isArray(userDocuments) || userDocuments.length === 0) {
    return {
      status: 'Missing',
      isVerified: false,
      isPending: false,
      isMissing: true,
      isReviewRequired: false,
      matchedDoc: null,
      notes: 'No documents in vault'
    };
  }

  // 1. Direct match by normalized ID / documentType
  const directDoc = userDocuments.find(d => {
    if (!d) return false;
    const ownerId = d.userId || d.user_id || d.applicantId || d.applicant_id || null;
    if (currentUserId && ownerId && String(ownerId) !== String(currentUserId)) {
      return false;
    }
    const dType = String(d.documentType || d.document_type || d.type || '').toLowerCase();
    const dId = String(d.id || '').toLowerCase();
    const dBackendId = String(d.backendId || '').toLowerCase();
    const cleanReqId = String(reqId || '').toLowerCase();
    return dType === cleanReqId || dId === cleanReqId || dBackendId === cleanReqId;
  });

  if (directDoc) {
    const rawStatus = String(directDoc.status || directDoc.verificationStatus || '').toLowerCase().trim();
    if (rawStatus === 'verified') {
      return {
        status: 'Verified',
        isVerified: true,
        isPending: false,
        isMissing: false,
        isReviewRequired: false,
        matchedDoc: directDoc,
        notes: 'Document statutory verification completed'
      };
    }
    if (['action_required', 'review_required', 'flagged', 'rejected', 'conflict'].includes(rawStatus)) {
      return {
        status: 'Review Required',
        isVerified: false,
        isPending: false,
        isMissing: false,
        isReviewRequired: true,
        matchedDoc: directDoc,
        notes: 'Document requires applicant review or re-upload'
      };
    }
    // Uploaded, under_review, pending, or ocr_extracted
    return {
      status: 'Pending Verification',
      isVerified: false,
      isPending: true,
      isMissing: false,
      isReviewRequired: false,
      matchedDoc: directDoc,
      notes: directDoc.extractedData ? 'OCR facts indexed. Pending statutory authority verification.' : 'Uploaded. Pending statutory authority verification.'
    };
  }

  // 2. Fuzzy / alias match using matchDocumentStatus
  const helperStatus = matchDocumentStatus(reqLabel, userDocuments, currentUserId);
  if (helperStatus === 'Verified') {
    const matched = userDocuments.find(d => String(d.status || d.verificationStatus || '').toLowerCase() === 'verified');
    return {
      status: 'Verified',
      isVerified: true,
      isPending: false,
      isMissing: false,
      isReviewRequired: false,
      matchedDoc: matched || null,
      notes: 'Document statutory verification completed'
    };
  }
  if (helperStatus === 'Review Required') {
    return {
      status: 'Review Required',
      isVerified: false,
      isPending: false,
      isMissing: false,
      isReviewRequired: true,
      matchedDoc: null,
      notes: 'Document requires review'
    };
  }
  if (helperStatus === 'Uploaded') {
    const matched = userDocuments.find(d => ['under_review', 'pending'].includes(String(d.status || d.verificationStatus || '').toLowerCase()));
    return {
      status: 'Pending Verification',
      isVerified: false,
      isPending: true,
      isMissing: false,
      isReviewRequired: false,
      matchedDoc: matched || null,
      notes: 'Uploaded. Pending statutory authority verification.'
    };
  }

  return {
    status: 'Missing',
    isVerified: false,
    isPending: false,
    isMissing: true,
    isReviewRequired: false,
    matchedDoc: null,
    notes: 'Document not found in vault'
  };
}

/**
 * Evaluates the full scheme document readiness for a given scheme.
 * Supports dynamic checklist items, raw catalog scheme objects, and neutral unselected states.
 *
 * @param {Object|null} scheme - Scheme from checklist or catalog
 * @param {Array} userDocuments - Vault documents
 * @param {string|null} currentUserId - Active applicant ID
 * @returns {Object} Readiness evaluation object
 */
export function evaluateSchemeReadiness(scheme, userDocuments = [], currentUserId = null) {
  if (!scheme) {
    return {
      status: 'NO_SCHEME_SELECTED',
      schemeId: null,
      schemeName: '',
      message: 'Select a scheme to check document readiness.',
      neutralMessage: 'Select a scheme to check document readiness.',
      requirements: [],
      isReady: false,
      isFullyReady: false,
      allVerified: false,
      canApply: false,
      verifiedCount: 0,
      missingCount: 0,
      pendingCount: 0,
      reviewCount: 0,
      totalCount: 0
    };
  }

  const schemeId = scheme.id || scheme.scheme_id || null;
  const schemeName = scheme.name || scheme.scheme_name || scheme.title || '';

  // Handle both dynamic checklist objects (with requiredDocIds) and raw catalog objects (with documents_required)
  let rawReqs = [];
  if (Array.isArray(scheme.requiredDocIds)) {
    rawReqs = scheme.requiredDocIds;
  } else if (Array.isArray(scheme.documents_required)) {
    rawReqs = scheme.documents_required.map(docName => ({
      id: normalizeDocRequirementId(docName),
      label: docName
    }));
  } else if (Array.isArray(scheme.documentsRequired)) {
    rawReqs = scheme.documentsRequired.map(docName => ({
      id: normalizeDocRequirementId(docName),
      label: docName
    }));
  }

  if (rawReqs.length === 0) {
    return {
      status: 'REQUIREMENTS_UNAVAILABLE',
      schemeId,
      schemeName,
      message: 'Requirements unavailable for this scheme in the official registry.',
      unavailableMessage: 'Requirements unavailable for this scheme in the official registry.',
      requirements: [],
      isReady: false,
      isFullyReady: false,
      allVerified: false,
      canApply: false,
      verifiedCount: 0,
      missingCount: 0,
      pendingCount: 0,
      reviewCount: 0,
      totalCount: 0
    };
  }

  const evaluatedRequirements = rawReqs.map(reqItem => {
    const rawId = typeof reqItem === 'object' ? reqItem.id : reqItem;
    const reqLabel = typeof reqItem === 'object' ? reqItem.label : rawId;
    const evalResult = evaluateRequirementStatus(reqItem, userDocuments, currentUserId);
    return {
      id: rawId,
      label: reqLabel,
      ...evalResult
    };
  });

  const verifiedCount = evaluatedRequirements.filter(r => r.status === 'Verified').length;
  const pendingCount = evaluatedRequirements.filter(r => r.status === 'Pending Verification').length;
  const reviewCount = evaluatedRequirements.filter(r => r.status === 'Review Required').length;
  const missingCount = evaluatedRequirements.filter(r => r.status === 'Missing').length;
  const totalCount = evaluatedRequirements.length;
  const allVerified = verifiedCount === totalCount && totalCount > 0;

  return {
    status: allVerified ? 'READY' : 'INCOMPLETE',
    schemeId,
    schemeName,
    allVerified,
    isReady: allVerified,
    isFullyReady: allVerified,
    canApply: allVerified,
    verifiedCount,
    pendingCount,
    reviewCount,
    missingCount,
    totalCount,
    requirements: evaluatedRequirements,
    summaryMessage: allVerified
      ? 'All required documents verified in vault.'
      : `${verifiedCount} of ${totalCount} documents verified.${pendingCount > 0 ? ` ${pendingCount} pending verification.` : ''}${missingCount > 0 ? ` ${missingCount} missing.` : ''}`,
    disclaimer: '* Document readiness indicates vault document availability only and does not guarantee government eligibility, sanction, qualification, or official scheme approval.'
  };
}

