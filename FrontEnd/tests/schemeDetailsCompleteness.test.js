import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { getSchemePortalDetails, parseApplicationProcess } from '../src/utils/schemeDetailsHelpers.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Scheme Details Completeness & Application Flow Suite', async (t) => {
  await t.test('1. Deep-linking /schemes/:id maps exact canonical scheme ID', () => {
    const pagePath = path.join(__dirname, '..', 'src', 'pages', 'SchemeDetailsPage.jsx');
    const content = fs.readFileSync(pagePath, 'utf8');

    // Asserts useParams extracts routeSchemeId and queries backend API directly
    assert.ok(content.includes('useParams()'), 'Must use useParams to extract route schemeId');
    assert.ok(content.includes('fetchSchemeById(schemeId)'), 'Must call backend fetchSchemeById with exact id');
  });

  await t.test('2. Documents tab renders honest "Not specified" state when requirements are empty', () => {
    const pagePath = path.join(__dirname, '..', 'src', 'pages', 'SchemeDetailsPage.jsx');
    const content = fs.readFileSync(pagePath, 'utf8');

    assert.ok(content.includes('Document Requirements Not Specified'), 'Must render honest unstated state');
    assert.ok(
      content.includes('Specific document requirements are not detailed in the official scheme record'),
      'Must explain document omission truthfully without fabricating requirements'
    );
  });

  await t.test('3. How To Apply parses step-by-step processes dynamically', () => {
    const rawProcess = `
      Step 1: Register on the official portal using Aadhaar and mobile number.
      Step 2: Fill out the application form with bank account and landholding details.
      Step 3: Upload required documents and submit the application for verification.
    `;

    const steps = parseApplicationProcess(rawProcess);
    assert.ok(Array.isArray(steps));
    assert.strictEqual(steps.length, 3);
    assert.strictEqual(String(steps[0].step), '1');
    assert.ok(steps[0].title.includes('Step 1'));
    assert.ok(steps[0].desc.includes('Register'));
    assert.strictEqual(String(steps[1].step), '2');
    assert.strictEqual(String(steps[2].step), '3');
  });

  await t.test('4. How To Apply renders official application CTA button pointing to verified portal', () => {
    const pagePath = path.join(__dirname, '..', 'src', 'pages', 'SchemeDetailsPage.jsx');
    const content = fs.readFileSync(pagePath, 'utf8');

    assert.ok(content.includes('Apply via Official Portal'), 'Must render Official Portal application CTA');
    assert.ok(content.includes('Proceed to Official Application'), 'Must provide link to official application');
  });

  await t.test('5. Source & Rules renders Authoritative Scheme Portal and Departmental Portal', () => {
    const pagePath = path.join(__dirname, '..', 'src', 'pages', 'SchemeDetailsPage.jsx');
    const content = fs.readFileSync(pagePath, 'utf8');

    assert.ok(content.includes('Official Scheme Portal & Authoritative Source'), 'Must render Official Scheme Portal');
    assert.ok(content.includes('Implementing Authority Departmental Portal'), 'Must render Implementing Authority Departmental Portal');
    assert.ok(content.includes('Visit Official Portal'), 'Must render Visit Official Portal button');
  });
});
