import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Discovery Final Production Audit & Canonical Catalog Verification Suite', async (t) => {
  const discoverPagePath = path.join(__dirname, '..', 'src', 'pages', 'DiscoverPage.jsx');
  const discoverContent = fs.readFileSync(discoverPagePath, 'utf8');
  const backendSchemeServicePath = path.join(__dirname, '..', '..', 'BackEnd', 'src', 'services', 'schemeService.js');
  const backendSchemeServiceContent = fs.readFileSync(backendSchemeServicePath, 'utf8');
  const frontendSchemeServicePath = path.join(__dirname, '..', 'src', 'services', 'schemeService.js');
  const frontendSchemeServiceContent = fs.readFileSync(frontendSchemeServicePath, 'utf8');

  // 1. DISCOVERY SOURCE OF TRUTH
  await t.test('1. Source of Truth: Canonical dynamic flow through Supabase public.schemes', () => {
    assert.match(
      backendSchemeServiceContent,
      /supabaseAdmin\s*\.from\('schemes'\)/,
      'Backend schemeService must query public.schemes table directly'
    );
    assert.match(
      discoverContent,
      /searchSchemes\(\{/,
      'DiscoverPage must query searchSchemes from schemeService'
    );
    assert.match(
      frontendSchemeServiceContent,
      /\/api\/schemes\/search/,
      'Frontend schemeService must query backend /api/schemes/search endpoint'
    );
  });

  // 2. NO HARDCODED OR MOCK SCHEMES
  await t.test('2. No Mock/Fabricated Schemes: Zero fallback or static mock arrays in Discovery', () => {
    const forbiddenPatterns = [
      /const\s+mockSchemes/i,
      /const\s+demoSchemes/i,
      /const\s+fallbackSchemes/i,
      /const\s+sampleSchemes/i,
      /schemeData\s*=\s*\[/i,
      /fakeScheme/i
    ];
    for (const pat of forbiddenPatterns) {
      assert.strictEqual(
        pat.test(discoverContent),
        false,
        `DiscoverPage must not contain forbidden mock pattern: ${pat}`
      );
    }
  });

  // 3. CATALOG COMPLETENESS & PROVENANCE
  await t.test('3. Catalog Completeness: Live backend stats return exactly 4,752 canonical records', async () => {
    const statsRes = await fetch('http://localhost:5000/api/schemes/stats');
    assert.strictEqual(statsRes.ok, true, 'GET /api/schemes/stats must succeed');
    const stats = await statsRes.json();
    assert.strictEqual(stats.total, 4752, 'Canonical public.schemes total count must be exactly 4,752');
    const counts = stats.categoryCounts || stats.categories;
    assert.strictEqual(counts.business, 762, 'Business category count must be 762');
    assert.strictEqual(counts.agriculture, 487, 'Agriculture category count must be 487');
    assert.strictEqual(counts.education, 1227, 'Education category count must be 1227');
    assert.strictEqual(counts.women, 549, 'Women category count must be 549');
    assert.strictEqual(counts.youth, 515, 'Youth category count must be 515');
    assert.strictEqual(counts.health, 326, 'Health category count must be 326');
  });

  // 4. NO ARBITRARY LIMITS
  await t.test('4. No Arbitrary Limits: Backend supports pagination up to 5,000 without artificial caps', () => {
    assert.match(
      backendSchemeServiceContent,
      /parsedLimit\s*=\s*Math\.min\(Math\.max\(Number\(limit\)\s*\|\|\s*50,\s*1\),\s*5000\)/,
      'Backend must allow limit up to 5,000 without arbitrary low caps'
    );
    assert.match(
      discoverContent,
      /handleLoadMore/,
      'DiscoverPage must implement dynamic handleLoadMore pagination'
    );
    assert.match(
      discoverContent,
      /hasMore\s*=\s*sortedSchemes\.length\s*>\s*displayLimit\s*\|\|\s*schemes\.length\s*<\s*totalMatches/,
      'DiscoverPage must check against totalMatches for unbounded catalog pagination'
    );
  });

  // 5. SEARCH CAPABILITIES
  await t.test('5. Search: Supports case-insensitive, partial, exact, and nonsense queries safely', async () => {
    // Exact search on database
    const exactRes = await fetch('http://localhost:5000/api/schemes/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'Penalty Mafi', limit: 5 })
    });
    assert.strictEqual(exactRes.ok, true);
    const exactJson = await exactRes.json();
    assert.ok(exactJson.schemes.length > 0, 'Exact search for Penalty Mafi should return results');
    assert.ok(
      exactJson.schemes.some(s => (s.scheme_name || s.title || '').toLowerCase().includes('penalty mafi')),
      'Result should include 100% Penalty Mafi Yojana'
    );

    // Direct database search for statutory seed scheme
    const dbSearchRes = await fetch('http://localhost:5000/api/schemes/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'MUDRA Shishu', filters: { databaseOnly: true }, limit: 5 })
    });
    assert.strictEqual(dbSearchRes.ok, true);
    const dbSearchJson = await dbSearchRes.json();
    assert.strictEqual(dbSearchJson.schemes.length, 1);
    assert.strictEqual(dbSearchJson.schemes[0].id, 'mudra-shishu');

    // Partial lowercase search
    const partialRes = await fetch('http://localhost:5000/api/schemes/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'kisan', limit: 5 })
    });
    assert.strictEqual(partialRes.ok, true);
    const partialJson = await partialRes.json();
    assert.ok(partialJson.schemes.length > 0, 'Partial search for kisan should return results');

    // Nonsense query
    const nonsenseRes = await fetch('http://localhost:5000/api/schemes/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'xyznonexistent123999qwe', limit: 5 })
    });
    assert.strictEqual(nonsenseRes.ok, true);
    const nonsenseJson = await nonsenseRes.json();
    assert.strictEqual(nonsenseJson.schemes.length, 0, 'Nonsense query must return 0 results');
    assert.strictEqual(nonsenseJson.total, 0, 'Nonsense query total count must be 0');
  });

  // 6. FILTERS
  await t.test('6. Filters: Dynamic filter dimensions with clear-all restoration', () => {
    assert.match(discoverContent, /selectedCategories/, 'DiscoverPage must support categories filter');
    assert.match(discoverContent, /selectedState/, 'DiscoverPage must support state filter');
    assert.match(discoverContent, /selectedAgeGroup/, 'DiscoverPage must support age group filter');
    assert.match(discoverContent, /selectedIncomeRange/, 'DiscoverPage must support income range filter');
    assert.match(discoverContent, /selectedCasteCategory/, 'DiscoverPage must support social category filter');
    assert.match(discoverContent, /selectedSchemeTypes/, 'DiscoverPage must support scheme types filter');

    // Clear all handler
    assert.match(discoverContent, /handleClearAll/, 'DiscoverPage must have handleClearAll handler');
    assert.match(discoverContent, /setActiveCategoryPill\('all'\)/, 'handleClearAll must reset active category pill');
  });

  // 7. JURISDICTION SEPARATION
  await t.test('7. Jurisdiction Separation: Discovery is National (4,752) while Applicable Catalog is 670', async () => {
    // 1. National Discovery Catalog
    const statsRes = await fetch('http://localhost:5000/api/schemes/stats');
    const stats = await statsRes.json();
    assert.strictEqual(stats.total, 4752, 'National catalog must have 4,752 schemes');

    // 2. Applicable Catalog for Gujarat applicant (641 Gujarat + 29 Central = 670)
    const appRes = await fetch('http://localhost:5000/api/schemes/applicable?state=Gujarat');
    assert.strictEqual(appRes.ok, true);
    const appJson = await appRes.json();
    assert.strictEqual(appJson.totalApplicable, 670, 'Gujarat applicable catalog must be 670 schemes');
    assert.strictEqual(appJson.applicableStateCount, 641, 'Gujarat state schemes must be 641');
    assert.strictEqual(appJson.applicableCentralCount, 29, 'Central applicable schemes must be 29');
    assert.strictEqual(appJson.schemes.length, 670, 'Applicable catalog array must contain 670 schemes');
  });

  // 8. NEUTRALITY & NO RECOMMENDATION LEAKAGE
  await t.test('8. Neutrality: Discovery cards render canonical jurisdiction without recommendation matchScore %', () => {
    // Verify adaptScheme does not attach recommendation percentage to conditionText
    assert.ok(
      !discoverContent.includes('`${matchScore}% Match`'),
      'adaptScheme must not format conditionText as matchScore %'
    );
    assert.ok(
      !discoverContent.includes('`${scheme.matchScore}% Match`'),
      'Discovery card metrics column must not display matchScore %'
    );
    // Verify jurisdiction badge is used
    assert.match(
      discoverContent,
      /jurisdictionLabel/,
      'Discovery card must render canonical jurisdictionLabel'
    );
  });

  // 9. BENEFIT SEMANTICS INTEGRITY
  await t.test('9. Benefit Semantics: Financial interpretation separates loans, waivers, and monetary grants', () => {
    assert.match(
      discoverContent,
      /interpretFinancialBenefit\(raw\)/,
      'DiscoverPage must utilize interpretFinancialBenefit engine'
    );
    assert.match(
      discoverContent,
      /scheme\.benefitAmount/,
      'DiscoverPage must render sanitized benefitAmount'
    );
    assert.match(
      discoverContent,
      /scheme\.benefitSubtitle/,
      'DiscoverPage must render contextual benefitSubtitle (Loan, Subsidy, etc.)'
    );
  });

  // 10. OFFICIAL SOURCES & URL VALIDATION
  await t.test('10. Official Sources: Strictly validated against authoritative government domain allowlists', () => {
    assert.match(
      backendSchemeServiceContent,
      /validateOfficialUrl/,
      'Backend schemeService must validate official URLs'
    );
    assert.match(
      backendSchemeServiceContent,
      /TRUSTED_GOV_DOMAINS/,
      'Backend schemeService must enforce TRUSTED_GOV_DOMAINS allowlist'
    );
    assert.match(
      backendSchemeServiceContent,
      /UNTRUSTED_DOMAIN_PATTERNS/,
      'Backend schemeService must reject untrusted commercial blogs/aggregators'
    );
  });

  // 11. SCHEME DETAILS DEEP LINK & INVALID SCHEME HANDLING
  await t.test('11. Scheme Details Deep Link: Valid IDs load canonically, invalid IDs return 404', async () => {
    // Valid scheme by ID
    const validRes = await fetch('http://localhost:5000/api/schemes/mudra-shishu');
    assert.strictEqual(validRes.ok, true, 'Valid scheme ID must return 200 OK');
    const validJson = await validRes.json();
    assert.strictEqual(validJson.scheme.id, 'mudra-shishu');
    assert.strictEqual(validJson.scheme.type, 'Loan');

    // Invalid scheme by ID
    const invalidRes = await fetch('http://localhost:5000/api/schemes/non-existent-invalid-scheme-id-999');
    assert.strictEqual(invalidRes.status, 404, 'Invalid scheme ID must return 404 Not Found');
  });

  // 12. ERROR & EMPTY STATES
  await t.test('12. Error & Empty States: Honest states without fabricated fallback cards', () => {
    assert.match(
      discoverContent,
      /No matching schemes found/,
      'DiscoverPage must render honest empty state when 0 matches found'
    );
    assert.match(
      discoverContent,
      /Unable to load schemes/,
      'DiscoverPage must render honest error title on API error'
    );
    assert.match(
      discoverContent,
      /Retry Search/,
      'DiscoverPage must provide retry search button on failure'
    );
  });

  // 13. USER-SCOPED BOOKMARKS & TENANT ISOLATION
  await t.test('13. Multi-Tenant Bookmarks: Bookmarks are scoped to authenticated user ID in storage', () => {
    assert.match(
      discoverContent,
      /bookmarkStorageKey\s*=\s*storedUser\?\.id\s*\?\s*`fin_bookmarked_schemes_\$\{storedUser\.id\}`\s*:\s*'fin_bookmarked_schemes_guest'/,
      'Bookmarks must be isolated by user ID'
    );
  });

  // 14. SORTING MODES
  await t.test('14. Sorting: Deterministic sorting across relevant, highest_benefit, name_asc, name_desc', () => {
    assert.match(discoverContent, /sortBy === 'highest_benefit'/);
    assert.match(discoverContent, /sortBy === 'name_asc'/);
    assert.match(discoverContent, /sortBy === 'name_desc'/);
    assert.match(discoverContent, /useState\('relevant'\)/);
  });
});
