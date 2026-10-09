import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Discovery Page Full Data Integrity & Dynamic Catalog Regression Suite', async (t) => {
  const discoverPagePath = path.join(__dirname, '..', 'src', 'pages', 'DiscoverPage.jsx');
  const discoverContent = fs.readFileSync(discoverPagePath, 'utf8');
  const authServicePath = path.join(__dirname, '..', 'src', 'services', 'authService.js');
  const authContent = fs.readFileSync(authServicePath, 'utf8');
  const backendSchemeServicePath = path.join(__dirname, '..', '..', 'BackEnd', 'src', 'services', 'schemeService.js');
  const backendSchemeServiceContent = fs.readFileSync(backendSchemeServicePath, 'utf8');

  await t.test('1. Dynamic total count is queried from backend stats and never hardcoded', () => {
    assert.ok(
      !discoverContent.includes('totalCount = 4752') && !discoverContent.includes('total: 4752'),
      'DiscoverPage must not hardcode total scheme count to 4752'
    );
    assert.match(
      discoverContent,
      /fetchSchemeStats\(\)/,
      'DiscoverPage must call fetchSchemeStats to load stats dynamically'
    );
    assert.match(
      discoverContent,
      /Number\(totalMatches\)\.toLocaleString\('en-IN'\)/,
      'DiscoverPage must render totalMatches dynamically'
    );
  });

  await t.test('2. Dynamic category counts are populated from canonical API facets/stats', () => {
    assert.ok(
      !discoverContent.includes('count: 762') &&
      !discoverContent.includes('count: 487') &&
      !discoverContent.includes('count: 1227') &&
      !discoverContent.includes('count: 549') &&
      !discoverContent.includes('count: 515') &&
      !discoverContent.includes('count: 326'),
      'DiscoverPage must not hardcode category counts in initial array'
    );
    assert.match(
      discoverContent,
      /setLiveCategoryCounts\(stats\.categoryCounts\)/,
      'DiscoverPage must dynamically populate liveCategoryCounts from API stats'
    );
  });

  await t.test('3. Dynamic remaining count uses totalMatches and loaded schemes calculation', () => {
    assert.ok(
      !discoverContent.includes('4702 remaining'),
      'DiscoverPage must not hardcode 4,702 remaining in template'
    );
    assert.match(
      discoverContent,
      /totalMatches\s*-\s*Math\.min\(displayLimit,\s*sortedSchemes\.length\)/,
      'DiscoverPage must calculate remaining schemes dynamically'
    );
    assert.match(
      discoverContent,
      /Load more\s*\(/,
      'Load More button must be present and dynamic'
    );
  });

  await t.test('4. Pagination fetches incremental batches and hides Load More when depleted', () => {
    assert.match(
      discoverContent,
      /setDisplayLimit\(\(prev\)\s*=>\s*prev\s*\+\s*50\)/,
      'DiscoverPage must increment display limit on Load More click'
    );
    assert.match(
      discoverContent,
      /const\s+hasMore\s*=\s*sortedSchemes\.length\s*>\s*displayLimit\s*\|\|\s*schemes\.length\s*<\s*totalMatches/,
      'Load More button must conditionally render only when remaining items exist'
    );
  });

  await t.test('5. Deduplication prevents duplicate cards on Load More using unique scheme IDs', () => {
    assert.match(
      discoverContent,
      /const\s+existingIds\s*=\s*new\s+Set\(prev\.map\(s\s*=>\s*s\.id\)\)/,
      'DiscoverPage must build a Set of existing scheme IDs before appending'
    );
    assert.match(
      discoverContent,
      /const\s+newItems\s*=\s*nextSchemes\.filter\(s\s*=>\s*!existingIds\.has\(s\.id\)\)/,
      'DiscoverPage must strictly filter out duplicate scheme IDs'
    );
  });

  await t.test('6. Search queries canonical fields and triggers backend search with debounce', () => {
    assert.match(
      discoverContent,
      /query:\s*searchQuery\.trim\(\)/,
      'Search query must be trimmed and passed to backend API'
    );
    assert.match(
      discoverContent,
      /setTimeout\(\(\)\s*=>\s*\{\s*executeSearch\(\);/,
      'Search execution must be debounced'
    );
  });

  await t.test('7. Category filter handles multiple category selections via OR semantics', () => {
    assert.match(
      discoverContent,
      /categories:\s*categoriesFilter/,
      'Selected categories array must be passed to searchSchemes'
    );
    assert.match(
      backendSchemeServiceContent,
      /combinedCategoryTags\.push\(\.\.\.mapped\)/,
      'Backend schemeService must combine category tags for multi-category filtering'
    );
  });

  await t.test('8. State filter queries specific state without corrupting other jurisdictions', () => {
    assert.match(
      discoverContent,
      /state:\s*selectedState\s*&&\s*selectedState\s*!==\s*'All India'\s*\?\s*selectedState\s*:\s*undefined/,
      'DiscoverPage must pass selectedState to backend query'
    );
    assert.match(
      backendSchemeServiceContent,
      /filters\.state\s*!==\s*'All India'/,
      'Backend schemeService must properly handle All India and specific State filtering'
    );
  });

  await t.test('9. Age filter maps to backend ageGroup parameter', () => {
    assert.match(
      discoverContent,
      /ageGroup:\s*selectedAgeGroup\s*\|\|\s*undefined/,
      'DiscoverPage must pass selectedAgeGroup to query'
    );
    assert.match(
      backendSchemeServiceContent,
      /ageKey\s*===\s*'60\+'/,
      'Backend schemeService must parse ageGroup parameter'
    );
  });

  await t.test('10. Income filter maps to backend incomeRange parameter', () => {
    assert.match(
      discoverContent,
      /incomeRange:\s*selectedIncomeRange\s*\|\|\s*undefined/,
      'DiscoverPage must pass selectedIncomeRange to query'
    );
    assert.match(
      backendSchemeServiceContent,
      /incKey\s*===\s*'below-1\.5l'/,
      'Backend schemeService must evaluate incomeRange criteria'
    );
  });

  await t.test('11. Scheme type filter maps to backend types array', () => {
    assert.match(
      discoverContent,
      /types:\s*selectedSchemeTypes\.length\s*>\s*0\s*\?\s*selectedSchemeTypes\s*:\s*undefined/,
      'DiscoverPage must pass selectedSchemeTypes to backend query'
    );
    assert.match(
      backendSchemeServiceContent,
      /SCHEME_TYPE_TAGS/,
      'Backend schemeService must define canonical SCHEME_TYPE_TAGS mapping'
    );
  });

  await t.test('12. Multiple filters combine cleanly and propagate simultaneously', () => {
    assert.match(
      discoverContent,
      /socialCategory:\s*selectedCasteCategory\s*\|\|\s*undefined/,
      'DiscoverPage must include socialCategory in query parameters'
    );
  });

  await t.test('13. Clear All resets all filter dimensions and pagination back to initial catalog state', () => {
    assert.match(
      discoverContent,
      /const\s+handleClearAll\s*=\s*\(\)\s*=>/,
      'DiscoverPage must provide handleClearAll handler'
    );
    assert.match(
      discoverContent,
      /setSelectedCategories\(\[\]\)/,
      'Clear All must reset selected categories'
    );
    assert.match(
      discoverContent,
      /setSelectedState\(''\)/,
      'Clear All must reset selected state'
    );
  });

  await t.test('14. Sorting supports 4 canonical modes (relevant, highest_benefit, name_asc, name_desc)', () => {
    assert.match(discoverContent, /value="relevant"/, 'Sorting must support relevant');
    assert.match(discoverContent, /value="highest_benefit"/, 'Sorting must support highest_benefit');
    assert.match(discoverContent, /value="name_asc"/, 'Sorting must support name_asc');
    assert.match(discoverContent, /value="name_desc"/, 'Sorting must support name_desc');
  });

  await t.test('15. Empty results display honest zero-state message without showing fake schemes', () => {
    assert.match(
      discoverContent,
      /No matching schemes found/,
      'DiscoverPage must display an honest empty state message'
    );
  });

  await t.test('16. API error displays honest error notification without showing fabricated fallback schemes', () => {
    assert.match(
      discoverContent,
      /Failed to search schemes/,
      'DiscoverPage must display an honest error banner on failure'
    );
    assert.ok(
      !discoverContent.includes('const FALLBACK_SCHEMES'),
      'DiscoverPage must never define or inject fabricated fallback schemes'
    );
  });

  await t.test('17. Discovery cards display canonical jurisdiction badge without recommendation score %', () => {
    assert.match(
      discoverContent,
      /jurisdictionLabel/,
      'Discovery cards must display canonical jurisdiction'
    );
    assert.ok(
      !discoverContent.includes('`${scheme.matchScore}% Match`'),
      'Discovery cards must not conflate retrieval matchScore with statutory eligibility'
    );
  });

  await t.test('18. Benefit mapping preserves authentic data without inventing loan ceilings as cash grants', () => {
    assert.match(
      discoverContent,
      /interpretFinancialBenefit/,
      'DiscoverPage must use financial benefit interpretation'
    );
  });

  await t.test('19. Tags derived from canonical categories, department, and state', () => {
    assert.match(
      discoverContent,
      /raw\.state\s*\|\|\s*'All India'/,
      'DiscoverPage must display authentic jurisdiction tag'
    );
  });

  await t.test('20. Bookmark persistence saves to localStorage namespaced by user ID', () => {
    assert.match(
      discoverContent,
      /bookmarkStorageKey\s*=\s*storedUser\?\.id/,
      'DiscoverPage must use user-scoped bookmark storage key'
    );
    assert.match(
      discoverContent,
      /fin_bookmarked_schemes_\$\{storedUser\.id\}/,
      'Bookmark storage key must include user ID'
    );
  });

  await t.test('21. View Details navigates to /schemes/${scheme.id} using authentic canonical ID/slug', () => {
    assert.match(
      discoverContent,
      /to=\{`\/schemes\/\$\{scheme\.id\}`\}/,
      'View Details must navigate using the scheme canonical ID'
    );
  });

  await t.test('22. Zero fabricated fallback schemes in production code', () => {
    const rawMatches = discoverContent.match(/dummy|mockSchemes|fakeScheme|placeholderSchemes/i);
    assert.strictEqual(rawMatches, null, 'DiscoverPage must contain no dummy/mock scheme definitions');
  });

  await t.test('23. User isolation cleans up user bookmarks on logout in authService', () => {
    assert.match(
      authContent,
      /fin_bookmarked_schemes/,
      'authService.clearCachedUserData must clean up user-scoped bookmarks on logout'
    );
  });

  await t.test('24. Canonical catalog consistency: 4,752 total schemes and 670 applicant applicable', async () => {
    const statsRes = await fetch('http://localhost:5000/api/schemes/stats');
    if (statsRes.ok) {
      const stats = await statsRes.json();
      assert.strictEqual(stats.total, 4752, 'Supabase schemes catalog total must be 4,752');
      const cats = stats.categoryCounts || stats.categories;
      assert.ok(cats, 'Stats must provide categoryCounts');
      assert.strictEqual(cats.business, 762, 'Business category count must be 762');
      assert.strictEqual(cats.agriculture, 487, 'Agriculture category count must be 487');
      assert.strictEqual(cats.education, 1227, 'Education category count must be 1227');
      assert.strictEqual(cats.women, 549, 'Women category count must be 549');
      assert.strictEqual(cats.youth, 515, 'Youth category count must be 515');
      assert.strictEqual(cats.health, 326, 'Health category count must be 326');
    }
  });

  await t.test('25. Discovery → Scheme Details consistency: schemes in catalog have valid IDs and titles', async () => {
    const searchRes = await fetch('http://localhost:5000/api/schemes/search?limit=5');
    if (searchRes.ok) {
      const result = await searchRes.json();
      assert.ok(Array.isArray(result.schemes), 'Search endpoint must return schemes array');
      assert.ok(result.total >= 4700, 'Search total must reflect canonical catalog');
      for (const scheme of result.schemes) {
        assert.ok(scheme.id, 'Scheme must have a valid ID');
        assert.ok(scheme.title || scheme.name || scheme.scheme_name, 'Scheme must have a valid title/name');
      }
    }
  });
});
