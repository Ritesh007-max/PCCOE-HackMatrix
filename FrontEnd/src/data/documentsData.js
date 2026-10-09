/**
 * Documents Data Model
 * Enhanced for PCCOE HackMatrix Citizen Portal
 * Clean state: zero dummy/mock documents or tickets.
 */

export const INITIAL_DOCUMENTS = [];

export const SUPPORTED_DOC_TYPES = [
  { id: 'aadhaar', name: 'Aadhaar Card', category: 'Identity Verification', purpose: 'Identity Proof', iconType: 'id-card', iconColor: 'blue' },
  { id: 'pan', name: 'PAN Card', category: 'Tax Identification', purpose: 'Financial Transactions', iconType: 'credit-card', iconColor: 'purple' },
  { id: 'income_cert', name: 'Income Certificate', category: 'Issued by State Government', purpose: 'Income Proof', iconType: 'certificate', iconColor: 'green' },
  { id: 'caste_cert', name: 'Caste Certificate', category: 'Issued by Competent Authority', purpose: 'Category Benefit', iconType: 'scroll', iconColor: 'amber' },
  { id: 'domicile', name: 'Domicile Certificate', category: 'State of Residence Proof', purpose: 'State Eligibility', iconType: 'home', iconColor: 'rose' },
  { id: 'bank_passbook', name: 'Bank Passbook / Details', category: 'Cancelled Cheque / Passbook', purpose: 'Direct Benefit Transfer', iconType: 'bank', iconColor: 'blue' },
  { id: 'address_proof', name: 'Address Proof', category: 'Residency Verification', purpose: 'Address Proof', iconType: 'map-pin', iconColor: 'cyan' },
  { id: 'udyam', name: 'Udyam Registration', category: 'MSME Verification', purpose: 'Business Eligibility', iconType: 'award', iconColor: 'purple' },
  { id: 'itr', name: 'Income Tax Return (ITR)', category: 'Financial Verification', purpose: 'Income Verification', iconType: 'file-text', iconColor: 'green' },
  { id: 'land', name: 'Land Records (7/12 Extract)', category: 'Revenue Department', purpose: 'Agriculture Proof', iconType: 'home', iconColor: 'amber' },
  { id: 'photo', name: 'Passport Size Photo', category: 'Visual Verification', purpose: 'Identity Verification', iconType: 'image', iconColor: 'rose' },
  { id: 'disability_cert', name: 'Disability Certificate', category: 'Medical Board', purpose: 'Affirmative Action', iconType: 'scroll', iconColor: 'blue' }
];

export const DOC_TYPE_LOOKUP = Object.fromEntries(SUPPORTED_DOC_TYPES.map(d => [d.id, d]));

export const SCHEMES_CHECKLIST = [
  {
    id: 'pmegp',
    name: 'PMEGP (Prime Minister Employment Generation)',
    benefit: 'Credit-Linked Margin Money Subsidy',
    requiredDocIds: ['aadhaar', 'pan', 'caste_cert', 'address_proof'],
  },
  {
    id: 'pm-kisan',
    name: 'PM Kisan Samman Nidhi',
    benefit: '₹ 6,000 / year (Direct Income Support)',
    requiredDocIds: ['aadhaar', 'bank_passbook', 'land', 'domicile'],
  },
  {
    id: 'msme',
    name: 'MSME Credit & Financial Support',
    benefit: 'Credit Guarantee & Term Support',
    requiredDocIds: ['aadhaar', 'pan', 'bank_passbook', 'address_proof'],
  },
  {
    id: 'scholarship',
    name: 'National Higher Education Scholarship',
    benefit: 'Direct Financial Assistance',
    requiredDocIds: ['aadhaar', 'income_cert', 'domicile', 'photo'],
  },
];

export const STORAGE_DOCUMENTS_KEY = 'fin_documents_data';
export const STORAGE_TICKETS_KEY = 'fin_support_tickets_data';
export const STORAGE_APPLICATIONS_KEY = 'fin_associated_applications_data';

export const INITIAL_TICKETS = [];

/**
 * Normalizes statutory requirement identifiers to standard vault document types:
 * caste -> caste_cert
 * address -> address_proof
 * bank -> bank_passbook
 * income -> income_cert
 */
export function normalizeDocRequirementId(rawId) {
  if (!rawId) return 'address_proof';
  const clean = String(rawId).toLowerCase().trim().replace(/[^a-z0-9_]/g, '_');
  if (clean === 'caste' || clean.includes('caste') || clean.includes('jati')) return 'caste_cert';
  if (clean === 'address' || clean.includes('address') || clean.includes('residence') || clean.includes('domicile')) return clean.includes('domicile') ? 'domicile' : 'address_proof';
  if (clean === 'bank' || clean.includes('bank') || clean.includes('passbook')) return 'bank_passbook';
  if (clean === 'income' || clean.includes('income') || clean.includes('salary') || clean.includes('aavak')) return 'income_cert';
  if (clean === 'photo' || clean.includes('photo') || clean.includes('picture')) return 'photo';
  if (clean === 'aadhaar' || clean.includes('aadhaar') || clean.includes('aadhar') || clean.includes('uidai')) return 'aadhaar';
  if (clean === 'pan' || clean.includes('pan')) return 'pan';
  if (clean === 'land' || clean.includes('land') || clean.includes('712') || clean.includes('ror')) return 'land';
  if (clean === 'domicile') return 'domicile';
  if (clean === 'udyam' || clean.includes('udyam') || clean.includes('msme')) return 'udyam';
  if (clean === 'itr' || clean.includes('tax') || clean.includes('itr')) return 'itr';
  if (clean.includes('disability') || clean.includes('handicap')) return 'disability_cert';
  return clean;
}

/**
 * Dynamically builds scheme checklist from canonical scheme records
 */
export function buildDynamicSchemeChecklist(schemesList = []) {
  if (!Array.isArray(schemesList) || schemesList.length === 0) {
    return SCHEMES_CHECKLIST;
  }
  return schemesList.map(s => {
    const rawDocs = s.documents_required || s.required_documents || s.documents || [];
    let parsedDocs = [];
    if (Array.isArray(rawDocs)) {
      parsedDocs = rawDocs;
    } else if (typeof rawDocs === 'string') {
      parsedDocs = rawDocs.split(/[;\n|]+/).map(t => t.trim()).filter(Boolean);
    }

    let requiredDocIds = [];
    if (parsedDocs.length > 0) {
      requiredDocIds = parsedDocs.map(d => ({
        id: normalizeDocRequirementId(d),
        label: d
      }));
    } else {
      requiredDocIds = [];
    }

    return {
      id: s.id || s.scheme_id,
      slug: s.slug || s.scheme_slug || null,
      name: s.name || s.scheme_name || s.title || 'Government Scheme',
      state: s.state || null,
      benefit: s.benefit_display || s.benefit_summary || (s.max_benefit ? `Up to ₹${Number(s.max_benefit).toLocaleString('en-IN')}` : 'Statutory Guidelines'),
      requiredDocIds
    };
  });
}

function getStorageKey(baseKey, userId) {
  return userId ? `${baseKey}_${userId}` : baseKey;
}

export function loadTicketsFromStorage(userId = null) {
  if (typeof window === 'undefined' || !window.localStorage) return [];
  try {
    const key = getStorageKey(STORAGE_APPLICATIONS_KEY, userId);
    let raw = localStorage.getItem(key);
    if (!raw && !userId) raw = localStorage.getItem(STORAGE_TICKETS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch (e) {
    console.error('Failed to load applications from storage', e);
  }
  return [];
}

export function saveTicketsToStorage(tickets, userId = null) {
  if (typeof window === 'undefined' || !window.localStorage) return;
  try {
    const key = getStorageKey(STORAGE_APPLICATIONS_KEY, userId);
    localStorage.setItem(key, JSON.stringify(tickets));
  } catch (e) {
    console.error('Failed to save applications to storage', e);
  }
}

export function loadDocumentsFromStorage(userId = null) {
  if (typeof window === 'undefined' || !window.localStorage) return [];
  try {
    const key = getStorageKey(STORAGE_DOCUMENTS_KEY, userId);
    const raw = localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch (e) {
    console.error('Failed to load documents from storage', e);
  }
  return [];
}

export function saveDocumentsToStorage(docs, userId = null) {
  if (typeof window === 'undefined' || !window.localStorage) return;
  try {
    const key = getStorageKey(STORAGE_DOCUMENTS_KEY, userId);
    localStorage.setItem(key, JSON.stringify(docs));
  } catch (e) {
    console.error('Failed to save documents to storage', e);
  }
}

