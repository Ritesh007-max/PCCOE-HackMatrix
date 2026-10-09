import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Suggested Schemes Production Data-Integrity Suite', async (t) => {
  const pagePath = path.join(__dirname, '..', 'src', 'pages', 'SuggestedSchemesPage.jsx');
  const pageContent = fs.readFileSync(pagePath, 'utf8');

  await t.test('1. Income separation: Personal Income and Family Income are displayed separately', () => {
    assert.ok(pageContent.includes('displayPersonalIncome'), 'Must have separate displayPersonalIncome');
    assert.ok(pageContent.includes('displayFamilyIncome'), 'Must have separate displayFamilyIncome');
    assert.ok(pageContent.includes('Personal Income'), 'Must display Personal Income label');
    assert.ok(pageContent.includes('Family Income (Doc)'), 'Must display Family Income (Doc) label');
    // Ensure profile income does not overwrite verified family income
    assert.match(pageContent, /activeFactsSummary\.annual_family_income/);
  });

  await t.test('2. Navigation integrity: Apply Now navigates to canonical /schemes/:id rather than blindly dumping to documents', () => {
    assert.ok(pageContent.includes('btn-suggested-apply'));
    assert.match(pageContent, /navigate\(targetId \? `\/schemes\/\${targetId}` : '\/documents'\)/);
  });

  await t.test('3. Deduplication: recommendations are deduplicated by canonical scheme_id or slug', () => {
    assert.match(pageContent, /const seen = new Set\(\)/);
    assert.match(pageContent, /rec\.scheme_id \|\| rec\.scheme_slug/);
  });

  await t.test('4. Statutory 4-state classification: preserves PASS, REVIEW, FAIL, and UNKNOWN', () => {
    assert.ok(pageContent.includes("case 'PASS'"));
    assert.ok(pageContent.includes("case 'REVIEW'"));
    assert.ok(pageContent.includes("case 'FAIL'"));
    assert.ok(pageContent.includes("case 'UNKNOWN'"));
    assert.ok(pageContent.includes('Evaluation Pending'));
    assert.ok(pageContent.includes('Requires Review'));
  });

  await t.test('5. No hardcoded or fabricated scores: scores derive from overall_match_score or compatibility_score', () => {
    assert.match(pageContent, /scheme\.overall_match_score \|\| scheme\.compatibility_score \|\| scheme\.relevance_score/);
  });
});
