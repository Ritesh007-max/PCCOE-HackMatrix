import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { fetchApplicableSchemesCatalog } from '../src/services/schemeService.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Frontend Scheme Catalog Unification & Parity Suite', async (t) => {
  await t.test('1. SchemeReadinessCombobox placeholder contains dynamic scheme count and jurisdiction label', () => {
    const comboboxPath = path.join(__dirname, '..', 'src', 'components', 'documents', 'SchemeReadinessCombobox.jsx');
    const content = fs.readFileSync(comboboxPath, 'utf8');

    // Asserts that triggerLabel dynamically interpolates schemes.length and policyState
    assert.match(content, /`-- Select from \${schemes\.length} Schemes \(\${policyState \|\| 'Gujarat'} & Central\) --`/);
  });

  await t.test('2. fetchApplicableSchemesCatalog is exported and defined', () => {
    assert.strictEqual(typeof fetchApplicableSchemesCatalog, 'function');
  });

  await t.test('3. DocumentsPage imports fetchApplicableSchemesCatalog as canonical source', () => {
    const docPagePath = path.join(__dirname, '..', 'src', 'pages', 'DocumentsPage.jsx');
    const docPageContent = fs.readFileSync(docPagePath, 'utf8');

    assert.ok(docPageContent.includes('fetchApplicableSchemesCatalog'), 'DocumentsPage must import fetchApplicableSchemesCatalog');
    assert.ok(docPageContent.includes('await fetchApplicableSchemesCatalog(stateParam)'), 'DocumentsPage must query fetchApplicableSchemesCatalog');
  });
});
