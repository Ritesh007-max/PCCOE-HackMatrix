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
} from '../src/utils/documentSchemeValidation.js';

import {
  buildDynamicSchemeChecklist,
  normalizeDocRequirementId,
} from '../src/data/documentsData.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN Phase D4.3: Scheme Readiness Logic Audit & Responsive Table UI Suite', async (t) => {

  // =========================================================================
  // TASK A & C: SCHEME READINESS LOGIC
  // =========================================================================

  await t.test('1. No arbitrary scheme is selected by default', () => {
    // Initializing state with empty selectedSchemeId produces a clean unselected state
    const readiness = evaluateSchemeReadiness(null, []);
    assert.strictEqual(readiness.schemeId, null);
    assert.strictEqual(readiness.schemeName, '');
    assert.strictEqual(readiness.status, 'NO_SCHEME_SELECTED');
    assert.strictEqual(readiness.canApply, false);
    assert.strictEqual(readiness.requirements.length, 0);
    assert.strictEqual(readiness.neutralMessage, 'Select a scheme to check document readiness.');
  });

  await t.test('2. Selected scheme ID matches the displayed scheme and maintains consistency', () => {
    const scheme = {
      id: 'sch_gujarat_scholarship',
      name: 'Gujarat Post-Matric Scholarship',
      state: 'Gujarat',
      documents_required: ['Caste Certificate', 'Income Certificate', 'Aadhaar Card'],
    };

    const userDocs = [
      {
        documentType: 'caste_cert',
        verificationStatus: 'VERIFIED',
        status: 'verified',
      },
    ];

    const evaluation = evaluateSchemeReadiness(scheme, userDocs);
    assert.strictEqual(evaluation.schemeId, 'sch_gujarat_scholarship');
    assert.strictEqual(evaluation.schemeName, 'Gujarat Post-Matric Scholarship');
    assert.strictEqual(evaluation.requirements.length, 3);
    assert.strictEqual(evaluation.verifiedCount, 1);
    assert.strictEqual(evaluation.missingCount, 2);
  });

  await t.test('3. Applicant-specific scheme filtering follows canonical applicability data', () => {
    const rawCatalog = [
      { id: 'c1', name: 'PM Kisan Samman Nidhi', level: 'Central', state: null },
      { id: 'c2', name: 'National Apprenticeship Promotion Scheme', level: 'National', state: 'All India' },
      { id: 'c3', name: 'PMEGP', level: 'Central', state: 'Central' },
      { id: 'g1', name: 'Mukhyamantri Amrutum Yojana', level: 'State', state: 'Gujarat' },
      { id: 'm1', name: 'MahaDBT Post Matric Scholarship', level: 'State', state: 'Maharashtra' },
      { id: 'k1', name: 'Karnataka Gruha Lakshmi', level: 'State', state: 'Karnataka' },
    ];

    // Applicant from Gujarat
    const gujaratSchemes = filterApplicantRelevantSchemes(rawCatalog, 'Gujarat');
    const gujaratIds = gujaratSchemes.map((s) => s.id);

    // Central schemes must be included
    assert.ok(gujaratIds.includes('c1'), 'Central PM Kisan must be included');
    assert.ok(gujaratIds.includes('c2'), 'National scheme must be included');
    assert.ok(gujaratIds.includes('c3'), 'Central PMEGP must be included');

    // Gujarat state scheme must be included
    assert.ok(gujaratIds.includes('g1'), 'Gujarat scheme must be included for Gujarat applicant');

    // Other state schemes must be excluded
    assert.ok(!gujaratIds.includes('m1'), 'Maharashtra scheme must be excluded for Gujarat applicant');
    assert.ok(!gujaratIds.includes('k1'), 'Karnataka scheme must be excluded for Gujarat applicant');

    // Verify helper isCentralScheme
    assert.strictEqual(isCentralScheme({ level: 'Central' }), true);
    assert.strictEqual(isCentralScheme({ state: 'National' }), true);
    assert.strictEqual(isCentralScheme({ state: 'All India' }), true);
    assert.strictEqual(isCentralScheme({ state: 'Maharashtra' }), false);
  });

  await t.test('4. Missing documents remain Missing', () => {
    const reqItem = { id: 'land_records', label: 'Land Record (7/12)' };
    const userDocs = [
      { documentType: 'aadhaar', verificationStatus: 'VERIFIED', status: 'verified' },
      { documentType: 'income_cert', verificationStatus: 'VERIFIED', status: 'verified' },
    ];

    const result = evaluateRequirementStatus(reqItem, userDocs);
    assert.strictEqual(result.status, 'Missing');
    assert.strictEqual(result.matchedDoc, null);
    assert.strictEqual(result.isVerified, false);
  });

  await t.test('5. Uploaded but unverified documents remain Pending Verification', () => {
    const reqItem = { id: 'income_cert', label: 'Income Certificate' };
    const userDocs = [
      {
        id: 'doc-pending-1',
        documentType: 'income_cert',
        fileName: 'income_2026.pdf',
        verificationStatus: 'PENDING',
        status: 'under_review',
      },
    ];

    const result = evaluateRequirementStatus(reqItem, userDocs);
    assert.strictEqual(result.status, 'Pending Verification');
    assert.strictEqual(result.isPending, true);
    assert.strictEqual(result.isVerified, false);
    assert.ok(result.matchedDoc !== null);
  });

  await t.test('6. OCR extraction does NOT count as verification', () => {
    const reqItem = { id: 'caste_cert', label: 'Caste Certificate' };
    const userDocsWithOcr = [
      {
        id: 'doc-ocr-1',
        documentType: 'caste_cert',
        fileName: 'caste_scan.pdf',
        verificationStatus: 'PENDING',
        status: 'under_review',
        extractedData: {
          category: 'OBC',
          certificate_no: 'OBC/2026/09912',
          confidence: 0.98,
        },
      },
    ];

    const result = evaluateRequirementStatus(reqItem, userDocsWithOcr);
    assert.strictEqual(result.status, 'Pending Verification');
    assert.strictEqual(result.isVerified, false, 'OCR extracted data must never override PENDING verification');
    assert.ok(!result.notes?.includes('Verified'), 'Notes must not claim document is verified');
  });

  await t.test('7. Verified documents satisfy matching requirements', () => {
    const reqItem = { id: 'aadhaar', label: 'Aadhaar Card' };
    const userDocs = [
      {
        id: 'doc-aadhaar-1',
        documentType: 'aadhaar',
        fileName: 'aadhaar.pdf',
        verificationStatus: 'VERIFIED',
        status: 'verified',
      },
    ];

    const result = evaluateRequirementStatus(reqItem, userDocs);
    assert.strictEqual(result.status, 'Verified');
    assert.strictEqual(result.isVerified, true);
    assert.strictEqual(result.isPending, false);
    assert.strictEqual(result.matchedDoc.id, 'doc-aadhaar-1');
  });

  await t.test('8. Missing canonical requirements produce an honest unavailable state', () => {
    // Scheme with no documents_required defined in catalog
    const schemeWithoutReqs = {
      id: 'sch_sparse_data',
      name: 'Sparse Scheme Without Requirements',
      documents_required: null,
    };

    const evaluation = evaluateSchemeReadiness(schemeWithoutReqs, []);
    assert.strictEqual(evaluation.status, 'REQUIREMENTS_UNAVAILABLE');
    assert.strictEqual(evaluation.requirements.length, 0);
    assert.strictEqual(evaluation.canApply, false);
    assert.ok(evaluation.unavailableMessage.includes('Requirements unavailable'));

    // Check buildDynamicSchemeChecklist does not fabricate fallback requirements
    const dynamicList = buildDynamicSchemeChecklist([schemeWithoutReqs]);
    assert.strictEqual(dynamicList[0].requiredDocIds.length, 0, 'Must NOT inject fake Aadhaar/Address Proof');
  });

  await t.test('9. Readiness is not represented as eligibility or approval', () => {
    const scheme = {
      id: 'sch_fully_ready',
      name: 'Fully Documented Scheme',
      documents_required: ['Aadhaar Card'],
    };
    const userDocs = [
      { documentType: 'aadhaar', verificationStatus: 'VERIFIED', status: 'verified' },
    ];

    const evaluation = evaluateSchemeReadiness(scheme, userDocs);
    assert.strictEqual(evaluation.status, 'READY');
    assert.strictEqual(evaluation.isFullyReady, true);

    // Disclaimer must clarify document completeness vs government approval/eligibility
    assert.ok(evaluation.disclaimer, 'Evaluation must provide a disclaimer');
    assert.ok(evaluation.disclaimer.includes('does not guarantee government eligibility, sanction, qualification, or official scheme approval'));
    assert.ok(!evaluation.disclaimer.includes('guaranteed approval'));
  });

  // =========================================================================
  // TASK B & C: RESPONSIVE DOCUMENTS UI & CSS INVARIANTS
  // =========================================================================

  await t.test('10. Document content and action controls remain accessible without horizontal overflow', () => {
    const cssPath = path.join(__dirname, '..', 'src', 'styles', 'documents.css');
    const cssContent = fs.readFileSync(cssPath, 'utf8');

    // 1. .docs-table-wrapper must not have a forced large min-width or overflow clipping
    assert.ok(cssContent.includes('.docs-table-wrapper {'), 'Wrapper class must exist');
    assert.ok(!cssContent.match(/\.docs-table-wrapper\s*\{[^}]*min-width:\s*\d{3,}px/i), 'Wrapper must not have a destructive min-width');

    // 2. .docs-table must be table-layout: auto or responsive with width: 100%
    assert.ok(cssContent.includes('table-layout: auto;'), 'Table layout should be auto for responsive text fitting');

    // 3. .doc-info-cell must NOT have fixed min-width: 210px that causes overflow
    assert.ok(!cssContent.includes('min-width: 210px;'), 'Destructive min-width 210px on doc-info-cell must be removed');

    // 4. .doc-purpose-cell must NOT have white-space: nowrap or fixed min-width: 140px
    assert.ok(!cssContent.match(/\.doc-purpose-cell\s*\{[^}]*min-width:\s*140px/i), 'Destructive min-width 140px on doc-purpose-cell must be removed');
    assert.ok(!cssContent.match(/\.doc-purpose-title\s*\{[^}]*white-space:\s*nowrap/i), 'white-space: nowrap on doc-purpose-title must be removed to allow wrapping');

    // 5. Word break should be enabled for responsive purpose text
    assert.ok(cssContent.includes('word-break: break-word;') || cssContent.includes('overflow-wrap: break-word;'), 'Wrap rules must be active');
  });

  await t.test('11. The document table provides responsive stacked layout for mobile / narrow viewports', () => {
    const cssPath = path.join(__dirname, '..', 'src', 'styles', 'documents.css');
    const cssContent = fs.readFileSync(cssPath, 'utf8');

    // Must have responsive media query for narrow viewports
    assert.ok(cssContent.includes('@media (max-width: 768px)'), 'Mobile media query must be defined');

    // Under max-width 768px, table elements should transition to block/stacked layout
    assert.ok(cssContent.includes('.docs-table, .docs-table tbody, .doc-row, .doc-cell'), 'Stacked table elements must be targeted');
    assert.ok(cssContent.includes('display: block;'), 'Stacked display block must be used on mobile');

    // No arbitrary global overflow-x: hidden on body/root that conceals broken content
    assert.ok(!cssContent.match(/^body\s*\{[^}]*overflow-x:\s*hidden/m), 'Must not use global overflow-x: hidden workaround');
  });

  await t.test('12. Existing document upload, view, and action functionality remains intact in DocumentsPage', () => {
    const jsxPath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const jsxContent = fs.readFileSync(jsxPath, 'utf8');

    // Verify key upload and view handlers are preserved
    assert.ok(jsxContent.includes('handleOpenUploadModal'), 'handleOpenUploadModal must be preserved');
    assert.ok(jsxContent.includes('handleProcessDirectUpload'), 'handleProcessDirectUpload must be preserved');
    assert.ok(jsxContent.includes('handleDeleteDoc'), 'handleDeleteDoc must be preserved');
    assert.ok(jsxContent.includes('setSelectedDocForView'), 'setSelectedDocForView must be preserved');
    assert.ok(jsxContent.includes('handleExportDossier'), 'handleExportDossier must be preserved');

    // Verify scheme selection dropdown and persistence
    assert.ok(jsxContent.includes('fin_selected_readiness_scheme_id'), 'sessionStorage persistence key must be used');
    assert.ok(jsxContent.includes('Select a scheme to check document readiness'), 'Neutral placeholder must be rendered');
    assert.ok(jsxContent.includes('Requirements unavailable'), 'Requirements unavailable state must be handled');

    // Verify four-tier verification badges
    assert.ok(jsxContent.includes('Pending Verification'), 'Pending Verification status must be present');
    assert.ok(jsxContent.includes('Verified'), 'Verified status must be present');
    assert.ok(jsxContent.includes('Missing'), 'Missing status must be present');
    assert.ok(jsxContent.includes('Review Required'), 'Review Required status must be present');
  });

  await t.test('13. Viewport-level overflow prevention: structural grid and flex containment invariants', () => {
    const cssPath = path.join(__dirname, '..', 'src', 'styles', 'documents.css');
    const cssContent = fs.readFileSync(cssPath, 'utf8');

    // 1. .docs-main-grid must use minmax(0, 1fr) rather than unconstrained 1fr
    assert.ok(cssContent.includes('grid-template-columns: minmax(0, 1fr) 320px;'), '.docs-main-grid must constrain column with minmax(0, 1fr)');

    // 2. .docs-metrics-row must use minmax(0, 1fr)
    assert.ok(cssContent.includes('grid-template-columns: repeat(4, minmax(0, 1fr));'), '.docs-metrics-row must use minmax(0, 1fr)');

    // 3. .docs-toolbar-row must wrap rather than nowrap
    assert.ok(cssContent.match(/\.docs-toolbar-row\s*\{[^}]*flex-wrap:\s*wrap;/), '.docs-toolbar-row must wrap to prevent horizontal blow-out');

    // 4. .docs-bottom-deck must use minmax(0, 1fr)
    assert.ok(cssContent.includes('grid-template-columns: repeat(3, minmax(0, 1fr));'), '.docs-bottom-deck must use minmax(0, 1fr)');

    // 5. Tablet & narrow breakpoint for main grid stacking
    assert.ok(cssContent.includes('@media (max-width: 1024px)'), 'Tablet breakpoint at 1024px must exist');
    assert.ok(cssContent.includes('grid-template-columns: minmax(0, 1fr);'), 'Main grid must stack at 1024px');
  });
});

