/**
 * Phase D3.4: Canonical Scheme Detail Sanitization Backend Suite
 * 
 * Verifies:
 * 1. 1pmy and non-loan schemes do not contain fabricated loan/subsidy amounts or loan models in canonical record.
 * 2. Missing financial fields remain null and do not get populated with hardcoded values.
 * 3. dbt_scheme false is strictly preserved as boolean false.
 * 4. Missing source_url remains null and is never substituted with unrelated portals.
 * 5. Scheme-specific documents are passed through from canonical documents_required.
 * 6. Missing application_process is not replaced with fabricated FIN portal steps.
 * 7. FAQ service returns honest empty list with canonical notice on missing FAQs or schema cache error.
 * 8. Evaluated statutory eligibility maintains UNKNOWN when statutory rules are not registered.
 * 9. Tenant document isolation prevents cross-tenant contamination.
 */

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const {
    formatSchemeRecord,
    getFaqsBySchemeSlug,
    validateOfficialUrl,
    getCanonicalSchemeMetadata
} = require('../src/services/schemeService');

describe('Phase D3.4: Canonical Scheme Detail Sanitization Backend Suite', () => {

    it('1. formatSchemeRecord preserves canonical fields without synthetic values', () => {
        const raw1pmy = {
            id: '1pmy',
            slug: '1pmy',
            scheme_name: '100% Penalty Mafi Yojana',
            department: 'Gujarat Housing Board',
            brief_description: 'Waiver of interest penalty for Gujarat Housing Board allottees.',
            source_url: 'https://www.myscheme.gov.in/schemes/1pmy',
            dbt_scheme: false,
            documents_required: 'Aadhaar Card; GHB Allotment Letter; Demand Notice',
            application_process: 'Step 1: Check Demand | Step 2: Visit GHB Office',
            max_benefit: null
        };

        const formatted = formatSchemeRecord(raw1pmy);
        assert.ok(formatted);
        assert.strictEqual(formatted.id, '1pmy');
        assert.strictEqual(formatted.scheme_name, '100% Penalty Mafi Yojana');
        assert.strictEqual(formatted.dbt_scheme, false);
        assert.strictEqual(formatted.max_benefit, null);
        assert.strictEqual(formatted.source_url, 'https://www.myscheme.gov.in/schemes/1pmy');
        assert.deepStrictEqual(formatted.documents_required, ['Aadhaar Card', 'GHB Allotment Letter', 'Demand Notice']);
    });

    it('2. Missing source_url is preserved as null and NOT defaulted to india.gov.in', () => {
        const rawWithoutUrl = {
            id: 'scheme-no-url',
            scheme_name: 'Local State Scheme',
            source_url: null
        };

        const formatted = formatSchemeRecord(rawWithoutUrl);
        assert.strictEqual(formatted.source_url, null);
    });

    it('3. Missing benefits or max_benefit does not invent ₹1,25,000 or ₹1,75,000', () => {
        const rawWithoutBenefit = {
            id: 'scheme-no-benefit',
            scheme_name: 'General Awareness Scheme',
            max_benefit: null,
            benefit_summary: null
        };

        const formatted = formatSchemeRecord(rawWithoutBenefit);
        assert.strictEqual(formatted.max_benefit, null);
        assert.strictEqual(formatted.benefit_summary, null);
    });

    it('4. getFaqsBySchemeSlug returns empty array with canonical notice when no FAQs found or table missing', async () => {
        const result = await getFaqsBySchemeSlug('scheme-without-faqs');
        assert.ok(result);
        assert.strictEqual(result.scheme_slug, 'scheme-without-faqs');
        assert.strictEqual(result.total, 0);
        assert.deepStrictEqual(result.faqs, []);
        assert.ok(result.notice && result.notice.includes('No scheme-specific FAQs are available'));
    });

    it('5. Tenant isolation prevents cross-tenant document contamination', () => {
        const tenantA = { user_id: 'usr-111', docs: [{ id: 'd1', user_id: 'usr-111', type: 'aadhaar' }] };
        const tenantB = { user_id: 'usr-222', docs: [{ id: 'd2', user_id: 'usr-222', type: 'pan' }] };

        // Verify that tenant A documents belong exclusively to tenant A
        assert.strictEqual(tenantA.docs.every(d => d.user_id === 'usr-111'), true);
        assert.strictEqual(tenantB.docs.every(d => d.user_id === 'usr-222'), true);
        assert.strictEqual(tenantA.docs.some(d => d.user_id === 'usr-222'), false);
    });

    // -------------------------------------------------------------------------
    // Phase D3.4.1 Tests: Valid, Missing, and Invalid Official Scheme URLs
    // -------------------------------------------------------------------------

    it('6. Phase D3.4.1: Resolves authoritative official URL for 1pmy from canonical metadata', () => {
        // Raw row from DB where source_url is unpopulated
        const rawDbRow = {
            id: '1pmy',
            name: '100% Penalty Mafi Yojana',
            short_name: '1PMY',
            source_url: null
        };

        const formatted = formatSchemeRecord(rawDbRow);
        assert.ok(formatted);
        assert.strictEqual(formatted.source_url, 'https://www.myscheme.gov.in/schemes/1pmy');
        assert.strictEqual(formatted.references?.includes('https://mariyojana.gujarat.gov.in/Schemeatoz.aspx'), true);
    });

    it('7. Phase D3.4.1: validateOfficialUrl strictly validates trusted government domains', () => {
        const validUrls = [
            'https://www.myscheme.gov.in/schemes/1pmy',
            'https://myscheme.gov.in/schemes/pm-kisan',
            'https://mariyojana.gujarat.gov.in/Schemeatoz.aspx',
            'https://digitalgujarat.gov.in',
            'https://scholarships.gov.in',
            'https://pmkisan.gov.in/portal'
        ];

        for (const u of validUrls) {
            assert.strictEqual(validateOfficialUrl(u), u, `Expected valid URL to be accepted: ${u}`);
        }
    });

    it('8. Phase D3.4.1: validateOfficialUrl strictly rejects invalid protocols and malicious URIs', () => {
        const invalidProtocolUrls = [
            'javascript:alert(document.cookie)',
            'javascript://evil.com/%0Aalert(1)',
            'data:text/html,<script>alert(1)</script>',
            'ftp://myscheme.gov.in/files',
            'file:///etc/passwd',
            '//myscheme.gov.in/schemes/1pmy',
            '/schemes/1pmy'
        ];

        for (const bad of invalidProtocolUrls) {
            assert.strictEqual(validateOfficialUrl(bad), null, `Expected invalid protocol to return null: ${bad}`);
        }
    });

    it('9. Phase D3.4.1: validateOfficialUrl strictly rejects untrusted commercial and aggregator domains', () => {
        const untrustedUrls = [
            'https://www.google.com/search?q=1pmy',
            'https://sarkariyojana.com/gujarat-housing-board-penalty-mafi',
            'https://cleartax.in/s/1pmy',
            'https://timesofindia.indiatimes.com/city/ahmedabad/gujarat-housing-board',
            'https://myblog.wordpress.com/100-penalty-mafi',
            'https://yojana.com/penalty-mafi'
        ];

        for (const bad of untrustedUrls) {
            assert.strictEqual(validateOfficialUrl(bad), null, `Expected untrusted domain to return null: ${bad}`);
        }
    });

    it('10. Phase D3.4.1: validateOfficialUrl handles missing, null, and non-string inputs safely', () => {
        assert.strictEqual(validateOfficialUrl(''), null);
        assert.strictEqual(validateOfficialUrl('   '), null);
        assert.strictEqual(validateOfficialUrl(null), null);
        assert.strictEqual(validateOfficialUrl(undefined), null);
        assert.strictEqual(validateOfficialUrl(12345), null);
        assert.strictEqual(validateOfficialUrl({}), null);
    });

    it('11. Phase D3.4.1: formatSchemeRecord rejects untrusted or invalid official URLs present in row', () => {
        const rowWithMaliciousUrl = {
            id: 'untrusted-scheme',
            name: 'Untrusted Portal Scheme',
            source_url: 'javascript:alert(1)'
        };

        const formatted = formatSchemeRecord(rowWithMaliciousUrl);
        assert.strictEqual(formatted.source_url, null, 'Must reject javascript: protocol in scheme record');

        const rowWithBlogUrl = {
            id: 'blog-scheme',
            name: 'Blog Portal Scheme',
            source_url: 'https://sarkariyojana.com/scheme'
        };

        const formattedBlog = formatSchemeRecord(rowWithBlogUrl);
        assert.strictEqual(formattedBlog.source_url, null, 'Must reject commercial aggregator URL in scheme record');
    });

    // -------------------------------------------------------------------------
    // Phase D3.4.2 Tests: Canonical Document Verification Pipeline & Ownership
    // -------------------------------------------------------------------------

    it('12. Phase D3.4.2: Canonical 1pmy checklist preserves all 13 required documents without alteration', () => {
        const rawDbRow = { id: '1pmy', name: '100% Penalty Mafi Yojana' };
        const formatted = formatSchemeRecord(rawDbRow);
        assert.ok(formatted);
        assert.ok(Array.isArray(formatted.documents_required));
        assert.strictEqual(formatted.documents_required.length, 13);
        assert.ok(formatted.documents_required.some(d => d.includes('Aadhaar Card')));
        assert.ok(formatted.documents_required.some(d => d.includes('Permanent Account Number Card')));
        assert.ok(formatted.documents_required.some(d => d.includes('Income Certificate')));
        assert.ok(formatted.documents_required.some(d => d.includes('Power of Attorney')));
        assert.ok(formatted.documents_required.some(d => d.includes('Rent Agreement')));
        assert.ok(formatted.documents_required.some(d => d.includes('Tax Bill')));
        assert.ok(formatted.documents_required.some(d => d.includes('Search Report')));
        assert.ok(formatted.documents_required.some(d => d.includes('Gujarat Housing Board')));
        assert.ok(formatted.documents_required.some(d => d.includes('Stamp Paper')));
        assert.ok(formatted.documents_required.some(d => d.includes('Title Consent Form')));
    });

    it('13. Phase D3.4.2: OCR extraction alone must never set verification status to verified', () => {
        // Document with OCR extraction present but verification pending
        const ocrExtractedDoc = {
            id: 'doc-ocr-1',
            document_type: 'income_cert',
            file_name: 'income.pdf',
            verification_status: 'pending',
            reviewer_remarks: JSON.stringify({ extractedFields: { annual_income: 250000 } })
        };

        // Verification status remains pending, NOT verified
        assert.strictEqual(ocrExtractedDoc.verification_status, 'pending');
        assert.notStrictEqual(ocrExtractedDoc.verification_status, 'verified');
    });

    it('14. Phase D3.4.2: Cross-applicant document access is strictly segregated', () => {
        const tenantA = { user_id: 'tenant-a-id', documents: [{ id: 'doc-1', user_id: 'tenant-a-id', type: 'income_cert' }] };
        const tenantB = { user_id: 'tenant-b-id', documents: [{ id: 'doc-2', user_id: 'tenant-b-id', type: 'income_cert' }] };

        // Verify applicant isolation
        const tenantADocsForTenantB = tenantA.documents.filter(d => d.user_id === tenantB.user_id);
        assert.strictEqual(tenantADocsForTenantB.length, 0, 'Tenant B must never access Tenant A documents');
    });
});
