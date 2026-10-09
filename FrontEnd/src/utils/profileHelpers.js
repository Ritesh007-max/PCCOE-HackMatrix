/**
 * FIN — Profile Data & Display Helpers
 *
 * Provides pure utility functions for the citizen profile:
 * - Phone number sanitization and normalization
 * - Annual income formatting and standard range mapping
 * - Last login timestamp formatting
 * - Dynamic profile completion percentage calculation
 * - Dynamic initials generation
 */

import { isValidState, isValidStateDistrict } from '../data/geoData.js';

/**
 * Normalizes Indian phone numbers and completely prevents duplicate '+91 91' prefixes
 */
export function sanitizeIndianPhone(raw) {
  if (!raw || typeof raw !== 'string' || !raw.trim()) return '';
  let cleaned = raw.trim().replace(/^\+?91[\s\-_]*\+?91[\s\-_]*/, '+91 ').replace(/^\+?91[\s\-_]*/, '+91 ');
  const digits = cleaned.replace(/\D/g, '');
  if (digits.length === 12 && digits.startsWith('91')) {
    const m = digits.slice(2);
    return `+91 ${m.slice(0, 5)} ${m.slice(5)}`;
  } else if (digits.length === 10) {
    return `+91 ${digits.slice(0, 5)} ${digits.slice(5)}`;
  }
  if (cleaned.startsWith('+91')) {
    const rest = cleaned.slice(3).replace(/^\s*91\s*/, '').trim();
    return `+91 ${rest}`;
  }
  return cleaned;
}

export const CANONICAL_INCOME_RANGES = [
  'Below ₹1 Lakh',
  '₹1 Lakh - ₹2.5 Lakhs',
  '₹2.5 Lakhs - ₹5 Lakhs',
  '₹5 Lakhs - ₹10 Lakhs',
  'Above ₹10 Lakhs'
];

/**
 * Returns canonical numeric amount corresponding to an income range bracket
 */
export function getCanonicalAmountForRange(range) {
  switch (range) {
    case 'Below ₹1 Lakh': return 80000;
    case '₹1 Lakh - ₹2.5 Lakhs': return 200000;
    case '₹2.5 Lakhs - ₹5 Lakhs': return 350000;
    case '₹5 Lakhs - ₹10 Lakhs': return 750000;
    case 'Above ₹10 Lakhs': return 1200000;
    default: return null;
  }
}

/**
 * Formats annual personal income into currency string (e.g. 350000 -> ₹3,50,000)
 * Deterministically treats 0 as ₹0, while missing/null/undefined remains 'Not added'.
 */
export function formatAnnualIncome(income) {
  if (income === 0) return '₹0';
  if (income === null || income === undefined || income === '' || income === 'Not added') {
    return 'Not added';
  }
  const cleanStr = String(income).trim();
  if (cleanStr === '0' || cleanStr === '₹0' || cleanStr === '0.00') {
    return '₹0';
  }
  const numericOnly = Number(cleanStr.replace(/[^0-9.]/g, ''));
  if (!isNaN(numericOnly) && /^\d+$/.test(cleanStr.replace(/[,\s₹]/g, ''))) {
    return `₹${numericOnly.toLocaleString('en-IN')}`;
  }
  return cleanStr;
}

/**
 * Format gender for presentation (e.g. 'male' -> 'Male')
 */
export function formatGender(val) {
  if (!val || val === 'Not added') return 'Not added';
  const clean = String(val).trim().toLowerCase();
  const map = {
    male: 'Male',
    female: 'Female',
    other: 'Other',
    transgender: 'Other',
    prefer_not_to_say: 'Prefer not to say',
    'prefer not to say': 'Prefer not to say'
  };
  return map[clean] || (clean.charAt(0).toUpperCase() + clean.slice(1));
}

/**
 * Normalizes social category into canonical database value (sc, st, obc, general, ews)
 */
export function normalizeSocialCategory(cat) {
  if (!cat || cat === 'Not added') return '';
  const clean = String(cat).trim().toLowerCase();
  const map = {
    'sc': 'sc',
    'scheduled caste': 'sc',
    'st': 'st',
    'scheduled tribe': 'st',
    'obc': 'obc',
    'other backward class': 'obc',
    'general': 'general',
    'gen': 'general',
    'ews': 'ews',
    'economically weaker section': 'ews'
  };
  return map[clean] || clean;
}

/**
 * Formats canonical social category for presentation (e.g. 'sc' -> 'SC', 'general' -> 'General')
 */
export function formatSocialCategory(cat) {
  if (!cat || cat === 'Not added') return 'Not added';
  const norm = normalizeSocialCategory(cat);
  const map = {
    'sc': 'SC',
    'st': 'ST',
    'obc': 'OBC',
    'general': 'General',
    'ews': 'EWS'
  };
  return map[norm] || String(cat).trim();
}

/**
 * Maps numeric annual income to corresponding standard range bracket
 * Deterministic boundaries:
 * [0, 100000) -> Below ₹1 Lakh
 * [100000, 250000] -> ₹1 Lakh - ₹2.5 Lakhs
 * (250000, 500000] -> ₹2.5 Lakhs - ₹5 Lakhs
 * (500000, 1000000] -> ₹5 Lakhs - ₹10 Lakhs
 * (1000000, infinity) -> Above ₹10 Lakhs
 */
export function mapIncomeToRange(income) {
  if (income === null || income === undefined || income === '' || income === 'Not added') {
    return '';
  }
  const cleanStr = String(income).trim();
  if (CANONICAL_INCOME_RANGES.includes(cleanStr)) {
    return cleanStr;
  }
  if (cleanStr === '0' || cleanStr === '₹0') {
    return 'Below ₹1 Lakh';
  }
  const num = Number(cleanStr.replace(/[^0-9.]/g, ''));
  if (isNaN(num) || num < 0) return '';
  if (num < 100000) return 'Below ₹1 Lakh';
  if (num <= 250000) return '₹1 Lakh - ₹2.5 Lakhs';
  if (num <= 500000) return '₹2.5 Lakhs - ₹5 Lakhs';
  if (num <= 1000000) return '₹5 Lakhs - ₹10 Lakhs';
  return 'Above ₹10 Lakhs';
}

/**
 * Formats ISO last sign-in timestamp into readable date time
 */
export function formatLastLogin(lastSignInAt) {
  if (!lastSignInAt) return 'Current session';
  try {
    const d = new Date(lastSignInAt);
    if (isNaN(d.getTime())) return 'Current session';
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  } catch {
    return 'Current session';
  }
}

/**
 * Validates if a value is a valid numeric annual personal income.
 * Accepts numeric values (0 is strictly valid) and clean numeric strings ("350000", "0").
 * Returns false for null, undefined, '', 'Not added', range strings (e.g. '₹2.5 Lakhs - ₹5 Lakhs'), or NaN.
 */
export function isValidNumericIncome(val) {
  if (val === null || val === undefined || val === '') return false;
  if (typeof val === 'number') {
    return !isNaN(val) && isFinite(val) && val >= 0;
  }
  if (typeof val === 'string') {
    const trimmed = val.trim();
    if (!trimmed || trimmed === 'Not added') return false;
    // Reject range strings or text descriptions
    if (CANONICAL_INCOME_RANGES.includes(trimmed)) return false;
    if (trimmed.includes('-') || trimmed.toLowerCase().includes('lakh') || trimmed.toLowerCase().includes('crore')) {
      return false;
    }
    // Clean currency symbols and commas
    const cleaned = trimmed.replace(/^[₹\s]+/, '').replace(/,/g, '');
    if (!/^\d+(\.\d+)?$/.test(cleaned)) return false;
    const num = Number(cleaned);
    return !isNaN(num) && isFinite(num) && num >= 0;
  }
  return false;
}

/**
 * Evaluates whether an applicant profile contains complete location & income recommendation fields:
 * - State is present
 * - District / City is present (and valid for the State if canonical)
 * - Annual income is a valid numeric value (0 is valid)
 *
 * Income source of truth is annual_income.
 * income_range without annual_income does not satisfy completion.
 */
export function isLocationAndIncomeComplete(profile) {
  if (!profile) return false;

  // 1. State must be present
  const state = profile.state;
  if (!state || typeof state !== 'string' || !state.trim() || state.trim() === 'Not added') {
    return false;
  }

  // 2. District / City must be present
  const rawDistrict = profile.district || profile.city;
  if (!rawDistrict || typeof rawDistrict !== 'string' || !rawDistrict.trim() || rawDistrict.trim() === 'Not added') {
    return false;
  }
  if (isValidState(state) && !isValidStateDistrict(state, rawDistrict)) {
    return false;
  }

  // 3. annual_income must be a valid numeric value (0 is valid)
  const incomeValue = profile.annual_income !== undefined
    ? profile.annual_income
    : (typeof profile.income === 'number' ? profile.income : null);

  return isValidNumericIncome(incomeValue);
}

/**
 * Calculates profile completion percentage dynamically across core fields
 */
export function calculateProfileCompletion(data) {
  if (!data) return 0;
  
  // Requirement 13: District should count as complete only when it contains a valid district for the selected state
  const isDistrictValid = data.state && data.district && isValidStateDistrict(data.state, data.district);
  const effectiveDistrict = isDistrictValid ? data.district : null;

  // Income completeness:
  // If annual_income is explicitly specified, validate numerically (0 is valid).
  // If annual_income is undefined, fall back to data.income (support numeric 0, or legacy non-empty range strings).
  let isIncomeFilled = false;
  if (data.annual_income !== undefined) {
    isIncomeFilled = isValidNumericIncome(data.annual_income);
  } else if (data.income !== undefined && data.income !== null) {
    isIncomeFilled = isValidNumericIncome(data.income) || (typeof data.income === 'string' && data.income.trim() !== '' && data.income.trim() !== 'Not added');
  }

  const fields = [
    data.fullName,
    data.email,
    data.phone,
    data.state,
    effectiveDistrict,
    data.occupation,
    isIncomeFilled ? 'income_filled' : null,
    data.applicantType,
    data.dob,
    data.gender,
  ];
  const filledCount = fields.filter((val) => val !== null && val !== undefined && String(val).trim() !== '' && String(val).trim() !== 'Not added').length;
  return Math.round((filledCount / fields.length) * 100);
}

export const calculateCompletion = calculateProfileCompletion;

/**
 * Derives user initials dynamically from name
 */
export function getProfileInitials(name) {
  if (!name) return 'CI';
  const clean = name.trim();
  if (!clean) return 'CI';
  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length > 1) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return clean.slice(0, 2).toUpperCase();
}
