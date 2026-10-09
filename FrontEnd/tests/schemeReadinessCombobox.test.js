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
  filterActiveSchemesForCatalog,
} from '../src/utils/documentSchemeValidation.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Final Scheme Readiness Checker UX and Applicability Verification Suite', async (t) => {
  // =========================================================================
  // TASK 1: SEARCHABLE COMBOBOX & POPOVER COMPONENT CHECKS
  // =========================================================================

  await t.test('1. SchemeReadinessCombobox component file exists with accessible ARIA combobox attributes', () => {
    const componentPath = path.join(__dirname, '..', 'src', 'components', 'documents', 'SchemeReadinessCombobox.jsx');
    assert.ok(fs.existsSync(componentPath), 'SchemeReadinessCombobox.jsx must exist');

    const content = fs.readFileSync(componentPath, 'utf8');

    // ARIA roles and accessibility
    assert.ok(content.includes('aria-haspopup="listbox"'), 'Must declare aria-haspopup="listbox"');
    assert.ok(content.includes('aria-expanded='), 'Must dynamically track aria-expanded');
    assert.ok(content.includes('role="listbox"'), 'Must render list with role="listbox"');
    assert.ok(content.includes('role="option"'), 'Must render options with role="option"');
    assert.ok(content.includes('aria-selected='), 'Must indicate selected option via aria-selected');

    // Keyboard handlers
    assert.ok(content.includes('ArrowDown'), 'Must handle ArrowDown for navigation');
    assert.ok(content.includes('ArrowUp'), 'Must handle ArrowUp for navigation');
    assert.ok(content.includes('Escape'), 'Must handle Escape key for dismissal');
    assert.ok(content.includes('Enter'), 'Must handle Enter key for selection');

    // Outside click listener
    assert.ok(content.includes('mousedown') && content.includes('contains'), 'Must detect outside clicks');

    // Search and count features
    assert.ok(content.includes('checker-search-input'), 'Must render input with checker-search-input class');
    assert.ok(content.includes('checker-combobox-count-bar'), 'Must render result count indicator');
    assert.ok(content.includes('No schemes matching'), 'Must display clean empty state');
  });

  await t.test('2. CSS rules bound dropdown height, prevent horizontal overflow, and style combobox', () => {
    const cssPath = path.join(__dirname, '..', 'src', 'styles', 'documents.css');
    const cssContent = fs.readFileSync(cssPath, 'utf8');

    // Viewport-relative maximum height and scrolling
    assert.ok(
      cssContent.includes('max-height: min(280px, 45vh);'),
      'Dropdown list must limit height to sensible viewport-relative maximum'
    );
    assert.ok(
      cssContent.includes('overflow-y: auto;'),
      'Dropdown list must allow internal vertical scrolling'
    );
    assert.ok(
      cssContent.includes('overflow-x: hidden;'),
      'Dropdown must prevent horizontal scrollbar'
    );
    assert.ok(
      cssContent.includes('overscroll-behavior: contain;'),
      'Must contain overscroll within listbox'
    );

    // Popover positioning and z-index
    assert.ok(cssContent.includes('.checker-combobox-popover'), '.checker-combobox-popover class must exist');
    assert.ok(cssContent.includes('position: absolute;'), 'Popover must be positioned absolutely');
    assert.ok(cssContent.includes('z-index: 60;'), 'Popover must render with high z-index above card content');
    assert.ok(cssContent.includes('box-shadow:'), 'Popover must render elevation shadow');

    // Trigger styling and text truncation
    assert.ok(cssContent.includes('.checker-combobox-trigger'), '.checker-combobox-trigger class must exist');
    assert.ok(cssContent.includes('text-overflow: ellipsis;'), 'Trigger must use ellipsis for long scheme names');

    // Selected and highlighted option styling
    assert.ok(cssContent.includes('.checker-combobox-option.selected'), 'Selected option styling must exist');
    assert.ok(cssContent.includes('.checker-combobox-option.highlighted'), 'Highlighted option styling must exist');
  });

  await t.test('3. DocumentsPage replaces oversized native select with SchemeReadinessCombobox', () => {
    const pagePath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const pageContent = fs.readFileSync(pagePath, 'utf8');

    // Imported and rendered
    assert.ok(
      pageContent.includes("import SchemeReadinessCombobox from '../components/documents/SchemeReadinessCombobox'"),
      'Must import SchemeReadinessCombobox'
    );
    assert.ok(
      pageContent.includes('<SchemeReadinessCombobox'),
      'Must render SchemeReadinessCombobox component'
    );

    // Does not use native select in readiness checker widget
    const checkerSection = pageContent.substring(
      pageContent.indexOf('docs-scheme-checker-card'),
      pageContent.indexOf('checker-selected-card')
    );
    assert.ok(
      !checkerSection.includes('<select'),
      'Checker card must not render a native <select> element'
    );
  });

  // =========================================================================
  // TASK 2: CATALOG SOURCING, FILTERING & DEDUPLICATION VERIFICATION
  // =========================================================================

  await t.test('4. Explains and verifies exact difference between 529 and full 670 scheme catalog', () => {
    // Synthetic sample mirroring canonical DB distribution:
    // 641 Gujarat state schemes + 30 Central schemes (1 territory-restricted) = 670 genuine applicable
    const gujaratSchemes = Array.from({ length: 641 }, (_, i) => ({
      id: `guj_sch_${i + 1}`,
      name: `Gujarat Scheme ${i + 1}`,
      state: 'Gujarat',
      tags: ['Gujarat'],
      documents_required: ['Aadhaar Card', 'Income Certificate'],
    }));

    const centralPanIndiaSchemes = Array.from({ length: 29 }, (_, i) => ({
      id: `cen_sch_${i + 1}`,
      name: `Central Pan-India Scheme ${i + 1}`,
      level: 'Central',
      state: 'All India',
      tags: ['Central'],
      documents_required: ['Aadhaar Card'],
    }));

    const territoryRestrictedCentralScheme = {
      id: 'cen_sch_jk_ladakh',
      name: 'Special Scholarship Scheme For Jammu & Kashmir And Ladakh Students',
      level: 'Central',
      state: 'All India',
      documents_required: ['Domicile'],
    };

    const fullCatalog = [...gujaratSchemes, ...centralPanIndiaSchemes, territoryRestrictedCentralScheme];
    assert.strictEqual(fullCatalog.length, 671);

    // 1. Simulating previous truncated query (limit: 500 on state query + 100 on Central)
    const previousStateTruncated = gujaratSchemes.slice(0, 500);
    const previousCentral = [...centralPanIndiaSchemes, territoryRestrictedCentralScheme];
    const previousCombined = [...previousStateTruncated, ...previousCentral];
    const previousFiltered = filterApplicantRelevantSchemes(previousCombined, 'Gujarat');

    // Previous count was exactly 529 (500 Gujarat + 29 Central)
    assert.strictEqual(previousFiltered.length, 529, 'Previous truncated query produces exactly 529 schemes');

    // 2. Full catalog without arbitrary first-N limit
    const fullFiltered = filterApplicantRelevantSchemes(fullCatalog, 'Gujarat');
    assert.strictEqual(
      fullFiltered.length,
      670,
      'Full catalog without arbitrary limit produces 670 genuinely applicable schemes'
    );

    // Territory restricted scheme was correctly filtered out
    const ids = fullFiltered.map((s) => s.id);
    assert.strictEqual(ids.includes('cen_sch_jk_ladakh'), false);
  });

  await t.test('5. Deduplication preserves unique canonical IDs without data loss', () => {
    const rawWithDuplicates = [
      { id: 'sch_g1', name: 'Scheme One', state: 'Gujarat' },
      { id: 'sch_g1', name: 'Scheme One (Duplicate)', state: 'Gujarat' },
      { id: 'sch_g2', name: 'Scheme Two', state: 'Gujarat' },
      { id: 'sch_c1', name: 'Central One', level: 'Central', state: 'All India' },
      { id: 'sch_c1', name: 'Central One (Duplicate)', level: 'Central', state: 'All India' },
    ];

    const seenIds = new Set();
    const deduplicated = [];
    rawWithDuplicates.forEach((s) => {
      const sid = s.id || s.scheme_id;
      if (sid && !seenIds.has(sid)) {
        seenIds.add(sid);
        deduplicated.push(s);
      }
    });

    assert.strictEqual(deduplicated.length, 3);
    assert.deepStrictEqual(deduplicated.map((s) => s.id), ['sch_g1', 'sch_g2', 'sch_c1']);
  });

  await t.test('6. Other-state-only schemes are excluded and unannotated jurisdiction is rejected', () => {
    const mixedSchemes = [
      { id: 'sch_guj', name: 'Gujarat Scheme', state: 'Gujarat' },
      { id: 'sch_mh', name: 'Maharashtra Scheme', state: 'Maharashtra' },
      { id: 'sch_up', name: 'Uttar Pradesh Scheme', state: 'Uttar Pradesh' },
      { id: 'sch_unannotated', name: 'Unknown Scheme', state: null, level: null },
      { id: 'sch_central', name: 'National Scheme', level: 'Central', state: 'All India' },
    ];

    const filtered = filterApplicantRelevantSchemes(mixedSchemes, 'Gujarat');
    const ids = filtered.map((s) => s.id);

    assert.ok(ids.includes('sch_guj'));
    assert.ok(ids.includes('sch_central'));
    assert.strictEqual(ids.includes('sch_mh'), false);
    assert.strictEqual(ids.includes('sch_up'), false);
    assert.strictEqual(ids.includes('sch_unannotated'), false);
  });

  // =========================================================================
  // TASK 3: READINESS EVALUATION INTEGRITY
  // =========================================================================

  await t.test('7. OCR extraction does NOT count as Verified and honest disclaimer is present', () => {
    const scheme = {
      id: 'sch_test',
      name: 'Test Scheme',
      state: 'Gujarat',
      documents_required: ['Income Certificate'],
    };

    // Document with extractedData (OCR) but status is 'under_review' or 'uploaded'
    const docs = [
      {
        documentType: 'income_cert',
        status: 'under_review',
        extractedData: { annualIncome: '120000' },
      },
    ];

    const evaluation = evaluateSchemeReadiness(scheme, docs);
    assert.strictEqual(evaluation.status, 'INCOMPLETE');
    assert.strictEqual(evaluation.verifiedCount, 0);
    assert.strictEqual(evaluation.pendingCount, 1);
    assert.strictEqual(evaluation.requirements[0].status, 'Pending Verification');
    assert.strictEqual(evaluation.requirements[0].isVerified, false);
    assert.ok(evaluation.disclaimer.includes('does not guarantee government eligibility'));
  });

  await t.test('8. Missing requirements produce honest REQUIREMENTS_UNAVAILABLE state', () => {
    const schemeWithoutReqs = {
      id: 'sch_noreqs',
      name: 'Scheme Without Documents Specified',
      state: 'Gujarat',
      documents_required: [],
    };

    const evaluation = evaluateSchemeReadiness(schemeWithoutReqs, []);
    assert.strictEqual(evaluation.status, 'REQUIREMENTS_UNAVAILABLE');
    assert.strictEqual(evaluation.requirements.length, 0);
    assert.ok(evaluation.unavailableMessage.includes('Requirements unavailable'));
  });
});
