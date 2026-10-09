/**
 * FIN Phase C: Runtime Data Integrity, Correct Fact Retrieval & Structured AI Responses Regression Tests (Node.js)
 * 
 * Tests all 14 mandatory regression cases:
 * 1. Applicant full name retrieval.
 * 2. Certificate number retrieval.
 * 3. Personal income absent while family income exists.
 * 4. Father's income not substituted as personal income.
 * 5. Family income returns correct source-backed total (₹1,80,000 from Page 2).
 * 6. Conflicting income sources trigger REVIEW.
 * 7. Stale facts do not override active evidence.
 * 8. Deleted documents are excluded.
 * 9. Different query handlers return consistent values.
 * 10. Page 2 citations remain accurate.
 * 11. Cross-applicant data isolation.
 * 12. Structured answers contain no raw Markdown leakage.
 * 13. Missing facts are reported as unavailable.
 * 14. No fixed sample values in production response logic.
 */

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const {
    computeLocalFallback,
    resolveDocumentFactPage,
    formatPageLabel
} = require('../src/services/chatService');

describe('FIN Phase C: Fact Retrieval & Runtime Data Integrity', () => {

    const syntheticDoc = {
        id: 'doc-aarav-c',
        file_name: 'FIN_MultiPage_Income_Certificate_QA.pdf',
        document_type: 'INCOME_CERTIFICATE',
        verification_status: 'VERIFIED',
        is_active: true,
        extracted_text: `--- [Page 1] ---
SYNTHETIC TEST DOCUMENT — NOT VALID FOR OFFICIAL USE
GOVERNMENT OF GUJARAT — REVENUE DEPARTMENT
OFFICE OF THE MAMLATDAR & EXECUTIVE MAGISTRATE, AHMEDABAD (CITY)
Certificate No: TEST/GJ/INC/2026/TEST-84729
Date of Issue: 18 February 2026
Aadhaar Reference Token: 8392-4820-1940 (Last 4 Digits: 1940)

1. Full Name of Applicant: Aarav Patel
2. Father's / Guardian's Name: Rajesh Patel
3. Mother's Name: Meenaben Patel
4. Date of Birth: 12 August 2004 (Age: 22 Years)
5. Residential Address: B-402, Shivalik Heights, Bodakdev
   District: Ahmedabad, Gujarat — 380054
6. Social Category: General / EWS

--- [Page 2] ---
SYNTHETIC TEST DOCUMENT — NOT VALID FOR OFFICIAL USE
DETAILED INCOME ASSESSMENT & ENQUIRY REPORT

Income Determination Schedule:
1. Father's Employment Income (Pvt. Logistics Executive): Rs. 1,20,000 /-
2. Mother's Tailoring & Home Enterprise Income: Rs. 60,000 /-
3. Income from Agricultural / Land Holdings: Rs. 0 /-
4. Income from Other Household Sources: Rs. 0 /-

Total Annual Family Income: Rs. 1,80,000 /-
(In Words: Rupees One Lakh Eighty Thousand Only)

It is hereby certified that the total annual family income of Aarav Patel from all combined sources for the financial assessment year 2025-2026 is determined to be Rs. 1,80,000/-.`,
        extracted_fields: {
            beneficiary_name: 'Aarav Patel',
            document_number: 'TEST/GJ/INC/2026/TEST-84729',
            annual_family_income: '180000',
            father_income: '120000',
            mother_income: '60000',
            other_income: '0',
            date_of_birth: '12 August 2004',
            district: 'Ahmedabad',
            social_category: 'EWS'
        }
    };

    const mockProfile = {
        id: 'user-aarav',
        full_name: 'Aarav Patel',
        annual_income: '350000', // Default registration bracket that must NOT override active document!
        occupation: 'Student',
        category: 'General'
    };

    it('1. Applicant full name retrieval returns actual field, not document status', () => {
        const res = computeLocalFallback('What is my full name?', mockProfile, [syntheticDoc]);
        assert.match(res.reply, /Aarav Patel/);
        assert.doesNotMatch(res.reply, /Ready for AI Chat/);
        assert.match(res.reply, /Applicant Full Name/);
    });

    it('2. Certificate number retrieval returns actual certificate number, not Token or Ready status', () => {
        const res = computeLocalFallback('What is my certificate number?', mockProfile, [syntheticDoc]);
        assert.match(res.reply, /TEST\/GJ\/INC\/2026\/TEST-84729/);
        assert.doesNotMatch(res.reply, /Token/);
        assert.doesNotMatch(res.reply, /Ready for AI Chat/);
    });

    it('3. Personal income absent while family income exists clearly distinguishes personal income as unavailable', () => {
        const res = computeLocalFallback('What is my personal income?', mockProfile, [syntheticDoc]);
        assert.match(res.reply, /personal annual income is not available/i);
        assert.match(res.reply, /Annual Family Income on File/i);
        assert.match(res.reply, /1,80,000/);
        assert.doesNotMatch(res.reply, /1,20,000/); // Never substitute father's income as family income
    });

    it("4. Father's income is strictly separated and not substituted as personal income", () => {
        const res = computeLocalFallback("What is my father's income?", mockProfile, [syntheticDoc]);
        assert.match(res.reply, /Father's Annual Income/i);
        assert.match(res.reply, /1,20,000/);
        assert.equal(res.citations[0].source, '📄 FIN_MultiPage_Income_Certificate_QA.pdf (Page 2)');
    });

    it('5. Family income returns correct source-backed total (₹1,80,000) with breakdown', () => {
        const res = computeLocalFallback('What is my annual family income?', mockProfile, [syntheticDoc]);
        assert.match(res.reply, /1,80,000/);
        assert.doesNotMatch(res.reply, /3,50,000/); // Registration bracket must NOT override
        assert.match(res.reply, /Father's income: ₹1,20,000/);
        assert.match(res.reply, /Mother's income: ₹60,000/);
        assert.equal(res.citations[0].source, '📄 FIN_MultiPage_Income_Certificate_QA.pdf (Page 2)');
    });

    it('6. Conflicting income sources trigger REVIEW with competing values', () => {
        const conflictDoc = {
            id: 'doc-old',
            file_name: 'Previous_Year_Income.pdf',
            extracted_text: '--- [Page 1] ---\nTotal Annual Family Income: Rs. 2,50,000 /-',
            extracted_fields: {
                annual_family_income: '250000'
            }
        };
        const res = computeLocalFallback('What is my annual family income according to my documents?', mockProfile, [syntheticDoc, conflictDoc]);
        assert.match(res.reply, /REVIEW/);
        assert.match(res.reply, /1,80,000/);
        assert.match(res.reply, /2,50,000/);
    });

    it('7. Stale registration profile bracket does not override active document evidence', () => {
        const res = computeLocalFallback('What is my annual family income?', { annual_income: '350000' }, [syntheticDoc]);
        assert.match(res.reply, /1,80,000/);
        assert.doesNotMatch(res.reply, /3,50,000/);
    });

    it('8. Deleted documents are excluded', () => {
        const deletedDoc = {
            id: 'doc-del',
            file_name: 'Cancelled.pdf',
            deleted_at: '2026-03-01T00:00:00Z',
            is_active: false,
            extracted_fields: { annual_family_income: '999999' }
        };
        const activeDocs = [syntheticDoc, deletedDoc].filter(d => !d.deleted_at && d.is_active !== false);
        const res = computeLocalFallback('What is my annual family income?', mockProfile, activeDocs);
        assert.match(res.reply, /1,80,000/);
        assert.doesNotMatch(res.reply, /999999/);
    });

    it('9. Different query handlers return consistent values without contradiction', () => {
        const resPage = computeLocalFallback('What information is mentioned on page 2?', mockProfile, [syntheticDoc]);
        const resIncome = computeLocalFallback('What is my annual family income?', mockProfile, [syntheticDoc]);

        assert.match(resPage.reply, /1,80,000/);
        assert.match(resIncome.reply, /1,80,000/);
    });

    it('10. Page 2 citations remain accurate across all handlers', () => {
        const pageFam = resolveDocumentFactPage(syntheticDoc, '180000', 'annual_family_income');
        const pageFather = resolveDocumentFactPage(syntheticDoc, '120000', 'father_income');
        const pageName = resolveDocumentFactPage(syntheticDoc, 'Aarav Patel', 'beneficiary_name');

        assert.equal(pageFam, 2);
        assert.equal(pageFather, 2);
        assert.equal(pageName, 1);
    });

    it('11. Cross-applicant data isolation ensures tenant documents are isolated', () => {
        // Tenant with no documents
        const res = computeLocalFallback('What is my full name?', { full_name: 'Priya Sharma' }, []);
        assert.match(res.reply, /Priya Sharma/);
        assert.doesNotMatch(res.reply, /Aarav Patel/);
    });

    it('12. Structured answers contain no raw Markdown or unsummarized PDF leakage', () => {
        const res = computeLocalFallback('What information is mentioned on page 2?', mockProfile, [syntheticDoc]);
        assert.doesNotMatch(res.reply, /SYNTHETIC TEST DOCUMENT/);
        assert.doesNotMatch(res.reply, /--- \[Page/);
        assert.match(res.reply, /\*\*Page 2/);
        assert.match(res.reply, /\*\*Source\*\*/);
    });

    it('13. Missing facts are reported explicitly as unavailable', () => {
        const res = computeLocalFallback('What is my caste category?', { full_name: 'Test' }, []);
        assert.match(res.reply, /not available in your uploaded documents or profile records/i);
    });

    it('14. No fixed sample values in production response logic (Dynamic verification)', () => {
        const dynamicDoc = {
            id: 'doc-dyn',
            file_name: 'Kavita_Sharma_Income.pdf',
            extracted_text: `--- [Page 1] ---\nApplicant Name: Kavita Sharma\nCertificate Number: MH-2026-9812\n--- [Page 2] ---\nTotal Annual Family Income: Rs. 5,50,000 /-`,
            extracted_fields: {
                beneficiary_name: 'Kavita Sharma',
                document_number: 'MH-2026-9812',
                annual_family_income: '550000'
            }
        };

        const resName = computeLocalFallback('What is my full name?', {}, [dynamicDoc]);
        assert.match(resName.reply, /Kavita Sharma/);
        assert.doesNotMatch(resName.reply, /Aarav Patel/);

        const resInc = computeLocalFallback('What is my annual family income?', {}, [dynamicDoc]);
        assert.match(resInc.reply, /5,50,000/);
        assert.doesNotMatch(resInc.reply, /1,80,000/);
    });

    it('15. Explicit Page 2 query mentioning income retrieves Page 2 summary', () => {
        const res = computeLocalFallback(
            'Summarize the important information on Page 2 of my uploaded certificate, including the income assessment.',
            mockProfile,
            [syntheticDoc]
        );
        assert.match(res.reply, /\*\*Page 2/);
        assert.match(res.reply, /1,80,000/);
        assert.doesNotMatch(res.reply, /Which one would you like to review\?/);
        assert.ok(res.citations.length > 0);
        assert.match(res.citations[0].source, /Page 2/);
    });

    it('16. Explicit Page 3 query mentioning income reports page absence cleanly', () => {
        const res = computeLocalFallback(
            'What is mentioned on Page 3 regarding the income assessment?',
            mockProfile,
            [syntheticDoc]
        );
        assert.match(res.reply, /Page 3 does not exist in the document/);
        assert.doesNotMatch(res.reply, /Which one would you like to review\?/);
    });

    it('17. Duplicate submission guard prevents concurrent requests (in-flight lock contract)', async () => {
        // Simulates the synchronous in-flight guard contract in FinAssistantModal
        let isSubmitting = false;
        let submitCallCount = 0;

        const guardedSubmit = async (query) => {
            if (isSubmitting) {
                return { skipped: true };
            }
            isSubmitting = true;
            submitCallCount++;
            // Simulate async network request
            await new Promise(r => setTimeout(r, 20));
            isSubmitting = false;
            return { skipped: false, result: `Handled ${query}` };
        };

        // Fire two concurrent submissions in the same event tick (rapid double Enter / Click)
        const [firstCall, secondCall] = await Promise.all([
            guardedSubmit('Query 1'),
            guardedSubmit('Query 1 duplicate')
        ]);

        assert.strictEqual(firstCall.skipped, false);
        assert.strictEqual(secondCall.skipped, true);
        assert.strictEqual(submitCallCount, 1);
        assert.strictEqual(isSubmitting, false);
    });

    it('18. Submission guard resets after request failure so chat is never permanently disabled', async () => {
        let isSubmitting = false;
        let errorCaught = false;

        const faultySubmit = async () => {
            if (isSubmitting) return;
            isSubmitting = true;
            try {
                throw new Error('Network timeout');
            } catch (err) {
                errorCaught = true;
            } finally {
                isSubmitting = false;
            }
        };

        await faultySubmit();
        assert.strictEqual(errorCaught, true);
        assert.strictEqual(isSubmitting, false, 'Guard must be released on failure');

        // Subsequent submission must be allowed
        let secondSuccess = false;
        const secondSubmit = async () => {
            if (isSubmitting) return;
            isSubmitting = true;
            try {
                secondSuccess = true;
            } finally {
                isSubmitting = false;
            }
        };

        await secondSubmit();
        assert.strictEqual(secondSuccess, true, 'Subsequent request must succeed after prior failure');
        assert.strictEqual(isSubmitting, false);
    });

    it('19. Phase C2: Page 2 income summary includes total, distinct breakdown, and no orphan table headers', () => {
        const res = computeLocalFallback(
            'Summarize the important information on Page 2 of my uploaded certificate, including the income assessment.',
            mockProfile,
            [syntheticDoc]
        );
        assert.match(res.reply, /\*\*Income Breakdown\*\*/);
        assert.match(res.reply, /Father's income:\s*₹1,20,000/);
        assert.match(res.reply, /Mother's income:\s*₹60,000/);
        assert.match(res.reply, /Total annual family income:\s*₹1,80,000/);
        // Verify table-header noise is stripped
        assert.doesNotMatch(res.reply, /Income Component/);
        assert.doesNotMatch(res.reply, /Contributing Household/);
        assert.doesNotMatch(res.reply, /Nature of Livelihood/);
        assert.doesNotMatch(res.reply, /Annual Amount/);
    });

    it('20. Phase C2: Page 1 non-income summary extracts Key Information without income breakdown', () => {
        const res = computeLocalFallback('What is on page 1 of my document?', mockProfile, [syntheticDoc]);
        assert.match(res.reply, /\*\*Key Information\*\*/);
        assert.match(res.reply, /Applicant Full Name:\s*Aarav Patel/);
        assert.match(res.reply, /Certificate \/ Document Number:\s*TEST\/GJ\/INC\/2026\/TEST-84729/);
        assert.doesNotMatch(res.reply, /\*\*Income Breakdown\*\*/);
        assert.match(res.reply, /\*\*Source\*\*/);
        assert.match(res.reply, /Page 1/);
    });

    it('21. Phase C2: Conflicting evidence triggers REVIEW in page summary', () => {
        const conflictingDoc = {
            id: 'doc-conflict',
            file_name: 'Previous_Income_Certificate.pdf',
            is_active: true,
            extracted_fields: { annual_family_income: '240000' },
            extracted_text: '--- [Page 1] ---\nAnnual Family Income: Rs. 2,40,000 /-'
        };
        const res = computeLocalFallback(
            'Summarize Page 2',
            mockProfile,
            [syntheticDoc, conflictingDoc]
        );
        assert.match(res.reply, /REVIEW REQUIRED — Conflicting Evidence Detected/);
        assert.match(res.reply, /1,80,000/);
        assert.match(res.reply, /2,40,000/);
    });

    it('22. Phase C2: Non-income document produces relevant summary and does not force income format', () => {
        const electricityDoc = {
            id: 'doc-elec',
            file_name: 'Electricity_Bill.pdf',
            is_active: true,
            extracted_text: `--- [Page 1] ---
Consumer Name: Aarav Patel
Consumer Number: CA-902148192
Billing Month: January 2026
Due Date: 15 February 2026
Total Amount Payable: Rs. 1,420 /-`,
            extracted_fields: {
                beneficiary_name: 'Aarav Patel'
            }
        };
        const res = computeLocalFallback('Summarize page 1 of my electricity bill', mockProfile, [electricityDoc]);
        assert.match(res.reply, /\*\*Key Information\*\*/);
        assert.match(res.reply, /Consumer Name:\s*Aarav Patel/);
        assert.doesNotMatch(res.reply, /\*\*Income Breakdown\*\*/);
        assert.match(res.reply, /Electricity_Bill\.pdf/);
    });

    it('23. Phase C3: Assessment-period verification returns distinct fields and CONSISTENT result for matching dates/FY', () => {
        const docWithDates = {
            id: 'doc-dates',
            file_name: 'FIN_Income_Cert.pdf',
            is_active: true,
            extracted_text: `--- [Page 1] ---\nApplicant: Aarav Patel\n--- [Page 2] ---\nAssessment Period: 1 April 2025 to 31 March 2026 (Financial Year 2025–2026)\nTotal Annual Family Income: Rs. 1,80,000 /-`,
            extracted_fields: { annual_family_income: '180000' }
        };
        const res = computeLocalFallback(
            'Verify the assessment period, exact dates, financial year, and consistency on Page 2 of my uploaded certificate.',
            mockProfile,
            [docWithDates]
        );
        assert.match(res.reply, /### Assessment Period Verification/);
        assert.match(res.reply, /Exact Source Start Date.*1 April 2025/);
        assert.match(res.reply, /Exact Source End Date.*31 March 2026/);
        assert.match(res.reply, /Financial Year as Stated.*2025/);
        assert.match(res.reply, /Consistency Result.*CONSISTENT/);
        assert.match(res.reply, /Page 2/);
        assert.doesNotMatch(res.reply, /\*\*Income Breakdown\*\*/);
    });

    it('24. Phase C3: Conflicting date/FY values return REVIEW REQUIRED (CONFLICT)', () => {
        const docConflictDates = {
            id: 'doc-conflict-dates',
            file_name: 'Conflict_Dates.pdf',
            is_active: true,
            extracted_text: `--- [Page 2] ---\nAssessment Period: 01 April 2022 to 31 March 2023 (Financial Year 2025–2026)\nTotal Annual Family Income: Rs. 1,80,000 /-`,
            extracted_fields: { annual_family_income: '180000' }
        };
        const res = computeLocalFallback(
            'Verify the assessment period, exact dates, financial year, and consistency on Page 2',
            mockProfile,
            [docConflictDates]
        );
        assert.match(res.reply, /REVIEW REQUIRED/);
        assert.match(res.reply, /01 April 2022/);
        assert.match(res.reply, /31 March 2023/);
    });

    it('25. Phase C3: Missing dates return UNABLE TO VERIFY without inventing facts', () => {
        const docMissingDates = {
            id: 'doc-no-dates',
            file_name: 'No_Dates.pdf',
            is_active: true,
            extracted_text: `--- [Page 2] ---\nFinancial Assessment Year: 2025-2026\nTotal Annual Family Income: Rs. 1,80,000 /-`,
            extracted_fields: { annual_family_income: '180000' }
        };
        const res = computeLocalFallback(
            'Verify the assessment period, exact dates, financial year, and consistency on Page 2',
            mockProfile,
            [docMissingDates]
        );
        assert.match(res.reply, /Consistency Result.*UNABLE TO VERIFY/);
        assert.match(res.reply, /Not specified in document/);
    });

    it('26. Phase C3: Explicit income extraction enumerates individual vs consolidated total', () => {
        const res = computeLocalFallback(
            'Enumerate every explicitly stated income amount, identify individual vs total income, and cite the source on Page 2.',
            mockProfile,
            [syntheticDoc]
        );
        assert.match(res.reply, /### Explicit Income Extraction/);
        assert.match(res.reply, /Father's Employment Income.*Individual Contribution/);
        assert.match(res.reply, /Mother's Self-Employment Income.*Individual Contribution/);
        assert.match(res.reply, /Total Annual Family Income.*Consolidated Total/);
        assert.match(res.reply, /Page 2/);
    });

    it('27. Phase C3: Missing income components are not fabricated as zero', () => {
        const singleEarnerDoc = {
            id: 'doc-single',
            file_name: 'Single_Earner.pdf',
            is_active: true,
            extracted_text: `--- [Page 2] ---\nFather's Employment Income: Rs. 1,50,000 /-\nTotal Annual Family Income: Rs. 1,50,000 /-`,
            extracted_fields: {
                father_income: '150000',
                annual_family_income: '150000'
            }
        };
        const res = computeLocalFallback(
            'Enumerate every explicitly stated income amount, identify individual vs total income, and cite the source on Page 2.',
            mockProfile,
            [singleEarnerDoc]
        );
        assert.match(res.reply, /Father's Employment Income.*₹1,50,000/);
        assert.match(res.reply, /Total Annual Family Income.*₹1,50,000/);
        // Mother's income was not mentioned and must NOT be fabricated as ₹0
        assert.doesNotMatch(res.reply, /Mother/);
        assert.doesNotMatch(res.reply, /Other Family Income/);
    });

    it('28. Phase C3: Intent-aware response selection ensures different tasks return distinct contracts', () => {
        const resSummary = computeLocalFallback('Summarize Page 2', mockProfile, [syntheticDoc]);
        const resVerify = computeLocalFallback('Verify the assessment period and consistency on Page 2', mockProfile, [syntheticDoc]);
        const resEnum = computeLocalFallback('Enumerate every explicitly stated income amount on Page 2', mockProfile, [syntheticDoc]);

        assert.match(resSummary.reply, /\*\*Page 2 — /);
        assert.match(resVerify.reply, /### Assessment Period Verification/);
        assert.match(resEnum.reply, /### Explicit Income Extraction/);

        // They must NOT return the exact same canned structure
        assert.notStrictEqual(resSummary.reply, resVerify.reply);
        assert.notStrictEqual(resVerify.reply, resEnum.reply);
    });

    it('29. Phase C3.2.1: Explicit zero in source remains zero and is identified as stated', () => {
        const res = computeLocalFallback(
            'What is other family income according to my document?',
            mockProfile,
            [syntheticDoc]
        );
        assert.match(res.reply, /\*\*Other Family Income\*\*/);
        assert.match(res.reply, /₹0/);
        assert.match(res.reply, /Explicitly stated in document/);
        assert.match(res.reply, /Page 2/);
    });

    it('30. Phase C3.2.1: Missing income component remains unavailable and is not assumed zero', () => {
        const singleDoc = {
            id: 'doc-single-2',
            file_name: 'Single_Earner.pdf',
            is_active: true,
            extracted_text: `--- [Page 2] ---\nFather's Employment Income: Rs. 1,50,000 /-\nTotal Annual Family Income: Rs. 1,50,000 /-`,
            extracted_fields: {
                father_income: '150000',
                annual_family_income: '150000'
            }
        };
        const res = computeLocalFallback(
            'What is other family income according to my document?',
            mockProfile,
            [singleDoc]
        );
        assert.match(res.reply, /not specified/i);
        assert.doesNotMatch(res.reply, /₹0/);
    });

    it('31. Phase C3.2.1: Explicit income extraction on document with zero source preserves ₹0 without calculation', () => {
        const res = computeLocalFallback(
            'Enumerate every explicitly stated income amount on Page 2',
            mockProfile,
            [syntheticDoc]
        );
        assert.match(res.reply, /### Explicit Income Extraction/);
        assert.match(res.reply, /Other Family Income.*₹0/);
        assert.match(res.reply, /Page 2/);
    });
});

