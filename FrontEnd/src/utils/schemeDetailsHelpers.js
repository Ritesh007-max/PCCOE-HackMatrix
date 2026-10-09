/**
 * FIN Phase D3.4: Canonical Scheme Detail Sanitization Helpers
 * 
 * Strict Principle:
 * AI interprets → Rules decide → Evidence proves → Human reviews uncertainty.
 * Every displayed scheme-specific fact must originate from an identifiable canonical
 * data field, authoritative source, deterministic calculation, or authenticated applicant record.
 */

import {
  interpretFinancialBenefit,
  BenefitCategories,
  extractCalculatorParameters,
  cleanPolicyText,
  extractPolicyConditions,
  parseBenefitComponents,
  STANDALONE_HEADER_REGEX
} from './financialBenefitEngine.js';

export {
  interpretFinancialBenefit,
  BenefitCategories,
  extractCalculatorParameters,
  cleanPolicyText,
  extractPolicyConditions,
  parseBenefitComponents,
  STANDALONE_HEADER_REGEX
};

/**
 * Format number as Indian Currency (e.g. ₹1,75,000)
 */
export function formatCurrency(num) {
  if (num == null || isNaN(num)) return '₹0';
  return '₹' + Math.round(num).toLocaleString('en-IN');
}

// Strict authoritative Indian government domains and vetted official portals
export const TRUSTED_GOV_DOMAINS = [
  '.gov.in',
  '.nic.in',
  '.ac.in',
  '.res.in',
  'myscheme.gov.in',
  'www.myscheme.gov.in',
  'pmkisan.gov.in',
  'scholarships.gov.in',
  'digitalgujarat.gov.in',
  'swayam.gov.in',
  'epfindia.gov.in',
  'pmjay.gov.in'
];

// Untrusted domain patterns (blogs, commercial aggregators, search engines, ad portals)
export const UNTRUSTED_DOMAIN_PATTERNS = [
  'google.',
  'bing.',
  'yahoo.',
  'blogspot.',
  'wordpress.',
  'medium.com',
  'timesofindia.',
  'hindustantimes.',
  'ndtv.',
  'jagran.',
  'amarujala.',
  'cleartax.',
  'bankbazaar.',
  'policybazaar.',
  'sarkariyojana.',
  'yojana.com',
  'yojana.in'
];

/**
 * Validates a scheme official URL against authoritative government domain allowlists.
 * Strictly rejects non-http/https schemes (javascript:, data:), search engines,
 * blogs, commercial aggregators, and unverified third-party domains.
 */
export function validateOfficialUrl(url) {
  if (!url || typeof url !== 'string') return null;
  const clean = url.trim();
  if (!clean.startsWith('http://') && !clean.startsWith('https://')) return null;
  try {
    const parsed = new URL(clean);
    const host = (parsed.hostname || '').toLowerCase();
    if (!host) return null;

    // Reject untrusted patterns unless it is a genuine gov.in/nic.in domain
    for (const bad of UNTRUSTED_DOMAIN_PATTERNS) {
      if (host.includes(bad) && !host.endsWith('.gov.in') && !host.endsWith('.nic.in')) {
        return null;
      }
    }

    // Must match trusted government domain suffix or explicit trusted host
    const isTrusted = TRUSTED_GOV_DOMAINS.some(t => host === t || host.endsWith(t) || host === t.replace(/^\./, ''));
    if (isTrusted) {
      return clean;
    }
    return null;
  } catch (_) {
    return null;
  }
}

/**
 * Resolve dynamic official government portal, ministry, and helpline according to canonical scheme record.
 * 
 * Strict rule:
 * - Uses canonical `source_url` when present and validated.
 * - Does NOT replace a missing source URL with an unrelated government portal (e.g. india.gov.in).
 * - Separates source URL from application URL.
 */
export function getSchemePortalDetails(scheme) {
  if (!scheme) {
    return {
      ministry: 'Implementing Authority Not Specified',
      department: null,
      schemeType: 'Government Welfare Programme',
      targetBeneficiaries: 'Eligible Indian Citizens',
      coverage: 'Not Specified',
      officialWebsite: null,
      authorityPortalUrl: null,
      authorityPortalStatus: 'Official link not verified',
      informationSourceUrl: null,
      informationSourceName: null,
      applicationUrl: null,
      guidelinesUrl: null,
      helplineName: null,
      helplineNumber: null,
      helplineHours: null,
      guidelinesTitle: 'Official Guidelines'
    };
  }

  // 1. Implementing Ministry / Department
  const ministry = scheme.department || scheme.ministry || scheme.source_authority || scheme.sourceAuthority || 'Implementing Authority Not Specified';
  
  // 2. Scheme Type
  const schemeType = Array.isArray(scheme.categories) && scheme.categories.length > 0
    ? scheme.categories.join(', ')
    : (scheme.benefit_type || scheme.beneficiary_type || 'Government Welfare Programme');

  // 3. Target Beneficiaries
  const targetBeneficiaries = Array.isArray(scheme.target_beneficiaries) && scheme.target_beneficiaries.length > 0
    ? scheme.target_beneficiaries.join(', ')
    : (scheme.beneficiary_type || 'Eligible Applicants under Policy Norms');

  // 4. Coverage / Jurisdiction
  const coverage = scheme.state ? `${scheme.state} (${scheme.level || 'State'})` : (scheme.level || 'All India (Central)');

  // 5. Official Source URLs & Authority Portal Resolution
  const rawSourceUrl = scheme.source_url || scheme.official_url || null;
  const validatedSourceUrl = validateOfficialUrl(rawSourceUrl);

  const refs = Array.isArray(scheme.references) ? scheme.references : [];

  // Authority Portal: look for departmental or implementing authority domain
  let authorityPortalUrl = null;

  // Check explicit authority portal field if present
  const rawAuthUrl = scheme.authority_url || scheme.implementing_authority_url || scheme.portal_url || null;
  if (rawAuthUrl) {
    const val = validateOfficialUrl(rawAuthUrl);
    if (val && !val.includes('myscheme.gov.in')) {
      authorityPortalUrl = val;
    }
  }

  // Check references for official authority portal
  if (!authorityPortalUrl) {
    for (const ref of refs) {
      const u = typeof ref === 'string' ? ref : ref?.url;
      if (!u || typeof u !== 'string') continue;
      const lower = u.toLowerCase();
      // Skip PDFs and skip myscheme aggregator URLs
      if (lower.endsWith('.pdf') || lower.includes('/pdf/') || lower.includes('myscheme.gov.in')) continue;
      const val = validateOfficialUrl(u);
      if (val) {
        authorityPortalUrl = val;
        break;
      }
    }
  }

  // If source_url is NOT myscheme, it is an authoritative official domain
  if (!authorityPortalUrl && validatedSourceUrl && !validatedSourceUrl.includes('myscheme.gov.in')) {
    authorityPortalUrl = validatedSourceUrl;
  }

  // Information Source URL (e.g. myScheme repository or authoritative record)
  const informationSourceUrl = validatedSourceUrl;
  const informationSourceName = informationSourceUrl
    ? (informationSourceUrl.includes('myscheme.gov.in') ? 'myScheme National Portal (Information Repository)' : 'Official Scheme Repository')
    : null;

  // Application Portal
  let applicationUrl = null;
  const rawAppUrl = scheme.application_url || null;
  if (rawAppUrl) {
    applicationUrl = validateOfficialUrl(rawAppUrl);
  } else {
    // Check references for application/registration portal
    for (const ref of refs) {
      const u = typeof ref === 'string' ? ref : ref?.url;
      if (!u || typeof u !== 'string') continue;
      const lower = u.toLowerCase();
      if (lower.endsWith('.pdf') || lower.includes('/pdf/')) continue;
      if (lower.includes('apply') || lower.includes('registration') || lower.includes('login') || lower.includes('portal')) {
        const val = validateOfficialUrl(u);
        if (val) {
          applicationUrl = val;
          break;
        }
      }
    }
  }

  // Guidelines document URL
  let guidelinesUrl = null;

  // 1. Check explicit canonical guidelines/document fields on the scheme
  const explicitGuidelinesCandidates = [
    scheme.guidelines_url,
    scheme.guidelinesUrl,
    scheme.official_guidelines_url,
    scheme.document_url,
    scheme.pdf_url
  ].filter(Boolean);

  for (const candidate of explicitGuidelinesCandidates) {
    const val = validateOfficialUrl(candidate);
    if (val && !val.toLowerCase().includes('myscheme.gov.in')) {
      guidelinesUrl = val;
      break;
    }
  }

  // 2. If source_url directly points to a PDF on an authoritative domain
  if (!guidelinesUrl && validatedSourceUrl && (validatedSourceUrl.toLowerCase().endsWith('.pdf') || validatedSourceUrl.toLowerCase().includes('/pdf/'))) {
    guidelinesUrl = validatedSourceUrl;
  }

  // 3. Check canonical references for verified guidelines PDF or document
  if (!guidelinesUrl) {
    for (const ref of refs) {
      const u = typeof ref === 'string' ? ref : ref?.url;
      if (!u || typeof u !== 'string') continue;
      const lower = u.toLowerCase();
      // Skip generic portal or aggregator URLs
      if (lower.includes('myscheme.gov.in')) continue;
      if (lower.endsWith('.pdf') || lower.includes('/pdf/') || lower.includes('guideline') || lower.includes('guidance')) {
        const val = validateOfficialUrl(u);
        if (val) {
          guidelinesUrl = val;
          break;
        }
      }
    }
  }

  const isPdf = Boolean(
    guidelinesUrl && (
      guidelinesUrl.toLowerCase().endsWith('.pdf') ||
      guidelinesUrl.toLowerCase().includes('/pdf/') ||
      guidelinesUrl.toLowerCase().includes('.pdf?') ||
      guidelinesUrl.toLowerCase().includes('pdf')
    )
  );

  // Check if an official webpage or rules URL exists when no PDF exists
  let officialRulesPageUrl = null;
  if (!isPdf) {
    if (guidelinesUrl) {
      officialRulesPageUrl = guidelinesUrl;
    } else {
      for (const ref of refs) {
        const u = typeof ref === 'string' ? ref : ref?.url;
        if (!u || typeof u !== 'string') continue;
        const lower = u.toLowerCase();
        if (lower.includes('myscheme.gov.in')) continue;
        if (lower.includes('guideline') || lower.includes('rule') || lower.includes('scheme') || lower.includes('about')) {
          const val = validateOfficialUrl(u);
          if (val) {
            officialRulesPageUrl = val;
            break;
          }
        }
      }
    }
  }

  // officialWebsite: Authority portal preferred, otherwise validated source URL
  const officialWebsite = authorityPortalUrl || validatedSourceUrl || null;

  return {
    ministry,
    department: scheme.department || null,
    schemeType,
    targetBeneficiaries,
    coverage,
    officialWebsite,
    authorityPortalUrl,
    authorityPortalStatus: authorityPortalUrl ? 'Verified' : 'Official link not verified',
    informationSourceUrl,
    informationSourceName,
    applicationUrl,
    guidelinesUrl,
    isPdf,
    officialRulesPageUrl,
    guidelinesType: isPdf ? 'PDF' : (officialRulesPageUrl ? 'WEBPAGE' : 'UNAVAILABLE'),
    helplineName: scheme.helpline_name || null,
    helplineNumber: scheme.helpline_number || null,
    helplineHours: scheme.helpline_hours || null,
    guidelinesTitle: isPdf
      ? (scheme.title ? `${scheme.title} Scheme Guidelines (PDF)` : 'Official Scheme Guidelines (PDF)')
      : (officialRulesPageUrl
        ? (scheme.title ? `${scheme.title} Official Guidelines & Rules` : 'Official Guidelines & Rules')
        : 'Official Scheme Guidelines')
  };
}

/**
 * Decode common HTML entities from raw scraping or database fields.
 */
export function cleanHtmlEntities(text) {
  if (!text || typeof text !== 'string') return '';
  return text
    .replace(/&amp;/g, '&')
    .replace(/&nbsp;/g, ' ')
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&ndash;/g, '–')
    .replace(/&mdash;/g, '—');
}

/**
 * Clean markdown artifacts, bullet symbols, backslash escapes, and redundant whitespace.
 */
export function normalizeContentText(text) {
  if (!text || typeof text !== 'string') return '';
  return cleanPolicyText(text);
}

/**
 * Universal clause list normalizer:
 * Splits by delimiter (pipe, semicolon, newline), strips leading bullets, numbers, hyphens,
 * cleans HTML entities and markdown artifacts, filters standalone headers, and deduplicates identical clauses.
 */
export function normalizeClauseList(rawInput, delimiters = /[|;\n]+/g) {
  if (!rawInput) return [];
  let items = [];
  if (Array.isArray(rawInput)) {
    items = rawInput.map(x => String(x || ''));
  } else if (typeof rawInput === 'string') {
    const unescaped = cleanPolicyText(rawInput);
    items = unescaped.split(delimiters);
  } else {
    return [];
  }

  const seen = new Set();
  const result = [];

  for (let item of items) {
    if (!item) continue;
    let clean = cleanPolicyText(item);
    // Strip leading list bullets, numbers, hyphens, asterisks, hashtags, pipes
    clean = clean.replace(/^[\s\-_*•·▪—–#>|]+/, '');
    clean = clean.replace(/^(\d+|[a-zA-Z])[\.\)]\s+/, '');
    // Strip trailing semicolon, commas, hyphens, slash-hyphen, and trailing periods
    clean = clean.replace(/[\s\-_*•·▪—–;,\.\/#>|]+$/, '');
    clean = clean.trim();

    if (!clean || clean.length < 2) continue;

    // Filter out standalone section headers (e.g. "Conditions", "Important Notes", etc.)
    if (STANDALONE_HEADER_REGEX.test(clean)) continue;

    // Deduplicate identical clauses (case-insensitive) while preserving original text
    const lowerKey = clean.toLowerCase();
    if (!seen.has(lowerKey)) {
      seen.add(lowerKey);
      result.push(clean);
    }
  }

  return result;
}

/**
 * Parse canonical documents_required into an array of normalized document items.
 * Supports semicolon-separated strings, newline lists, and array formats.
 */
export function parseRequiredDocuments(scheme) {
  const raw = scheme?.documents_required || scheme?.required_documents;
  return normalizeClauseList(raw, /[;\n|]+/g);
}

/**
 * Determine document status by matching against authenticated user's uploaded documents.
 * 
 * Distinct statuses:
 * - Verified: a matching document has genuinely passed the system's verification process.
 * - Uploaded: a matching document exists but verification is pending (even if OCR-extracted).
 * - Review Required: verification is pending manual review, flagged, or ambiguous.
 * - Missing: no matching document exists.
 * 
 * Strict Rules:
 * - OCR extraction alone must NEVER imply verification.
 * - Do not mark income certificate Verified merely because it was uploaded or OCR-extracted.
 * - Enforces tenant isolation if currentUserId is supplied.
 */
export function matchDocumentStatus(docName, userDocs = [], currentUserId = null) {
  if (!Array.isArray(userDocs) || userDocs.length === 0) {
    return 'Missing';
  }

  const rawTarget = String(docName || '').toLowerCase().trim();
  const cleanTarget = rawTarget.replace(/[^a-z0-9]/g, '');

  const match = userDocs.find(ud => {
    if (!ud || typeof ud !== 'object') return false;

    // Tenant isolation: if currentUserId is provided and document has an owner, verify ownership
    const ownerId = ud.userId || ud.user_id || ud.applicantId || ud.applicant_id || null;
    if (currentUserId && ownerId && String(ownerId) !== String(currentUserId)) {
      return false;
    }

    const udType = String(ud.documentType || ud.document_type || ud.type || '').toLowerCase().trim();
    const cleanType = udType.replace(/[^a-z0-9]/g, '');

    const udFileName = String(ud.fileName || ud.file_name || ud.original_name || ud.name || '').toLowerCase().trim();
    const cleanFileName = udFileName.replace(/[^a-z0-9]/g, '');

    const udTitle = String(ud.title || ud.documentName || ud.document_name || '').toLowerCase().trim();
    const cleanTitle = udTitle.replace(/[^a-z0-9]/g, '');

    // 1. Aadhaar Card
    const isAadhaarTarget = cleanTarget.includes('aadhaar') || cleanTarget.includes('aadhar') || cleanTarget.includes('adhaar') || cleanTarget.includes('uidai');
    if (isAadhaarTarget) {
      if (cleanType.includes('aadhaar') || cleanType.includes('aadhar') || cleanType === 'uidai' || cleanType === 'id') return true;
      if (cleanFileName.includes('aadhaar') || cleanFileName.includes('aadhar') || cleanFileName.includes('adhaar')) return true;
      if (cleanTitle.includes('aadhaar') || cleanTitle.includes('aadhar')) return true;
    }

    // 2. PAN (Permanent Account Number)
    const isPanTarget = cleanTarget.includes('permanentaccountnumber') || cleanTarget.includes('pancard') || /(^|[^a-z])pan([^a-z]|$)/.test(rawTarget);
    if (isPanTarget) {
      if (cleanType === 'pan' || cleanType === 'pancard') return true;
      if (cleanFileName.includes('pan') || cleanTitle.includes('pan')) return true;
    }

    // 3. Income Certificate
    const isIncomeTarget = cleanTarget.includes('income') || cleanTarget.includes('salary') || cleanTarget.includes('aavak') || cleanTarget.includes('aay');
    if (isIncomeTarget) {
      if (cleanType.includes('income') || cleanType === 'salaryslip' || cleanType === 'form16') return true;
      if (cleanFileName.includes('income') || cleanFileName.includes('salary') || cleanFileName.includes('form16') || cleanFileName.includes('aavak')) return true;
      if (cleanTitle.includes('income') || cleanTitle.includes('salary')) return true;
    }

    // 4. Caste Certificate
    const isCasteTarget = cleanTarget.includes('caste') || cleanTarget.includes('category') || cleanTarget.includes('jati') || cleanTarget.includes('tribe');
    if (isCasteTarget) {
      if (cleanType.includes('caste') || cleanType.includes('jati')) return true;
      if (cleanFileName.includes('caste') || cleanFileName.includes('jati')) return true;
      if (cleanTitle.includes('caste')) return true;
    }

    // 5. Bank Passbook / Bank Details
    const isBankTarget = cleanTarget.includes('passbook') || cleanTarget.includes('bankaccount') || cleanTarget.includes('bankstatement') || cleanTarget.includes('cancelledcheque');
    if (isBankTarget) {
      if (cleanType.includes('bank') || cleanType.includes('passbook')) return true;
      if (cleanFileName.includes('passbook') || cleanFileName.includes('bank') || cleanFileName.includes('cheque')) return true;
      if (cleanTitle.includes('passbook') || cleanTitle.includes('bank')) return true;
    }

    // 6. Land Records
    const isLandTarget = cleanTarget.includes('land') || cleanTarget.includes('712') || cleanTarget.includes('ror') || cleanTarget.includes('khatauni');
    if (isLandTarget) {
      if (cleanType.includes('land') || cleanType.includes('712')) return true;
      if (cleanFileName.includes('land') || cleanFileName.includes('712') || cleanFileName.includes('ror')) return true;
    }

    // 7. Photograph
    const isPhotoTarget = cleanTarget.includes('photograph') || cleanTarget.includes('photo') || cleanTarget.includes('picture');
    if (isPhotoTarget) {
      if (cleanType.includes('photo') || cleanType.includes('pic')) return true;
      if (cleanFileName.includes('photo') || cleanFileName.includes('pic') || cleanFileName.includes('passport')) return true;
    }

    // 8. Rent Agreement / Lease / Tenancy
    const isRentTarget = cleanTarget.includes('rent') || cleanTarget.includes('lease') || cleanTarget.includes('tenant') || cleanTarget.includes('tenancy') || cleanTarget.includes('landlord');
    if (isRentTarget) {
      if (cleanType.includes('rent') || cleanType.includes('lease') || cleanType.includes('tenan')) return true;
      if (cleanFileName.includes('rent') || cleanFileName.includes('lease') || cleanFileName.includes('agreement')) return true;
    }

    // 9. Power of Attorney
    const isPoaTarget = cleanTarget.includes('powerofattorney') || cleanTarget.includes('attorney') || cleanTarget.includes('poa');
    if (isPoaTarget) {
      if (cleanType.includes('attorney') || cleanType === 'poa') return true;
      if (cleanFileName.includes('attorney') || cleanFileName.includes('poa')) return true;
    }

    // 10. Tax Bill
    const isTaxTarget = cleanTarget.includes('taxbill') || cleanTarget.includes('taxreceipt') || (cleanTarget.includes('tax') && cleanTarget.includes('bill'));
    if (isTaxTarget) {
      if (cleanType.includes('tax')) return true;
      if (cleanFileName.includes('tax')) return true;
    }

    // 11. Death Certificate
    const isDeathTarget = cleanTarget.includes('deathcertificate') || cleanTarget.includes('death');
    if (isDeathTarget) {
      if (cleanType.includes('death')) return true;
      if (cleanFileName.includes('death')) return true;
    }

    // 12. Generic / direct name match
    if (cleanType && cleanTarget.includes(cleanType)) return true;
    if (cleanFileName && (cleanTarget.includes(cleanFileName) || cleanFileName.includes(cleanTarget))) return true;
    if (cleanTitle && (cleanTarget.includes(cleanTitle) || cleanTitle.includes(cleanTarget))) return true;

    return false;
  });

  if (!match) return 'Missing';

  const rawStatus = String(match.verificationStatus || match.verification_status || match.status || '').toLowerCase().trim();

  if (rawStatus === 'verified') {
    return 'Verified';
  }
  if (rawStatus === 'review_required' || rawStatus === 'review' || rawStatus === 'flagged' || rawStatus === 'conflict' || rawStatus === 'rejected') {
    return 'Review Required';
  }
  // Pending, newly uploaded, or in-progress files remain 'Uploaded' (even if OCR extracted)
  return 'Uploaded';
}

/**
 * Parse canonical application_process into structured steps without fabricating SLAs or durations.
 */
export function parseApplicationProcess(rawProcess) {
  if (!rawProcess || typeof rawProcess !== 'string' || !rawProcess.trim()) return [];

  const rawItems = rawProcess.split(/[|\n]+/);
  const cleanItems = [];

  let inContactSection = false;

  for (let item of rawItems) {
    let clean = cleanPolicyText(item);
    clean = clean.replace(/^[\s\-_*•·▪—–#>|]+/, '');
    clean = clean.replace(/[\s\-_*•·▪—–;,\.\/#>|]+$/, '');
    clean = clean.trim();
    if (!clean || clean.length < 2) continue;

    const lower = clean.toLowerCase();

    // 1. Detect start of contact details section
    if (lower.startsWith('contact details') || lower.startsWith('for further details') || lower.startsWith('helpline:') || lower.startsWith('e-mail:') || lower.startsWith('telephone:')) {
      inContactSection = true;
      continue;
    }
    if (inContactSection) {
      continue;
    }

    // 2. Filter out scoring rubric criteria definitions
    if (/^[0-5]\s*:\s*(fails|poor|fair|good|very good|excellent)/i.test(clean)) {
      continue;
    }
    if (/^score\s*points/i.test(clean) || lower.includes('contains 7 criteria') || lower.includes('scores from 5 to 0')) {
      continue;
    }

    // 3. Filter out standalone section headers or labels
    if (/^(selection procedure|procedure|how to apply|application procedure)\s*:?$/i.test(clean)) {
      continue;
    }

    cleanItems.push(clean);
  }

  const result = [];
  let currentStage = null;
  let stepCounter = 1;

  for (let item of cleanItems) {
    // Check if item is a Stage header
    const stageMatch = item.match(/^Stage\s*(\d+)[:\.\-]?\s*(.*)/i);
    if (stageMatch) {
      currentStage = stageMatch[2].trim() || ('Stage ' + stageMatch[1]);
      continue;
    }

    // Check if item is a Step
    const stepMatch = item.match(/^Step\s*(\d+)[:\.\-]?\s*(.*)/i);
    if (stepMatch) {
      const rest = stepMatch[2].trim();
      const sepMatch = rest.match(/^([^:\-\.]{3,60})[:\-\.]\s+(.+)$/);
      let title = '';
      let desc = '';

      if (sepMatch) {
        title = sepMatch[1].trim();
        desc = sepMatch[2].trim();
      } else if (rest.length > 0 && rest.length <= 60) {
        title = rest;
        desc = rest;
      } else {
        title = currentStage ? currentStage : ('Step ' + stepCounter);
        desc = rest;
      }

      if (currentStage && !title.toLowerCase().includes(currentStage.toLowerCase())) {
        title = currentStage + ': ' + title;
      }

      result.push({
        step: String(stepCounter++),
        title,
        desc
      });
      continue;
    }

    // Standalone note or instruction
    if (/^note\s*\d*[:\.\-]/i.test(item)) {
      result.push({
        step: String(stepCounter++),
        title: 'Submission Prerequisite Note',
        desc: item.replace(/^note\s*\d*[:\.\-]\s*/i, '').trim()
      });
      continue;
    }

    // General step or procedure line
    if (item.length >= 10 && !item.toLowerCase().startsWith('contact')) {
      const title = currentStage ? currentStage : ('Step ' + stepCounter);
      result.push({
        step: String(stepCounter++),
        title,
        desc: item
      });
    }
  }

  return result;
}

/**
 * Universal criteria parser:
 * Normalizes eligibility criteria text into structured list of policy conditions.
 */
export function parseEligibilityCriteria(scheme) {
  if (!scheme) return [];
  const raw = scheme.criteria || scheme.eligibility_criteria || scheme.eligibility || scheme.eligibilitySummary;
  return normalizeClauseList(raw, /[;\n|]+/g);
}

/**
 * Universal benefits breakdown parser:
 * Breaks down canonical benefit text into distinct normalized clauses.
 */
export function parseSchemeBenefits(scheme) {
  if (!scheme) return [];
  const raw = scheme.benefits || scheme.financial_assistance || scheme.benefitSummary;
  return normalizeClauseList(raw, /[|\n]+/g);
}

/**
 * Determine if scheme supports a genuine credit-linked loan calculator.
 * 
 * Strict condition:
 * Only schemes where canonical data explicitly identifies credit-linked model
 * or loan/subsidy parameters should display the interactive calculator.
 */
export function isLoanSchemeWithCalculator(scheme) {
  if (!scheme) return false;
  return interpretFinancialBenefit(scheme).hasLoanCalculator;
}

/**
 * Map raw scheme record to standard normalized scheme details.
 * Prevents default fallback values (e.g. ₹1,25,000) from leaking into output.
 */
/**
 * Helper to parse a date string in Indian Standard Time (IST, UTC+05:30).
 * Date boundaries:
 * - Start of day: YYYY-MM-DDT00:00:00.000+05:30
 * - End of day: YYYY-MM-DDT23:59:59.999+05:30
 */
export function parseDateInIST(dateInput, isEndOfDay = false) {
  if (!dateInput) return null;
  if (typeof dateInput !== 'string') {
    if (dateInput instanceof Date && !isNaN(dateInput.getTime())) {
      return dateInput;
    }
    return null;
  }
  const clean = dateInput.trim();
  if (clean === 'NaN' || clean === 'null' || clean === 'undefined' || !clean) return null;

  const match = clean.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return null;

  const [_, year, month, day] = match;
  const timePart = isEndOfDay ? '23:59:59.999' : '00:00:00.000';
  const isoStr = `${year}-${month}-${day}T${timePart}+05:30`;
  const parsed = new Date(isoStr);
  return isNaN(parsed.getTime()) ? null : parsed;
}

/**
 * Format a YYYY-MM-DD date into Indian human readable date (e.g. 31 Mar 2027)
 */
export function formatDisplayDate(dateInput) {
  if (!dateInput) return null;
  if (typeof dateInput !== 'string') return null;
  const clean = dateInput.trim();
  const match = clean.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return clean;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const [_, y, m, d] = match;
  const monthIdx = parseInt(m, 10) - 1;
  const monthName = months[monthIdx] || m;
  return `${parseInt(d, 10)} ${monthName} ${y}`;
}

/**
 * FIN Phase D3.7: Dynamic Scheme Application Cycle & Status Resolution
 * 
 * Computes deterministic application cycle status from canonical dates or explicit verified metadata.
 * Strictly respects IST (UTC+05:30) date boundaries.
 * 
 * Supported States:
 * - OPEN: Current date is within [open_date, close_date], or before close_date.
 * - UPCOMING: Current date is before open_date.
 * - CLOSED: Current date is after close_date.
 * - ONGOING: open_date is in past, and no close_date is specified.
 * - NOT_SPECIFIED: No reliable dates or verified status provided.
 * 
 * Strictly prohibits hardcoding financial years (e.g. FY 2025-26) or default "Ongoing" fallbacks.
 */
export function getSchemeApplicationCycle(scheme, referenceDate = null) {
  if (!scheme || typeof scheme !== 'object') {
    return {
      status: 'NOT_SPECIFIED',
      label: 'Status Not Specified',
      detailedStatus: 'Status Not Specified',
      badgeText: 'Status Not Specified',
      badgeClass: 'unspecified',
      isLive: false,
      openDate: null,
      closeDate: null,
      formattedOpenDate: null,
      formattedCloseDate: null,
      daysRemaining: null,
      cycleDescription: 'Application cycle dates are not specified in the official scheme record.'
    };
  }

  // 1. Resolve raw date strings
  const rawOpen = scheme.scheme_open_date || scheme.open_date || null;
  const rawClose = scheme.scheme_close_date || scheme.close_date || null;

  // Clean strings (reject "NaN", "null", etc.)
  const cleanOpen = typeof rawOpen === 'string' && rawOpen.trim() && rawOpen.trim() !== 'NaN' && rawOpen.trim() !== 'null' ? rawOpen.trim().slice(0, 10) : null;
  const cleanClose = typeof rawClose === 'string' && rawClose.trim() && rawClose.trim() !== 'NaN' && rawClose.trim() !== 'null' ? rawClose.trim().slice(0, 10) : null;

  const openDateIST = cleanOpen ? parseDateInIST(cleanOpen, false) : null;
  const closeDateIST = cleanClose ? parseDateInIST(cleanClose, true) : null;

  // 2. Reference timestamp in IST (default: now)
  const nowMs = referenceDate ? new Date(referenceDate).getTime() : Date.now();

  const formattedOpen = cleanOpen ? formatDisplayDate(cleanOpen) : null;
  const formattedClose = cleanClose ? formatDisplayDate(cleanClose) : null;

  let daysRemaining = null;
  if (closeDateIST && closeDateIST.getTime() >= nowMs) {
    daysRemaining = Math.max(0, Math.ceil((closeDateIST.getTime() - nowMs) / (1000 * 60 * 60 * 24)));
  }

  // Case 1: Both Open and Close dates available
  if (openDateIST && closeDateIST) {
    if (nowMs < openDateIST.getTime()) {
      return {
        status: 'UPCOMING',
        label: 'Upcoming Applications',
        detailedStatus: `Upcoming (Opens ${formattedOpen})`,
        badgeText: `Upcoming (Opens ${formattedOpen})`,
        badgeClass: 'upcoming',
        isLive: false,
        openDate: cleanOpen,
        closeDate: cleanClose,
        formattedOpenDate: formattedOpen,
        formattedCloseDate: formattedClose,
        daysRemaining: null,
        cycleDescription: `Applications will open on ${formattedOpen} and close on ${formattedClose}.`
      };
    }
    if (nowMs > closeDateIST.getTime()) {
      return {
        status: 'CLOSED',
        label: 'Applications Closed',
        detailedStatus: `Closed on ${formattedClose}`,
        badgeText: 'Applications Closed',
        badgeClass: 'closed',
        isLive: false,
        openDate: cleanOpen,
        closeDate: cleanClose,
        formattedOpenDate: formattedOpen,
        formattedCloseDate: formattedClose,
        daysRemaining: 0,
        cycleDescription: `Applications for this cycle closed on ${formattedClose}.`
      };
    }
    return {
      status: 'OPEN',
      label: 'Applications Open',
      detailedStatus: `Open (Deadline: ${formattedClose})`,
      badgeText: `Applications Open (Deadline: ${formattedClose})`,
      badgeClass: 'open',
      isLive: true,
      openDate: cleanOpen,
      closeDate: cleanClose,
      formattedOpenDate: formattedOpen,
      formattedCloseDate: formattedClose,
      daysRemaining,
      cycleDescription: `Applications are currently open until ${formattedClose}.`
    };
  }

  // Case 2: Only Close date available
  if (!openDateIST && closeDateIST) {
    if (nowMs > closeDateIST.getTime()) {
      return {
        status: 'CLOSED',
        label: 'Applications Closed',
        detailedStatus: `Closed on ${formattedClose}`,
        badgeText: 'Applications Closed',
        badgeClass: 'closed',
        isLive: false,
        openDate: null,
        closeDate: cleanClose,
        formattedOpenDate: null,
        formattedCloseDate: formattedClose,
        daysRemaining: 0,
        cycleDescription: `Applications for this cycle closed on ${formattedClose}.`
      };
    }
    return {
      status: 'OPEN',
      label: 'Applications Open',
      detailedStatus: `Open (Deadline: ${formattedClose})`,
      badgeText: `Applications Open (Deadline: ${formattedClose})`,
      badgeClass: 'open',
      isLive: true,
      openDate: null,
      closeDate: cleanClose,
      formattedOpenDate: null,
      formattedCloseDate: formattedClose,
      daysRemaining,
      cycleDescription: `Applications are currently open until ${formattedClose}.`
    };
  }

  // Case 3: Only Open date available
  if (openDateIST && !closeDateIST) {
    if (nowMs < openDateIST.getTime()) {
      return {
        status: 'UPCOMING',
        label: 'Upcoming Applications',
        detailedStatus: `Upcoming (Opens ${formattedOpen})`,
        badgeText: `Upcoming (Opens ${formattedOpen})`,
        badgeClass: 'upcoming',
        isLive: false,
        openDate: cleanOpen,
        closeDate: null,
        formattedOpenDate: formattedOpen,
        formattedCloseDate: null,
        daysRemaining: null,
        cycleDescription: `Applications will open on ${formattedOpen}.`
      };
    }
    return {
      status: 'ONGOING',
      label: 'Ongoing Applications',
      detailedStatus: `Ongoing (Since ${formattedOpen})`,
      badgeText: 'Ongoing Applications',
      badgeClass: 'ongoing',
      isLive: true,
      openDate: cleanOpen,
      closeDate: null,
      formattedOpenDate: formattedOpen,
      formattedCloseDate: null,
      daysRemaining: null,
      cycleDescription: `Applications accepted on rolling basis since ${formattedOpen}.`
    };
  }

  // Case 4: Neither date available — Check explicit verified status metadata if present
  const explicitStatus = String(scheme.application_status || scheme.cycle_status || scheme.status || '').toUpperCase().trim();
  if (explicitStatus === 'CLOSED') {
    return {
      status: 'CLOSED',
      label: 'Applications Closed',
      detailedStatus: 'Applications Closed',
      badgeText: 'Applications Closed',
      badgeClass: 'closed',
      isLive: false,
      openDate: null,
      closeDate: null,
      formattedOpenDate: null,
      formattedCloseDate: null,
      daysRemaining: null,
      cycleDescription: 'Applications are marked closed in official scheme metadata.'
    };
  }
  if (explicitStatus === 'UPCOMING') {
    return {
      status: 'UPCOMING',
      label: 'Upcoming Applications',
      detailedStatus: 'Upcoming Applications',
      badgeText: 'Upcoming Applications',
      badgeClass: 'upcoming',
      isLive: false,
      openDate: null,
      closeDate: null,
      formattedOpenDate: null,
      formattedCloseDate: null,
      daysRemaining: null,
      cycleDescription: 'Upcoming application cycle announced.'
    };
  }
  if (explicitStatus === 'ONGOING') {
    return {
      status: 'ONGOING',
      label: 'Ongoing Applications',
      detailedStatus: 'Ongoing Applications',
      badgeText: 'Ongoing Applications',
      badgeClass: 'ongoing',
      isLive: true,
      openDate: null,
      closeDate: null,
      formattedOpenDate: null,
      formattedCloseDate: null,
      daysRemaining: null,
      cycleDescription: 'Applications accepted on continuous rolling basis.'
    };
  }
  if (explicitStatus === 'OPEN') {
    return {
      status: 'OPEN',
      label: 'Applications Open',
      detailedStatus: 'Applications Open',
      badgeText: 'Applications Open',
      badgeClass: 'open',
      isLive: true,
      openDate: null,
      closeDate: null,
      formattedOpenDate: null,
      formattedCloseDate: null,
      daysRemaining: null,
      cycleDescription: 'Applications are currently open.'
    };
  }

  // Default: Status Not Specified (Honest Unavailable State)
  return {
    status: 'NOT_SPECIFIED',
    label: 'Status Not Specified',
    detailedStatus: 'Status Not Specified',
    badgeText: 'Status Not Specified',
    badgeClass: 'unspecified',
    isLive: false,
    openDate: null,
    closeDate: null,
    formattedOpenDate: null,
    formattedCloseDate: null,
    daysRemaining: null,
    cycleDescription: 'Application cycle dates are not specified in the official scheme record.'
  };
}

/**
 * Map raw scheme record to standard normalized scheme details.
 * Prevents default fallback values (e.g. ₹1,25,000) from leaking into output.
 */
export function adaptSchemeDetails(raw) {
  if (!raw) return null;
  const id = raw.id || raw.slug || '';
  const slug = raw.slug || raw.id || '';
  const title = raw.scheme_name || raw.name || raw.title || 'Government Scheme';
  const subtitle = raw.department || raw.ministry || raw.sourceAuthority || 'Government of India';
  const description = raw.detailed_description || raw.brief_description || raw.benefit_summary || raw.description || 'Official Government welfare initiative';
  const briefDescription = raw.brief_description || '';
  const detailedDescription = raw.detailed_description || raw.description || '';
  const applicationProcess = raw.application_process || '';
  const rawSourceUrl = raw.source_url || raw.official_url || null;
  const sourceUrl = validateOfficialUrl(rawSourceUrl);
  const faqCount = raw.faq_count != null ? Number(raw.faq_count) : 0;
  const eligibilitySummary = raw.eligibility_summary || (typeof raw.eligibility === 'string' ? raw.eligibility : '') || '';
  const benefitSummary = raw.benefit_summary || (typeof raw.benefits === 'string' ? raw.benefits : '') || '';
  const maxBenefit = raw.max_benefit != null ? Number(raw.max_benefit) : null;
  const benefitAmount = raw.benefit_amount || null;
  const tagsFromRaw = Array.isArray(raw.tags) && raw.tags.length > 0 ? raw.tags : null;
  const state = raw.state || (tagsFromRaw && tagsFromRaw.find(t => ['Gujarat', 'Maharashtra', 'Karnataka', 'Tamil Nadu', 'Kerala', 'Uttar Pradesh', 'Rajasthan', 'Delhi', 'Punjab', 'Haryana', 'Madhya Pradesh', 'Bihar', 'West Bengal', 'Odisha', 'Assam'].includes(t))) || 'All India';
  const level = raw.level || (state && state !== 'All India' ? 'State' : 'Central');
  const tags = tagsFromRaw || [state !== 'All India' ? state : null, `${level} Scheme`].filter(Boolean);
  const matchScore = raw.matchScore != null ? raw.matchScore : null;
  const relevanceScore = raw.relevanceScore != null ? (raw.relevanceScore > 1 ? Math.round(raw.relevanceScore) : Math.round(raw.relevanceScore * 100)) : null;

  const cleanOpenDate = (raw.scheme_open_date && String(raw.scheme_open_date).trim() !== 'NaN') ? String(raw.scheme_open_date).trim() : (raw.open_date && String(raw.open_date).trim() !== 'NaN') ? String(raw.open_date).trim() : null;
  const cleanCloseDate = (raw.scheme_close_date && String(raw.scheme_close_date).trim() !== 'NaN') ? String(raw.scheme_close_date).trim() : (raw.close_date && String(raw.close_date).trim() !== 'NaN') ? String(raw.close_date).trim() : null;

  const cycle = getSchemeApplicationCycle({
    ...raw,
    scheme_open_date: cleanOpenDate,
    scheme_close_date: cleanCloseDate
  });

  return {
    id,
    slug,
    title,
    subtitle,
    description,
    brief_description: briefDescription,
    detailed_description: detailedDescription,
    application_process: applicationProcess,
    source_url: sourceUrl,
    faq_count: faqCount,
    eligibilitySummary,
    benefitSummary,
    maxBenefit,
    benefitAmount,
    tags,
    state,
    level,
    dbt_scheme: raw.dbt_scheme === true,
    documents_required: raw.documents_required || raw.required_documents || null,
    criteria: raw.criteria || raw.eligibility_criteria || null,
    benefits: raw.benefits || null,
    benefit_type: raw.benefit_type || raw.benefitType || null,
    is_loan_scheme: raw.is_loan_scheme === true || raw.benefit_type === 'Credit Linked Subsidy',
    matchScore,
    relevanceScore,
    slogan: raw.slogan || raw.tagline || null,
    scheme_open_date: cleanOpenDate,
    scheme_close_date: cleanCloseDate,
    application_cycle: cycle,
    details: raw.details || null,
    calculator_parameters: raw.calculator_parameters || raw.calculatorParameters || (raw.details?.calculator_parameters) || null,
    calculatorParameters: raw.calculator_parameters || raw.calculatorParameters || (raw.details?.calculator_parameters) || null,
    categories: raw.categories || null,
    sub_categories: raw.sub_categories || null,
    category: raw.category || null,
    sub_category: raw.sub_category || null,
    department: raw.department || null,
    ministry: raw.ministry || null,
    scheme_name: raw.scheme_name || raw.title || raw.name || title,
    is_non_financial: raw.is_non_financial != null ? Boolean(raw.is_non_financial) : null,
    is_credit_linked: raw.is_credit_linked === true || raw.benefit_type === 'Credit Linked Subsidy',
    references: raw.references || null,
    application_url: raw.application_url || null,
    authority_url: raw.authority_url || null,
    guidelines_url: raw.guidelines_url || raw.guidelinesUrl || null,
    guidelinesUrl: raw.guidelines_url || raw.guidelinesUrl || null,
    official_guidelines_url: raw.official_guidelines_url || null,
    document_url: raw.document_url || null,
    pdf_url: raw.pdf_url || null
  };
}

/**
 * Resolve an authoritative, non-fabricated benefit classification label.
 * Fully data-driven via interpretFinancialBenefit; zero scheme-name special cases.
 */
export function resolveBenefitClassification(scheme) {
  if (!scheme) return 'Benefit Type Not Specified';
  return interpretFinancialBenefit(scheme).benefitType;
}

/**
 * Resolves authoritative amount text and subtitles for scheme details cards and views.
 * Prevents unsupported scalar amounts (e.g. monthly fellowships) from being
 * displayed as total lump-sum entitlements, and prevents generic fallbacks.
 * Fully data-driven via interpretFinancialBenefit; zero scheme-name special cases.
 */
export function getSchemeBenefitDisplay(scheme) {
  const interp = interpretFinancialBenefit(scheme);
  return {
    amountDisplay: interp.amountDisplay,
    subtitle: interp.subtitle,
    classification: interp.benefitType,
    entitlementText: interp.entitlementText,
    isScalarTotal: interp.isScalarTotal,
    isScalarCashGrant: interp.isScalarCashGrant,
    category: interp.category,
    hasLoanCalculator: interp.hasLoanCalculator,
    calculatorParameters: interp.calculatorParameters || null,
    benefitComponents: interp.benefitComponents || [],
    conditions: interp.conditions || []
  };
}

/**
 * Detects whether a string is an internal engine token/sentinel
 * rather than a genuine applicant data requirement.
 */
export function isInternalSentinel(field) {
  if (typeof field !== 'string') return true;
  const lower = field.toLowerCase().trim();
  return lower.includes('not_registered') ||
         lower.startsWith('scheme_') ||
         lower.endsWith('_error') ||
         lower === 'rule_evaluation_error' ||
         lower === 'unknown';
}

/**
 * Maps profile field key to human-readable applicant profile label.
 */
export function formatProfileFieldLabel(field) {
  if (!field || typeof field !== 'string') return '';
  const clean = field.toLowerCase().trim();
  const KNOWN_LABELS = {
    date_of_birth: 'Date of Birth',
    dob: 'Date of Birth',
    age: 'Age / Date of Birth',
    annual_income: 'Annual Family Income',
    income: 'Annual Family Income',
    occupation: 'Occupation',
    caste_category: 'Social Category',
    category: 'Social Category',
    gender: 'Gender',
    state: 'State of Residence',
    land_ownership_acres: 'Agricultural Land Ownership',
    education_level: 'Education Level',
    is_woman_entrepreneur: 'Woman Entrepreneur Status',
    marital_status: 'Marital Status'
  };
  if (KNOWN_LABELS[clean]) return KNOWN_LABELS[clean];
  return clean
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * FIN Phase D3.8: Eligibility State Messaging Integrity Helper
 * 
 * Strict Principle:
 * AI interprets → Rules decide → Evidence proves → Human reviews uncertainty.
 * 
 * Accurately distinguishes:
 * 1. MISSING_APPLICANT_FACTS
 * 2. UNREGISTERED_SCHEME
 * 3. INTELLIGENCE_UNAVAILABLE
 * 4. SNAPSHOT_UNAVAILABLE
 * 5. EVALUATION_ERROR
 * 6. MANUAL_REVIEW (Discretionary/field officer verification)
 * 7. ELIGIBLE (PASS)
 * 8. NOT_ELIGIBLE (FAIL)
 */
export function getEligibilityStateDetails(result) {
  if (!result) return null;

  const rawStatus = (result.status || 'UNKNOWN').toUpperCase();
  const rawVerdict = (result.verdict || (rawStatus === 'PASS' ? 'ELIGIBLE' : rawStatus === 'FAIL' ? 'NOT_ELIGIBLE' : 'MANUAL_REVIEW')).toUpperCase();
  const hasRules = Array.isArray(result.rules) && result.rules.length > 0;

  // Filter out any internal sentinels
  const rawMissing = Array.isArray(result.missingFields)
    ? result.missingFields
    : (Array.isArray(result.missing_fields) ? result.missing_fields : []);
  const sanitizedMissing = rawMissing
    .map(f => (typeof f === 'object' && f !== null ? (f.field || f.name || '') : String(f)))
    .filter(f => !isInternalSentinel(f));

  const missingFieldLabels = Array.isArray(result.missingFieldLabels) && result.missingFieldLabels.length > 0
    ? result.missingFieldLabels.filter(lbl => !isInternalSentinel(lbl))
    : sanitizedMissing.map(formatProfileFieldLabel);

  // Determine Category
  let category = result.evaluationCategory;
  if (!category) {
    if (rawStatus === 'PASS' || rawVerdict === 'ELIGIBLE') {
      category = 'ELIGIBLE';
    } else if (rawStatus === 'FAIL' || rawVerdict === 'NOT_ELIGIBLE') {
      category = 'NOT_ELIGIBLE';
    } else if (result.isRegistered === false || (!hasRules && rawMissing.some(f => typeof f === 'string' && f.includes('not_registered'))) || (!hasRules && !sanitizedMissing.length)) {
      category = 'UNREGISTERED_SCHEME';
    } else if (result.source === 'local_fallback' && result.intelligenceUnavailable && !hasRules) {
      category = 'INTELLIGENCE_UNAVAILABLE';
    } else if (sanitizedMissing.length > 0) {
      category = 'MISSING_APPLICANT_FACTS';
    } else {
      category = 'MANUAL_REVIEW';
    }
  }

  // Double check registered flag
  const isRegistered = result.isRegistered != null
    ? Boolean(result.isRegistered)
    : (category !== 'UNREGISTERED_SCHEME' && category !== 'SNAPSHOT_UNAVAILABLE');

  // Badge Class & Styling keys
  let badgeClass = 'amber';
  let verdictText = rawVerdict;
  let statusText = rawStatus;
  let tabSubtitle = 'Authoritative eligibility evaluation determined via Government policy rules engine.';
  let bannerReason = result.verdictReason || result.reason || '';
  let notice = null;
  let showMissingProfileBox = false;

  switch (category) {
    case 'ELIGIBLE':
      badgeClass = 'green';
      verdictText = 'ELIGIBLE';
      statusText = 'PASS';
      tabSubtitle = 'Evaluation completed against official statutory scheme rules.';
      bannerReason = result.verdictReason || `Your profile satisfies all ${result.rules?.length || 0} statutory eligibility criteria for this scheme.`;
      break;

    case 'NOT_ELIGIBLE':
      badgeClass = 'red';
      verdictText = 'NOT_ELIGIBLE';
      statusText = 'FAIL';
      tabSubtitle = 'Evaluation completed against official statutory scheme rules.';
      bannerReason = result.verdictReason || 'One or more statutory criteria were not satisfied.';
      break;

    case 'UNREGISTERED_SCHEME':
      badgeClass = 'amber';
      verdictText = 'MANUAL_REVIEW';
      statusText = 'UNKNOWN';
      tabSubtitle = 'Statutory rules not yet registered in automated engine — manual review applies.';
      bannerReason = 'Automated statutory rules are not registered for this scheme. Manual verification is required during departmental application review.';
      notice = 'Automated statutory rules are not registered for this scheme. Manual verification is required during departmental application review.';
      showMissingProfileBox = false;
      break;

    case 'INTELLIGENCE_UNAVAILABLE':
      badgeClass = 'amber';
      verdictText = 'MANUAL_REVIEW';
      statusText = 'UNKNOWN';
      tabSubtitle = 'Automated eligibility service is temporarily offline — manual review applies.';
      bannerReason = 'The eligibility intelligence service is currently offline or unreachable. Manual verification is required.';
      notice = 'The automated eligibility engine is temporarily unreachable. Please retry shortly or proceed with departmental application review.';
      showMissingProfileBox = false;
      break;

    case 'SNAPSHOT_UNAVAILABLE':
      badgeClass = 'amber';
      verdictText = 'MANUAL_REVIEW';
      statusText = 'UNKNOWN';
      tabSubtitle = 'Official policy snapshot is currently unavailable — manual review applies.';
      bannerReason = 'The statutory policy snapshot for this scheme is unavailable or could not be loaded. Manual verification is required.';
      notice = 'The official policy rules snapshot could not be retrieved. Manual verification is required.';
      showMissingProfileBox = false;
      break;

    case 'EVALUATION_ERROR':
      badgeClass = 'amber';
      verdictText = 'MANUAL_REVIEW';
      statusText = 'UNKNOWN';
      tabSubtitle = 'Automated evaluation encountered an error — manual review applies.';
      bannerReason = 'Automated statutory rules could not be evaluated due to an execution error. Manual verification is required.';
      notice = 'An unexpected error occurred while evaluating statutory criteria. Manual review will be performed.';
      showMissingProfileBox = false;
      break;

    case 'MISSING_APPLICANT_FACTS':
      badgeClass = 'amber';
      verdictText = 'MANUAL_REVIEW';
      statusText = (rawStatus === 'PASS' || rawStatus === 'FAIL') ? 'UNKNOWN' : rawStatus;
      tabSubtitle = 'Statutory evaluation paused: required applicant profile attributes are missing.';
      bannerReason = result.verdictReason || `Additional profile information is required to evaluate statutory criteria: ${missingFieldLabels.join(', ')}.`;
      showMissingProfileBox = sanitizedMissing.length > 0;
      break;

    case 'MANUAL_REVIEW':
    default:
      badgeClass = 'amber';
      verdictText = 'MANUAL_REVIEW';
      statusText = (rawStatus === 'PASS' || rawStatus === 'FAIL') ? 'UNKNOWN' : rawStatus;
      tabSubtitle = hasRules
        ? 'Evaluation completed: statutory guidelines mandate qualitative departmental review.'
        : 'Statutory guidelines require qualitative departmental review and manual officer verification.';
      bannerReason = result.verdictReason || 'Statutory guidelines mandate qualitative departmental review and manual officer verification.';
      showMissingProfileBox = false;
      break;
  }

  return {
    category,
    isRegistered,
    hasExecutedRules: hasRules && category !== 'UNREGISTERED_SCHEME',
    verdict: verdictText,
    status: statusText,
    badgeClass,
    tabSubtitle,
    bannerReason,
    notice,
    showMissingProfileBox,
    missingFields: showMissingProfileBox ? sanitizedMissing : [],
    missingFieldLabels: showMissingProfileBox ? missingFieldLabels : []
  };
}
