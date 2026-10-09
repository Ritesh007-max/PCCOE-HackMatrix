import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { validateOfficialUrl, getSchemePortalDetails } from '../src/utils/schemeDetailsHelpers.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Discovery Official Source & Metadata Completeness Suite', async (t) => {
  await t.test('1. getSchemePortalDetails dynamically extracts canonical metadata fields', () => {
    const raw = {
      id: '108easuk',
      title: 'Mukhyamantri Amrutam Yojana',
      ministry: 'Health and Family Welfare Department',
      department: 'Health and Family Welfare Department',
      state: 'Gujarat',
      level: 'State',
      categories: ['Health & Wellness', 'Social Welfare'],
      target_beneficiaries: ['BPL Families', 'Low Income Families'],
      source_url: 'https://www.myscheme.gov.in/schemes/108easuk',
      references: [
        'https://magujarat.com',
        'https://gujhealth.gujarat.gov.in'
      ]
    };

    const details = getSchemePortalDetails(raw);
    assert.strictEqual(details.department, 'Health and Family Welfare Department');
    assert.strictEqual(details.ministry, 'Health and Family Welfare Department');
    assert.strictEqual(details.schemeType, 'Health & Wellness, Social Welfare');
    assert.strictEqual(details.targetBeneficiaries, 'BPL Families, Low Income Families');
    assert.strictEqual(details.coverage, 'Gujarat (State)');
    assert.ok(details.officialWebsite, 'Official website must exist');
    assert.strictEqual(validateOfficialUrl(details.officialWebsite), details.officialWebsite);
  });

  await t.test('2. Official Website does not show "Official link not verified" when authoritative source exists', () => {
    const raw = {
      id: 'pmegp',
      title: 'Prime Minister Employment Generation Programme',
      ministry: 'Ministry of Micro, Small and Medium Enterprises',
      state: 'All India',
      level: 'Central',
      source_url: 'https://www.myscheme.gov.in/schemes/pmegp',
      references: ['https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp']
    };

    const details = getSchemePortalDetails(raw);
    assert.ok(details.officialWebsite);
    assert.notStrictEqual(details.officialWebsite, 'Official link not verified');
    assert.ok(
      details.officialWebsite.includes('kviconline.gov.in') || details.officialWebsite.includes('myscheme.gov.in'),
      'Must point to authoritative portal'
    );
  });

  await t.test('3. Rejects generic fallback URLs as scheme official websites', () => {
    assert.strictEqual(validateOfficialUrl('https://google.com'), null);
    assert.strictEqual(validateOfficialUrl('https://sarkariyojana.com/scheme'), null);
    assert.strictEqual(validateOfficialUrl('javascript:alert(1)'), null);
    assert.strictEqual(validateOfficialUrl('data:text/html,<html></html>'), null);
  });

  await t.test('4. DiscoverPage.jsx renders canonical metadata grid with all 5 required fields', () => {
    const discoverPath = path.join(__dirname, '..', 'src', 'pages', 'DiscoverPage.jsx');
    const content = fs.readFileSync(discoverPath, 'utf8');

    assert.ok(content.includes('scheme-card-meta-grid'), 'Must include scheme-card-meta-grid class');
    assert.ok(content.includes('Implementing Ministry:'), 'Must display Implementing Ministry');
    assert.ok(content.includes('Scheme Type:'), 'Must display Scheme Type');
    assert.ok(content.includes('Target Beneficiaries:'), 'Must display Target Beneficiaries');
    assert.ok(content.includes('Coverage:'), 'Must display Coverage');
    assert.ok(content.includes('Official Website:'), 'Must display Official Website');
    assert.ok(content.includes('scheme-card-meta-link'), 'Official website must be rendered with link class');
  });

  await t.test('5. discover.css contains responsive styling for canonical metadata grid', () => {
    const cssPath = path.join(__dirname, '..', 'src', 'styles', 'discover.css');
    const cssContent = fs.readFileSync(cssPath, 'utf8');

    assert.ok(cssContent.includes('.scheme-card-meta-grid'), 'Must define .scheme-card-meta-grid');
    assert.ok(cssContent.includes('.scheme-card-meta-row'), 'Must define .scheme-card-meta-row');
    assert.ok(cssContent.includes('.scheme-card-meta-key'), 'Must define .scheme-card-meta-key');
    assert.ok(cssContent.includes('.scheme-card-meta-val'), 'Must define .scheme-card-meta-val');
    assert.ok(cssContent.includes('.scheme-card-meta-link'), 'Must define .scheme-card-meta-link');
  });
});
