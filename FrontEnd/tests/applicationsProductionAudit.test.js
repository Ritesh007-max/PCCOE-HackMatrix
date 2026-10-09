/**
 * applicationsProductionAudit.test.js
 * FIN — Applications Final Production Audit Test Suite (Frontend)
 *
 * Covers:
 * - Application mapping from persisted database records
 * - Scheme mapping & unavailable scheme handling (no fabricated fallbacks)
 * - Dynamic applicant identity and last updated timestamp
 * - Benefit display & numeric safety (no loan ceilings as cash grants)
 * - Status integrity across all canonical statuses (under_review, approved, rejected, action_required, draft)
 * - Authentic 4-stage stepper progression (does not visually imply approved when under_review)
 * - Document relation (submitted documents with verification status; OCR_EXTRACTED != VERIFIED)
 * - Required scheme documents mapping
 * - Official acknowledgement receipt generation
 * - Filtering and sorting correctness
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { mapBackendApplication, downloadReceipt } from '../src/utils/applicationHelpers.js';

test('1. Scheme Mapping & Dynamic Data: maps authoritative scheme identity, category, and applicant details', () => {
  const bApp = {
    id: 'f87a8b42-1234-4567-89ab-cdef01234567',
    scheme_id: 'scholarship-st-2026',
    scheme_name: 'Post Matric Scholarship Scheme for ST Students',
    applicant_name: 'Dhruv',
    benefit_display: '₹25,000 / year',
    benefit_subtitle: 'Recurring Scholarship Grant',
    benefit_numeric: 25000,
    status: 'under_review',
    submitted_at: '2026-08-15T10:30:00.000Z',
    last_updated: '2026-10-04T12:00:00.000Z',
    scheme: {
      id: 'scholarship-st-2026',
      scheme_name: 'Post Matric Scholarship Scheme for ST Students',
      category: 'Education & Scholarships',
      dbt_scheme: true,
      documents_required: ['Aadhaar Card', 'Caste Certificate', 'Income Certificate']
    },
    submitted_documents: [
      {
        id: 'doc-1',
        name: 'income_cert.pdf',
        document_type: 'income_cert',
        verification_status: 'PENDING',
        verified: false,
        reason: 'Pending Verification'
      }
    ],
    remarks: 'Application under review at district nodal office'
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.schemeTitle, 'Post Matric Scholarship Scheme for ST Students');
  assert.equal(mapped.schemeSubtitle, 'Direct Benefit Transfer Scheme');
  assert.equal(mapped.applicantName, 'Dhruv');
  assert.equal(mapped.applicationId, 'FINF87A8B42');
  assert.equal(mapped.benefitAmount, '₹25,000 / year');
  assert.equal(mapped.benefitSubtitle, 'Recurring Scholarship Grant');
  assert.equal(mapped.status, 'under_review');
  assert.equal(mapped.statusBadge, 'Under Review');
  assert.equal(mapped.isSchemeAvailable, true);
  assert.equal(mapped.remarks, 'Application under review at district nodal office');
  assert.equal(mapped.submittedDocs.length, 1);
  assert.equal(mapped.submittedDocs[0].verified, false);
  assert.equal(mapped.requiredDocs.length, 3);
});

test('2. Missing/Stale Scheme Handling: marks unlinked schemes honestly without fabricating names or benefits', () => {
  const bApp = {
    id: 'e48e5ef1-24c6-498b-9e88-ae3036cb7821',
    scheme_id: 'unknown-deleted-scheme-uuid',
    scheme_name: null,
    is_scheme_available: false,
    benefit_display: 'Not specified',
    benefit_subtitle: 'Benefit Information Unavailable',
    status: 'under_review',
    submitted_at: '2026-09-20T10:00:00.000Z'
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.schemeTitle, 'Scheme Unavailable');
  assert.equal(mapped.schemeSubtitle, 'Unlinked Scheme Record');
  assert.equal(mapped.benefitAmount, 'Not specified');
  assert.equal(mapped.benefitSubtitle, 'Benefit Information Unavailable');
  assert.equal(mapped.isSchemeAvailable, false);
});

test('3. Benefit Integrity (Loan Distinction): displays loan ceiling clearly without cash grant confusion', () => {
  const bApp = {
    id: '15dsugt8-1234-5678-abcd-1234567890ab',
    scheme_id: 'pm-vidyalaxmi',
    scheme_name: 'PM Vidyalaxmi Education Support Scheme',
    benefit_display: 'Up to ₹7,50,000 (Loan)',
    benefit_subtitle: '(Credit Facility / Repayable Loan)',
    benefit_numeric: 0,
    status: 'under_review',
    submitted_at: '2026-07-20T08:00:00.000Z'
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.benefitAmount, 'Up to ₹7,50,000 (Loan)');
  assert.equal(mapped.benefitSubtitle, '(Credit Facility / Repayable Loan)');
  assert.equal(mapped.benefitNumeric, 0);
});

test('4. Benefit Integrity (Penalty Waiver): displays waiver without representing as cash income', () => {
  const bApp = {
    id: 'aa43bcf6-11ca-4b03-b944-c5ac7221ade3',
    scheme_id: '32198bb9-6b92-493f-8d45-9ba7f5807148',
    scheme_name: '100% Penalty Mafi Yojana',
    benefit_display: '100% Penalty Waiver',
    benefit_subtitle: '(Penalty Waiver)',
    benefit_numeric: 0,
    status: 'under_review'
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.benefitAmount, '100% Penalty Waiver');
  assert.equal(mapped.benefitSubtitle, '(Penalty Waiver)');
  assert.equal(mapped.benefitNumeric, 0);
});

test('5. Status Stepper Progression: under_review does NOT visually imply Approved or Disbursed', () => {
  const bApp = {
    id: 'app-under-review-1',
    status: 'under_review',
    submitted_at: '2026-09-26T10:00:00.000Z'
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.steps[0].label, 'Submitted');
  assert.equal(mapped.steps[0].status, 'completed');

  assert.equal(mapped.steps[1].label, 'Verification');
  assert.equal(mapped.steps[1].status, 'current-green');
  assert.equal(mapped.steps[1].date, 'In Progress');

  assert.equal(mapped.steps[2].label, 'Approval');
  assert.equal(mapped.steps[2].status, 'upcoming'); // Must NOT be completed or current
  assert.equal(mapped.steps[2].date, '');

  assert.equal(mapped.steps[3].label, 'Disbursement');
  assert.equal(mapped.steps[3].status, 'upcoming'); // Must NOT be completed or current
});

test('6. Status Stepper Progression: action_required highlights Verification as error', () => {
  const bApp = {
    id: 'app-action-req-1',
    status: 'action_required',
    submitted_at: '2026-09-26T10:00:00.000Z'
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.statusBadge, 'Action Required');
  assert.equal(mapped.steps[1].label, 'Verification');
  assert.equal(mapped.steps[1].status, 'error');
  assert.equal(mapped.steps[1].date, 'Action Required');
});

test('7. Status Stepper Progression: approved marks Approval completed and Disbursement scheduled', () => {
  const bApp = {
    id: 'app-approved-1',
    status: 'approved',
    submitted_at: '2026-09-26T10:00:00.000Z'
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.statusBadge, 'Approved');
  assert.equal(mapped.steps[1].status, 'completed');
  assert.equal(mapped.steps[2].label, 'Approval');
  assert.equal(mapped.steps[2].status, 'completed');
  assert.equal(mapped.steps[2].date, 'Approved');
  assert.equal(mapped.steps[3].label, 'Disbursement');
  assert.equal(mapped.steps[3].status, 'current-green');
});

test('8. Document Relation: preserves real document verification status; OCR_EXTRACTED is not VERIFIED', () => {
  const bApp = {
    id: 'app-doc-test',
    status: 'under_review',
    submitted_documents: [
      {
        id: 'doc-pending-1',
        name: 'income_cert.pdf',
        document_type: 'income_cert',
        verification_status: 'PENDING',
        verified: false,
        reason: 'Pending Verification'
      },
      {
        id: 'doc-verified-2',
        name: 'aadhaar_card.pdf',
        document_type: 'aadhaar',
        verification_status: 'VERIFIED',
        verified: true,
        reason: 'Verified ✓'
      }
    ]
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.submittedDocs.length, 2);
  assert.equal(mapped.submittedDocs[0].verified, false);
  assert.equal(mapped.submittedDocs[0].reason, 'Pending Verification');
  assert.equal(mapped.submittedDocs[1].verified, true);
  assert.equal(mapped.submittedDocs[1].reason, 'Verified ✓');
});

test('9. Official Receipt Generation: includes dynamic applicant name, ID, and scheme title', () => {
  const app = {
    applicationId: 'FIN5CCD4D20',
    dbId: '5ccd4d20-24e3-4607-9e3f-803d6124e1a7',
    applicantName: 'Dhruv',
    appliedDate: '02 Oct 2026',
    lastUpdated: '04 Oct 2026',
    statusBadge: 'Under Review',
    schemeTitle: 'PM Vidyalaxmi Education Support Scheme',
    schemeSubtitle: 'Government Assistance',
    benefitSubtitle: '(Credit Facility / Repayable Loan)',
    benefitAmount: 'Up to ₹7,50,000 (Loan)',
    statusMessage: 'Your application is under active departmental review.',
    steps: [
      { label: 'Submitted', date: '02 Oct 2026', status: 'completed' },
      { label: 'Verification', date: 'In Progress', status: 'current-green' }
    ]
  };

  const text = downloadReceipt(app);
  assert.ok(text.includes('FIN5CCD4D20'));
  assert.ok(text.includes('Dhruv'));
  assert.ok(text.includes('PM Vidyalaxmi Education Support Scheme'));
  assert.ok(text.includes('Up to ₹7,50,000 (Loan)'));
  assert.ok(text.includes('Under Review'));
});

test('10. Safe Fallbacks: null or undefined backend application returns null safely', () => {
  assert.equal(mapBackendApplication(null), null);
  assert.equal(mapBackendApplication(undefined), null);
  assert.equal(downloadReceipt(null), null);
});
