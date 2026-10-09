import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  isCentralScheme,
  filterApplicantRelevantSchemes,
  evaluateRequirementStatus,
  evaluateSchemeReadiness,
  deriveDynamicSchemeChecklist,
} from '../src/utils/documentSchemeValidation.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Scheme Readiness Selector Relevance and UX Audit Suite', async (t) => {

  const sampleCatalog = [
    {
      id: 'sch_gujarat_vahan',
      name: 'Self-Employment Scheme: Vahan Loan Sahay Yojana',
      state: 'Gujarat',
      level: 'State',
      tags: ['Gujarat', 'Self-Employment', 'Loan'],
      documents_required: ['Aadhaar Card', 'Driving License', 'Income Certificate', 'Caste Certificate'],
    },
    {
      id: 'sch_gujarat_vidhya',
      name: 'Vidhya Sadhana Yojana Gujarat',
      state: 'Gujarat',
      level: 'State',
      tags: ['Gujarat', 'Education'],
      documents_required: ['Aadhaar Card', 'School Bonafide', 'Income Certificate'],
    },
    {
      id: 'sch_tripura_pension',
      name: 'Tripura Pension Scheme For Providing Pension To Retired Home Guards',
      state: 'Tripura',
      level: 'State',
      tags: ['Tripura', 'Pension'],
      documents_required: ['Aadhaar Card', 'Domicile Certificate'],
    },
    {
      id: 'sch_wb_textile',
      name: 'West Bengal Textile Incentive Scheme',
      state: 'West Bengal',
      level: 'State',
      tags: ['West Bengal', 'Textiles'],
      documents_required: ['PAN', 'Trade License'],
    },
    {
      id: 'sch_pmegp_central',
      name: 'Prime Minister Employment Generation Programme (PMEGP)',
      state: 'All India',
      level: 'Central',
      ministry: 'Ministry of MSME',
      documents_required: ['Aadhaar Card', 'PAN', 'Project Report', 'Caste Certificate'],
    },
    {
      id: 'sch_central_pmsss',
      name: 'Prime Minister’s Special Scholarship Scheme For The Students Of Union Territories Of Jammu & Kashmir And Ladakh',
      state: 'All India',
      level: 'Central',
      ministry: 'Ministry of Education',
      documents_required: ['Domicile of J&K', 'Marksheet', 'Income Certificate'],
    },
    {
      id: 'sch_missing_jurisdiction',
      name: 'Unannotated Local Community Welfare Grant',
      state: null,
      level: null,
      tags: ['Welfare'],
      documents_required: ['Identity Proof'],
    },
    {
      id: 'sch_gujarat_no_level',
      name: 'Zupda Vijlikaran Yojana',
      state: 'Gujarat',
      level: null,
      tags: ['Gujarat', 'Electricity'],
      documents_required: ['Ration Card', 'Electricity Bill'],
    },
  ];

  await t.test('1. Gujarat-applicable schemes appear for Gujarat applicant', () => {
    const relevant = filterApplicantRelevantSchemes(sampleCatalog, 'Gujarat');
    const ids = relevant.map((s) => s.id);

    assert.ok(ids.includes('sch_gujarat_vahan'), 'Gujarat Vahan Loan Sahay must be included');
    assert.ok(ids.includes('sch_gujarat_vidhya'), 'Vidhya Sadhana Yojana Gujarat must be included');
    assert.ok(ids.includes('sch_gujarat_no_level'), 'Gujarat scheme even without explicit level must be included');
  });

  await t.test('2. Unrelated state-only schemes are excluded', () => {
    const relevant = filterApplicantRelevantSchemes(sampleCatalog, 'Gujarat');
    const ids = relevant.map((s) => s.id);

    assert.strictEqual(ids.includes('sch_tripura_pension'), false, 'Tripura pension scheme must be excluded for Gujarat');
    assert.strictEqual(ids.includes('sch_wb_textile'), false, 'West Bengal scheme must be excluded for Gujarat');
  });

  await t.test('3. Central scheme applicability is handled using canonical metadata without territory leak', () => {
    const relevant = filterApplicantRelevantSchemes(sampleCatalog, 'Gujarat');
    const ids = relevant.map((s) => s.id);

    // Genuinely national central scheme
    assert.ok(ids.includes('sch_pmegp_central'), 'National Central scheme PMEGP must be included for Gujarat applicant');

    // Central scheme restricted specifically to Jammu & Kashmir and Ladakh must NOT leak to Gujarat
    assert.strictEqual(
      ids.includes('sch_central_pmsss'),
      false,
      'Central scheme targeting J&K / Ladakh must not appear for Gujarat applicant'
    );
  });

  await t.test('4. Missing jurisdiction data is not assumed eligible', () => {
    assert.strictEqual(isCentralScheme({ state: null, level: null }), false, 'Null state and level is not central');
    assert.strictEqual(isCentralScheme({ state: '', level: '' }), false, 'Empty state and level is not central');

    const relevant = filterApplicantRelevantSchemes(sampleCatalog, 'Gujarat');
    const ids = relevant.map((s) => s.id);

    assert.strictEqual(
      ids.includes('sch_missing_jurisdiction'),
      false,
      'Scheme with missing state/level must be excluded rather than assumed eligible'
    );
  });

  await t.test('5. Search returns the correct canonical scheme in dynamic checklist', () => {
    const relevant = filterApplicantRelevantSchemes(sampleCatalog, 'Gujarat');
    const dynamic = deriveDynamicSchemeChecklist(relevant);

    // Filter by query "Vahan"
    const query = 'vahan';
    const matches = dynamic.filter(
      (s) => s.name.toLowerCase().includes(query) || s.id.toLowerCase().includes(query)
    );

    assert.strictEqual(matches.length, 1);
    assert.strictEqual(matches[0].id, 'sch_gujarat_vahan');
    assert.ok(matches[0].name.includes('Vahan Loan Sahay Yojana'));
  });

  await t.test('6. Selected scheme ID matches the readiness evaluator', () => {
    const relevant = filterApplicantRelevantSchemes(sampleCatalog, 'Gujarat');
    const dynamic = deriveDynamicSchemeChecklist(relevant);

    const targetId = 'sch_gujarat_vahan';
    const selected = dynamic.find((s) => s.id === targetId);
    assert.ok(selected, 'Target scheme must exist in dynamic checklist');

    const vaultDocs = [
      { documentType: 'aadhaar', status: 'verified', verificationStatus: 'VERIFIED' },
      { documentType: 'income_cert', status: 'under_review', verificationStatus: 'PENDING' },
    ];

    const evaluation = evaluateSchemeReadiness(selected, vaultDocs);
    assert.strictEqual(evaluation.schemeId, targetId);
    assert.strictEqual(evaluation.verifiedCount, 1);
    assert.strictEqual(evaluation.pendingCount, 1);
    assert.strictEqual(evaluation.missingCount, 2);
  });

  await t.test('7. Long scheme names do not cause layout overflow in card styling', () => {
    const cssPath = path.join(__dirname, '..', 'src', 'styles', 'documents.css');
    const cssContent = fs.readFileSync(cssPath, 'utf8');

    // 1. .checker-selected-name must have multi-line wrapping and overflow clamp
    assert.ok(cssContent.includes('.checker-selected-name'), '.checker-selected-name class must exist in CSS');
    assert.ok(cssContent.includes('word-break: break-word;'), 'Must have word-break to prevent text escaping container');
    assert.ok(cssContent.includes('-webkit-line-clamp: 2;'), 'Must have line clamp for clean multi-line display');

    // 2. .checker-select must constrain width and handle overflow
    assert.ok(cssContent.includes('.checker-select'), '.checker-select class must exist');
    assert.ok(cssContent.includes('text-overflow: ellipsis;'), 'Must use ellipsis on native select');
    assert.ok(cssContent.includes('max-width: 100%;'), 'Must be constrained to 100% card width');

    // 3. Search bar must fit inside card
    assert.ok(cssContent.includes('.checker-search-bar'), '.checker-search-bar must exist in CSS');
    assert.ok(cssContent.includes('.checker-search-input'), '.checker-search-input must exist in CSS');
  });

  await t.test('8. Existing document upload, view, and action menu functionality remains intact', () => {
    const jsxPath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const jsxContent = fs.readFileSync(jsxPath, 'utf8');

    // Critical handlers intact
    assert.ok(jsxContent.includes('handleOpenUploadModal'), 'Upload modal trigger must be preserved');
    assert.ok(jsxContent.includes('handleDeleteDoc'), 'Delete document handler must be preserved');
    assert.ok(jsxContent.includes('handleDownloadDoc'), 'Download handler must be preserved');
    assert.ok(jsxContent.includes('setSelectedDocForView'), 'Document details/view handler must be preserved');
    assert.ok(jsxContent.includes('handleOpenTicketModal'), 'Ticket/application modal handler must be preserved');

    // Floating action menu portal preserved
    assert.ok(jsxContent.includes('createPortal'), 'Action menu portal must be preserved');
    assert.ok(jsxContent.includes('computeDropdownPosition'), 'Dropdown positioning utility must be preserved');

    // Search bar inside readiness checker preserved
    assert.ok(jsxContent.includes('checker-search-input'), 'Searchable input in checker must be rendered');
    assert.ok(jsxContent.includes('checker-selected-card'), 'Selected scheme card must be rendered');
  });
});
