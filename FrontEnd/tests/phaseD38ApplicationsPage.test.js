import test from 'node:test';
import assert from 'node:assert/strict';
import { mapBackendApplication, downloadReceipt } from '../src/utils/applicationHelpers.js';

test('Phase D3.8 Frontend: 1. Grant scheme mapping preserves grant identity and authoritative benefit', () => {
  const bApp = {
    id: 'f87a8b42-1234-4567-89ab-cdef01234567',
    scheme_id: 'scholarship-grant-2026',
    scheme_name: 'Post Matric Scholarship Scheme for ST Students',
    benefit_display: '₹25,000 / year',
    benefit_subtitle: 'Recurring Scholarship Grant',
    status: 'under_review',
    submitted_at: '2026-08-15T10:30:00.000Z',
    scheme: {
      id: 'scholarship-grant-2026',
      scheme_name: 'Post Matric Scholarship Scheme for ST Students',
      category: 'Education & Scholarships',
      dbt_scheme: true
    }
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.schemeTitle, 'Post Matric Scholarship Scheme for ST Students');
  assert.equal(mapped.benefitAmount, '₹25,000 / year');
  assert.equal(mapped.benefitSubtitle, 'Recurring Scholarship Grant');
  assert.equal(mapped.schemeSubtitle, 'Direct Benefit Transfer Scheme');
  assert.equal(mapped.isSchemeAvailable, true);
  assert.notEqual(mapped.benefitAmount, '₹1,75,000');
});

test('Phase D3.8 Frontend: 2. Fellowship scheme preserves stipend presentation without lump-sum confusion', () => {
  const bApp = {
    id: 'b75fba18-7b98-4449-a1fc-2216834b9d0e',
    scheme_id: 'young-investigators-programme-in-biotechnology-yipb',
    scheme_name: 'Young Investigators Programme in Biotechnology (YIPB)',
    benefit_display: '₹75,000 / month (Stipend)',
    benefit_subtitle: 'Research Fellowship + Contingency Grant',
    status: 'under_review',
    submitted_at: '2026-09-01T12:00:00.000Z',
    scheme: {
      id: 'young-investigators-programme-in-biotechnology-yipb',
      scheme_name: 'Young Investigators Programme in Biotechnology (YIPB)',
      category: 'Science, IT & Research',
      dbt_scheme: false
    }
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.schemeTitle, 'Young Investigators Programme in Biotechnology (YIPB)');
  assert.equal(mapped.benefitAmount, '₹75,000 / month (Stipend)');
  assert.equal(mapped.benefitSubtitle, 'Research Fellowship + Contingency Grant');
  assert.equal(mapped.schemeSubtitle, 'Science, IT & Research');
  assert.notEqual(mapped.benefitAmount, '₹1,75,000');
});

test('Phase D3.8 Frontend: 3. Loan scheme distinguishes loan ceiling from approved grant', () => {
  const bApp = {
    id: '15dsugt8-1234-5678-abcd-1234567890ab',
    scheme_id: 'pm-vidyalaxmi',
    scheme_name: 'PM Vidyalaxmi Education Support Scheme',
    benefit_display: 'Up to ₹7,50,000 (Loan)',
    benefit_subtitle: 'Collateral-free Education Loan Support',
    status: 'approved',
    submitted_at: '2026-07-20T08:00:00.000Z',
    scheme: {
      id: 'pm-vidyalaxmi',
      scheme_name: 'PM Vidyalaxmi Education Support Scheme',
      category: 'Education & Loans',
      dbt_scheme: false
    }
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.schemeTitle, 'PM Vidyalaxmi Education Support Scheme');
  assert.equal(mapped.benefitAmount, 'Up to ₹7,50,000 (Loan)');
  assert.equal(mapped.benefitSubtitle, 'Collateral-free Education Loan Support');
  assert.equal(mapped.statusBadge, 'Approved');
  assert.notEqual(mapped.benefitAmount, '₹1,75,000');
});

test('Phase D3.8 Frontend: 4. Interest subsidy distinguishes interest subvention from cash grant', () => {
  const bApp = {
    id: 'c1234567-89ab-cdef-0123-456789abcdef',
    scheme_id: 'interest-subsidy-study-abroad',
    scheme_name: '6% Interest Subsidy on Loans taken through Banks for Study Abroad',
    benefit_display: '6% Interest Subsidy',
    benefit_subtitle: 'Interest Subvention on Bank Loan',
    status: 'under_review',
    submitted_at: '2026-08-10T11:00:00.000Z',
    scheme: {
      id: 'interest-subsidy-study-abroad',
      scheme_name: '6% Interest Subsidy on Loans taken through Banks for Study Abroad',
      category: 'Social Welfare & Empowerment',
      dbt_scheme: false
    }
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.schemeTitle, '6% Interest Subsidy on Loans taken through Banks for Study Abroad');
  assert.equal(mapped.benefitAmount, '6% Interest Subsidy');
  assert.equal(mapped.benefitSubtitle, 'Interest Subvention on Bank Loan');
  assert.notEqual(mapped.benefitAmount, '₹1,75,000');
});

test('Phase D3.8 Frontend: 5. Waiver scheme distinguishes statutory penalty waiver from monetary payout', () => {
  const bApp = {
    id: 'e6988891-fc5c-4f11-97b5-22d7d52a2336',
    scheme_id: '100-penalty-mafi-yojana',
    scheme_name: '100% Penalty Mafi Yojana',
    benefit_display: '100% Penalty Waiver',
    benefit_subtitle: 'Full Relief on Past Compounding Penalties',
    status: 'under_review',
    submitted_at: '2026-09-12T14:30:00.000Z',
    scheme: {
      id: '100-penalty-mafi-yojana',
      scheme_name: '100% Penalty Mafi Yojana',
      category: 'Finance & Tax Relief',
      dbt_scheme: false
    }
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.schemeTitle, '100% Penalty Mafi Yojana');
  assert.equal(mapped.benefitAmount, '100% Penalty Waiver');
  assert.equal(mapped.benefitSubtitle, 'Full Relief on Past Compounding Penalties');
  assert.notEqual(mapped.benefitAmount, '₹1,75,000');
});

test('Phase D3.8 Frontend: 6. Non-financial scheme preserves in-kind benefit without cash confusion', () => {
  const bApp = {
    id: 'd9876543-210f-edcb-a987-654321fedcba',
    scheme_id: 'free-textbook-distribution',
    scheme_name: 'Schemes for welfare of School Children - Free Uniform & Books',
    benefit_display: 'In-kind Assistance',
    benefit_subtitle: 'Educational Kits & Materials',
    status: 'under_review',
    submitted_at: '2026-09-05T09:00:00.000Z',
    scheme: {
      id: 'free-textbook-distribution',
      scheme_name: 'Schemes for welfare of School Children - Free Uniform & Books',
      category: 'Education & Learning',
      dbt_scheme: false
    }
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.schemeTitle, 'Schemes for welfare of School Children - Free Uniform & Books');
  assert.equal(mapped.benefitAmount, 'In-kind Assistance');
  assert.notEqual(mapped.benefitAmount, '₹1,75,000');
});

test('Phase D3.8 Frontend: 7. Missing scheme relationship renders transparent unavailable state', () => {
  const bApp = {
    id: '00000000-0000-0000-0000-000000000000',
    scheme_id: 'unknown-deleted-scheme-uuid',
    scheme_name: null,
    is_scheme_available: false,
    benefit_display: 'Not specified',
    benefit_subtitle: 'Benefit Information Unavailable',
    status: 'under_review',
    submitted_at: '2026-09-01T00:00:00.000Z',
    scheme: null
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.schemeTitle, 'Scheme Unavailable');
  assert.equal(mapped.schemeSubtitle, 'Unlinked Scheme Record');
  assert.equal(mapped.isSchemeAvailable, false);
  assert.equal(mapped.benefitAmount, 'Not specified');
  assert.equal(mapped.benefitSubtitle, 'Benefit Information Unavailable');
});

test('Phase D3.8 Frontend: 8. Missing benefit amount displays "Not specified"', () => {
  const bApp = {
    id: 'aaaa1111-2222-3333-4444-555566667777',
    scheme_id: 'horticulture-skill-dev',
    scheme_name: 'Training Scheme for Horticulture Skill Development',
    benefit_display: 'Not specified',
    benefit_subtitle: 'Not specified',
    status: 'under_review',
    submitted_at: '2026-09-02T10:00:00.000Z',
    scheme: {
      id: 'horticulture-skill-dev',
      scheme_name: 'Training Scheme for Horticulture Skill Development',
      category: 'Agriculture & Rural'
    }
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.benefitAmount, 'Not specified');
  assert.notEqual(mapped.benefitAmount, '₹1,75,000');
});

test('Phase D3.8 Frontend: 9. Pending / Under Review application uses authentic lifecycle stepper', () => {
  const bApp = {
    id: 'bbbb2222-3333-4444-5555-666677778888',
    scheme_id: 'test-scheme-pending',
    scheme_name: 'State Seed Capital Support',
    status: 'pending',
    submitted_at: '2026-09-10T12:00:00.000Z'
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.statusBadge, 'Under Review');
  assert.equal(mapped.steps[0].status, 'completed'); // Submitted
  assert.equal(mapped.steps[1].status, 'current-green'); // Verification in progress
  assert.equal(mapped.steps[2].status, 'upcoming'); // Approval upcoming (not invented)
  assert.equal(mapped.steps[3].status, 'upcoming'); // Disbursement upcoming (not invented)
});

test('Phase D3.8 Frontend: 10. Approved application correctly reflects completed verification & approval', () => {
  const bApp = {
    id: 'cccc3333-4444-5555-6666-777788889999',
    scheme_id: 'test-scheme-approved',
    scheme_name: 'Chief Minister Employment Generation Programme',
    status: 'approved',
    submitted_at: '2026-06-10T12:00:00.000Z'
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.statusBadge, 'Approved');
  assert.equal(mapped.steps[0].status, 'completed'); // Submitted
  assert.equal(mapped.steps[1].status, 'completed'); // Verification completed
  assert.equal(mapped.steps[2].status, 'completed'); // Approval completed
  assert.equal(mapped.steps[3].status, 'current-green'); // Disbursement pending/current
});

test('Phase D3.8 Frontend: 11. Rejected application halts lifecycle cleanly without fabricated disbursement', () => {
  const bApp = {
    id: 'dddd4444-5555-6666-7777-888899990000',
    scheme_id: 'test-scheme-rejected',
    scheme_name: 'Textile Modernization Subsidy',
    status: 'rejected',
    submitted_at: '2026-05-15T09:00:00.000Z'
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.statusBadge, 'Rejected');
  assert.equal(mapped.steps[0].status, 'completed'); // Submitted
  assert.equal(mapped.steps[1].status, 'completed'); // Verification
  assert.equal(mapped.steps[2].status, 'error'); // Approval Rejected
  assert.equal(mapped.steps[2].date, 'Rejected');
  assert.equal(mapped.steps[3].date, 'Not Applicable');
  assert.equal(mapped.steps[3].status, 'upcoming');
});

test('Phase D3.8 Frontend: 12. Action-required application indicates verification error state', () => {
  const bApp = {
    id: 'eeee5555-6666-7777-8888-999900001111',
    scheme_id: 'test-scheme-action',
    scheme_name: 'Solar Pump Subsidy',
    status: 'action_required',
    submitted_at: '2026-09-08T15:00:00.000Z'
  };

  const mapped = mapBackendApplication(bApp);
  assert.equal(mapped.statusBadge, 'Action Required');
  assert.equal(mapped.actionLabel, 'Update Documents');
  assert.equal(mapped.steps[1].status, 'error');
  assert.equal(mapped.steps[1].date, 'Action Required');
});

test('Phase D3.8 Frontend: Receipt generation produces authentic plaintext acknowledgement slip', () => {
  const app = {
    applicationId: 'FINB75FBA18',
    dbId: 'b75fba18-7b98-4449-a1fc-2216834b9d0e',
    appliedDate: '01 Sep 2026',
    statusBadge: 'Under Review',
    schemeTitle: 'Young Investigators Programme in Biotechnology (YIPB)',
    schemeSubtitle: 'Science, IT & Research',
    benefitSubtitle: 'Research Fellowship + Contingency Grant',
    benefitAmount: '₹75,000 / month (Stipend)',
    statusMessage: 'Your application is under active departmental review.',
    steps: [
      { label: 'Submitted', date: '01 Sep 2026', status: 'completed' },
      { label: 'Verification', date: 'In Progress', status: 'current-green' },
      { label: 'Approval', date: '', status: 'upcoming' },
      { label: 'Disbursement', date: '', status: 'upcoming' }
    ]
  };

  const receipt = downloadReceipt(app);
  assert.ok(receipt.includes('FINANCIAL POLICY INTELLIGENCE (FIN)'));
  assert.ok(receipt.includes('Application Identifier : FINB75FBA18'));
  assert.ok(receipt.includes('Young Investigators Programme in Biotechnology (YIPB)'));
  assert.ok(receipt.includes('₹75,000 / month (Stipend)'));
  assert.ok(receipt.includes('Under Review'));
  assert.ok(!receipt.includes('₹1,75,000'));
});
