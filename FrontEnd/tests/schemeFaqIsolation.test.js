import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Scheme FAQ Dynamic Isolation & Data Integrity Suite', async (t) => {
  await t.test('1. Scheme Details Page displays exact empty notice when no FAQs exist', () => {
    const pagePath = path.join(__dirname, '..', 'src', 'pages', 'SchemeDetailsPage.jsx');
    const content = fs.readFileSync(pagePath, 'utf8');

    assert.ok(
      content.includes('No official FAQs available for this scheme.'),
      'Must display exact requirement: "No official FAQs available for this scheme."'
    );
  });

  await t.test('2. Backend schemeService isolates FAQs strictly by slug or scheme_id', async () => {
    const backendServicePath = path.join(__dirname, '..', '..', 'BackEnd', 'src', 'services', 'schemeService.js');
    assert.ok(fs.existsSync(backendServicePath), 'Backend schemeService must exist');
    const content = fs.readFileSync(backendServicePath, 'utf8');

    // Asserts canonical FAQ indexer exists and uses slug index
    assert.ok(content.includes('getCanonicalFaqsIndex'), 'Must implement canonical FAQ index');
    assert.ok(content.includes('getFaqsBySchemeSlug'), 'Must query FAQs by scheme slug');
  });

  await t.test('3. Backend returns zero FAQs for unknown or non-existent scheme', async () => {
    const backendMod = await import('../../BackEnd/src/services/schemeService.js');
    const schemeService = backendMod.default || backendMod;
    const result = await schemeService.getFaqsBySchemeSlug('totally-non-existent-fake-scheme-id-999');

    assert.ok(result);
    assert.strictEqual(result.total, 0);
    assert.deepStrictEqual(result.faqs, []);
    assert.ok(result.notice.includes('No official FAQs available for this scheme.'));
  });

  await t.test('4. Backend returns authentic FAQs for known canonical schemes', async () => {
    const backendMod = await import('../../BackEnd/src/services/schemeService.js');
    const schemeService = backendMod.default || backendMod;
    const result108 = await schemeService.getFaqsBySchemeSlug('108easuk');
    assert.ok(result108);
    assert.ok(result108.total > 0, '108easuk must have FAQs in canonical index');
    assert.ok(result108.faqs.every(f => f.question && f.answer));

    const resultPmegp = await schemeService.getFaqsBySchemeSlug('pmegp');
    assert.ok(resultPmegp);
    assert.ok(resultPmegp.total > 0, 'pmegp must have FAQs in canonical index');

    // Verify isolation: 108easuk FAQs are distinct from pmegp FAQs
    const q108 = result108.faqs[0].question.toLowerCase();
    const qPmegp = resultPmegp.faqs[0].question.toLowerCase();
    assert.notStrictEqual(q108, qPmegp, 'FAQs must not leak between schemes');
  });
});
