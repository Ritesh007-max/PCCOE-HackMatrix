/**
 * Documents Data Model
 * Enhanced for PCCOE HackMatrix Citizen Portal
 */

export const INITIAL_DOCUMENTS = [
  {
    id: 'aadhaar',
    name: 'Aadhaar Card',
    category: 'Identity Verification',
    purpose: 'Identity Proof',
    requiredForSchemes: 8,
    schemesList: ['PMEGP', 'PM-Kisan', 'MSME Support', 'PM Awas', 'Ayushman Bharat'],
    status: 'verified',
    statusLabel: 'Verified',
    source: 'UIDAI Official',
    validity: 'Lifetime',
    uploadedOn: '12 Sep 2026',
    fileType: 'PDF',
    fileSize: '1.4 MB',
    docNumber: 'XXXX-XXXX-4921',
    issuer: 'Unique Identification Authority of India (UIDAI)',
    iconType: 'id-card',
    iconColor: 'blue',
  },
  {
    id: 'pan',
    name: 'PAN Card',
    category: 'Tax Identification',
    purpose: 'Financial Transactions',
    requiredForSchemes: 6,
    schemesList: ['PMEGP', 'MSME Support', 'Mudra Loan', 'Stand-Up India'],
    status: 'verified',
    statusLabel: 'Verified',
    source: 'Income Tax Dept',
    validity: 'Lifetime',
    uploadedOn: '12 Sep 2026',
    fileType: 'PDF',
    fileSize: '820 KB',
    docNumber: 'ABCDE1234F',
    issuer: 'Income Tax Department, Govt of India',
    iconType: 'credit-card',
    iconColor: 'purple',
  },
  {
    id: 'income',
    name: 'Income Certificate',
    category: 'Issued by State Government',
    purpose: 'Income Proof',
    requiredForSchemes: 5,
    schemesList: ['PM Awas', 'National Scholarship', 'RTE Scheme', 'EWS Housing'],
    status: 'verified',
    statusLabel: 'Verified',
    source: 'Revenue Dept (Digital)',
    validity: 'Valid till 31 Mar 2027',
    uploadedOn: '10 Sep 2026',
    fileType: 'PDF',
    fileSize: '2.1 MB',
    docNumber: 'INC/2026/98214',
    issuer: 'Revenue Department, Government of Gujarat',
    iconType: 'certificate',
    iconColor: 'green',
  },
  {
    id: 'caste',
    name: 'Caste Certificate',
    category: 'Issued by Competent Authority',
    purpose: 'Category Benefit',
    requiredForSchemes: 4,
    schemesList: ['PMEGP Subsidy Boost', 'OBC Fellowship', 'Post-Matric Aid'],
    status: 'under_review',
    statusLabel: 'Under Review',
    source: 'Self Uploaded',
    validity: 'Permanent',
    uploadedOn: '09 Sep 2026',
    fileType: 'PDF',
    fileSize: '1.8 MB',
    docNumber: 'CST/2026/04112',
    issuer: 'Sub-Divisional Magistrate (SDM)',
    iconType: 'scroll',
    iconColor: 'amber',
  },
  {
    id: 'domicile',
    name: 'Domicile Certificate',
    category: 'State of Residence Proof',
    purpose: 'State Eligibility',
    requiredForSchemes: 7,
    schemesList: ['Gujarat Startup Grant', 'State Quota Aid', 'Kisan Solar Subsidy'],
    status: 'verified',
    statusLabel: 'Verified',
    source: 'e-District Portal',
    validity: 'Lifetime',
    uploadedOn: '09 Sep 2026',
    fileType: 'PDF',
    fileSize: '1.5 MB',
    docNumber: 'DOM/GJ/2026/7190',
    issuer: 'Tehsildar Office, Ahmedabad',
    iconType: 'home',
    iconColor: 'rose',
  },
  {
    id: 'bank',
    name: 'Bank Account Details',
    category: 'Cancelled Cheque / Passbook',
    purpose: 'Direct Benefit Transfer',
    requiredForSchemes: 12,
    schemesList: ['PM-Kisan DBT', 'PMEGP Subsidy', 'LPG Subsidy', 'Scholarship DBT'],
    status: 'verified',
    statusLabel: 'Verified',
    source: 'NPCI Aadhaar-Seeded',
    validity: 'Active (DBT Enabled)',
    uploadedOn: '08 Sep 2026',
    fileType: 'JPG',
    fileSize: '950 KB',
    docNumber: 'SBIN0001234 - A/C 98765432101',
    issuer: 'State Bank of India',
    iconType: 'bank',
    iconColor: 'blue',
  },
  {
    id: 'photo',
    name: 'Passport Size Photo',
    category: 'Recent Photograph',
    purpose: 'Application Form',
    requiredForSchemes: 10,
    schemesList: ['All Application Portals'],
    status: 'verified',
    statusLabel: 'Verified',
    source: 'Self Uploaded',
    validity: 'Valid (Taken Aug 2026)',
    uploadedOn: '08 Sep 2026',
    fileType: 'JPG',
    fileSize: '420 KB',
    docNumber: 'PHOTO-2026-0908',
    issuer: 'Applicant Self-Upload',
    iconType: 'image',
    iconColor: 'purple',
  },
  {
    id: 'address',
    name: 'Address Proof',
    category: 'Electricity Bill / Rent Agreement',
    purpose: 'Address Verification',
    requiredForSchemes: 3,
    schemesList: ['PMEGP Project Site', 'MSME Enterprise Proof'],
    status: 'action_required',
    statusLabel: 'Action Required',
    source: 'Pending Verification',
    validity: 'Pending Upload',
    uploadedOn: '-',
    fileType: '-',
    fileSize: '-',
    docNumber: '-',
    issuer: 'State Electricity Board / Landlord Agreement',
    iconType: 'map-pin',
    iconColor: 'red',
  },
];

export const SCHEMES_CHECKLIST = [
  {
    id: 'pmegp',
    name: 'PMEGP (Prime Minister Employment Generation)',
    benefit: '₹ 1,25,000 Subsidy',
    requiredDocIds: ['aadhaar', 'pan', 'caste', 'address'],
  },
  {
    id: 'pm-kisan',
    name: 'PM Kisan Samman Nidhi',
    benefit: '₹ 6,000 / year',
    requiredDocIds: ['aadhaar', 'bank', 'domicile'],
  },
  {
    id: 'msme',
    name: 'MSME Credit & Financial Support',
    benefit: '₹ 80,000 Support',
    requiredDocIds: ['aadhaar', 'pan', 'bank', 'address'],
  },
  {
    id: 'scholarship',
    name: 'National Higher Education Scholarship',
    benefit: '₹ 50,000 / year',
    requiredDocIds: ['aadhaar', 'income', 'domicile', 'photo'],
  },
];

export const STORAGE_DOCUMENTS_KEY = 'fin_documents_data';
export const STORAGE_TICKETS_KEY = 'fin_support_tickets_data';

export const INITIAL_TICKETS = [
  {
    id: 'TKT-2026-1042',
    category: 'Document Verification Delay',
    docId: 'caste',
    docName: 'Caste Certificate',
    subject: 'Caste Certificate verification pending over 5 days',
    description: 'Submitted OBC certificate issued by SDM Ahmedabad. Status is still showing Under Review.',
    priority: 'High',
    status: 'Under Review',
    createdAt: '22 Sep 2026, 03:30 PM',
  },
];

export function loadTicketsFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_TICKETS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch (e) {
    console.error('Failed to load tickets from storage', e);
  }
  return INITIAL_TICKETS;
}

export function saveTicketsToStorage(tickets) {
  try {
    localStorage.setItem(STORAGE_TICKETS_KEY, JSON.stringify(tickets));
  } catch (e) {
    console.error('Failed to save tickets to storage', e);
  }
}

export function loadDocumentsFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_DOCUMENTS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        // Sanitize any legacy DigiLocker references
        return parsed.map((doc) => {
          if (doc.source && doc.source.includes('DigiLocker')) {
            let sanitizedSource = 'Verified Authority';
            if (doc.id === 'aadhaar') sanitizedSource = 'UIDAI Official';
            if (doc.id === 'pan') sanitizedSource = 'Income Tax Dept';
            if (doc.id === 'domicile') sanitizedSource = 'e-District Portal';
            if (doc.id === 'address') sanitizedSource = 'Utility Board';
            return { ...doc, source: sanitizedSource };
          }
          return doc;
        });
      }
    }
  } catch (e) {
    console.error('Failed to load documents from storage', e);
  }
  return INITIAL_DOCUMENTS;
}

export function saveDocumentsToStorage(docs) {
  try {
    localStorage.setItem(STORAGE_DOCUMENTS_KEY, JSON.stringify(docs));
  } catch (e) {
    console.error('Failed to save documents to storage', e);
  }
}
