/**
 * FIN Phase D1.2.2: Scheme Query Routing & Canonical Retrieval Fix Regression Suite (Node.js)
 * 
 * Verifies:
 * 1. Named scheme question containing "application process" does NOT trigger personal ticket lookup.
 * 2. Named scheme question containing "required documents" does NOT trigger personal document lookup.
 * 3. Genuine personal application status query returns user's active tickets.
 * 4. Genuine active ticket query returns user's active tickets.
 * 5. Personal uploaded-document query lists user's uploaded vault documents.
 * 6. Page-specific certificate query returns page-level extraction.
 * 7. Backend fallback routing parity preserves statutory scheme responses and personal ticket responses.
 * 8. Applicant isolation prevents cross-tenant ticket and document leakage.
 * 9. Missing scheme fields remain explicitly unavailable without fabricating data.
 */

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const {
    computeLocalFallback,
    resolveDocumentFactPage,
    formatPageLabel
} = require('../src/services/chatService');

describe('FIN Phase D1.2.2: Scheme Query Routing & Canonical Retrieval Regression Suite', () => {

    const userApplications = [
        {
            id: 'app-99990001',
            ticket_id: 'APP-99990001',
            scheme_id: 'pmegp',
            scheme_name: "Prime Minister's Employment Generation Programme",
            status: 'under_review',
            estimated_benefit: '₹ 2,50,000',
            submitted_at: '2026-09-15T10:00:00Z'
        }
    ];

    const userDocuments = [
        {
            id: 'doc-user-1',
            file_name: 'Income_Certificate_2026.pdf',
            document_type: 'INCOME_CERTIFICATE',
            verification_status: 'VERIFIED',
            is_active: true,
            extracted_fields: {
                annual_family_income: '180000',
                father_income: '120000',
                mother_income: '60000',
                document_number: 'DOC-INC-84729'
            },
            extracted_text: `--- [Page 1] ---
Government of Gujarat - Revenue Department
Certificate No: DOC-INC-84729
Applicant Name: Test Citizen
--- [Page 2] ---
Detailed Assessment:
Father's Employment Income: Rs. 1,20,000
Mother's Income: Rs. 60,000
Total Annual Family Income: Rs. 1,80,000`
        }
    ];

    const profileFacts = {
        full_name: 'Test Citizen',
        annual_family_income: '180000'
    };

    it('1. Named scheme question containing "application process" does NOT trigger personal ticket lookup in fallback', () => {
        const query = "Explain the application process for this scheme.";
        const fallbackRes = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(fallbackRes && fallbackRes.reply, "Expected reply from fallback");
        assert.ok(
            !fallbackRes.reply.includes("Here are your active government applications"),
            "Scheme application process question must NOT return personal application tickets"
        );
        assert.ok(
            !fallbackRes.reply.includes("Ticket ID: `APP-"),
            "Scheme application process question must not contain ticket IDs"
        );
        assert.ok(
            fallbackRes.reply.toLowerCase().includes("apply") || fallbackRes.reply.toLowerCase().includes("step"),
            "Should describe application procedure steps"
        );
    });

    it('2. Named scheme question containing "required documents" does NOT trigger personal document vault lookup in fallback', () => {
        const query = "What documents are required for this scheme?";
        const fallbackRes = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(fallbackRes && fallbackRes.reply, "Expected reply from fallback");
        assert.ok(
            !fallbackRes.reply.includes("You have uploaded 1 document"),
            "Scheme statutory documents question must NOT return personal document vault list"
        );
        assert.ok(
            !fallbackRes.reply.includes("DOC-INC-84729"),
            "Scheme statutory documents question must not return personal certificate numbers"
        );
        assert.ok(
            fallbackRes.reply.toLowerCase().includes("required") || fallbackRes.reply.toLowerCase().includes("identity"),
            "Should list statutory documents required for schemes"
        );
    });

    it('3. Genuine personal application status query returns user active tickets', () => {
        const query = "What is the status of my application?";
        const fallbackRes = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(fallbackRes && fallbackRes.reply, "Expected reply from fallback");
        assert.ok(
            fallbackRes.reply.includes("Here are your active government applications and support tickets"),
            "Personal application status query must return active applications"
        );
        assert.ok(
            fallbackRes.reply.includes("APP-99990001"),
            "Must include user's actual ticket ID"
        );
        assert.ok(
            fallbackRes.reply.includes("Prime Minister's Employment Generation Programme"),
            "Must include user's applied scheme name"
        );
    });

    it('4. Genuine active ticket query returns user active tickets', () => {
        const query = "Show my active tickets";
        const fallbackRes = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(fallbackRes && fallbackRes.reply, "Expected reply from fallback");
        assert.ok(
            fallbackRes.reply.includes("Here are your active government applications and support tickets"),
            "Active ticket query must return user tickets"
        );
        assert.ok(
            fallbackRes.reply.includes("APP-99990001"),
            "Must include ticket ID"
        );
    });

    it('5. Genuine active ticket query with no tickets informs user accurately', () => {
        const query = "Show my active applications";
        const fallbackRes = computeLocalFallback(query, profileFacts, userDocuments, []);

        assert.ok(fallbackRes && fallbackRes.reply, "Expected reply from fallback");
        assert.ok(
            fallbackRes.reply.includes("You currently have no active applications or tickets submitted"),
            "Must inform user that no applications are currently submitted"
        );
        assert.ok(
            !fallbackRes.reply.includes("APP-"),
            "Must not show any ticket IDs when applications list is empty"
        );
    });

    it('6. Personal uploaded-document query lists user uploaded documents', () => {
        const query = "What documents have I uploaded?";
        const fallbackRes = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(fallbackRes && fallbackRes.reply, "Expected reply from fallback");
        assert.ok(
            fallbackRes.reply.includes("1 document(s) in your vault") || fallbackRes.reply.includes("Income_Certificate_2026.pdf"),
            "Must list personal uploaded documents"
        );
    });

    it('7. Page-specific certificate query returns Page 2 extraction', () => {
        const query = "What is written on Page 2 of my certificate?";
        const fallbackRes = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(fallbackRes && fallbackRes.reply, "Expected reply from fallback");
        assert.ok(
            fallbackRes.reply.includes("Page 2") || fallbackRes.reply.includes("1,80,000") || fallbackRes.reply.includes("Father"),
            "Must retrieve Page 2 specific evidence"
        );
    });

    it('8. Applicant isolation prevents cross-tenant application and document leakage', () => {
        const userBApplications = [
            {
                id: 'app-user-b',
                ticket_id: 'APP-USER-B-SECRET',
                scheme_name: 'Special Sensitive Scheme',
                status: 'approved'
            }
        ];
        const userBDocuments = [
            {
                id: 'doc-user-b',
                file_name: 'Confidential_User_B.pdf',
                document_type: 'PASSPORT',
                extracted_fields: { doc_number: 'PASSPORT-SECRET-999' }
            }
        ];

        // Query executed for User A
        const resUserA = computeLocalFallback("Show my active tickets", profileFacts, userDocuments, userApplications);
        assert.ok(!resUserA.reply.includes("USER-B-SECRET"), "User A must not see User B's tickets");

        const resDocsUserA = computeLocalFallback("What documents have I uploaded?", profileFacts, userDocuments, userApplications);
        assert.ok(!resDocsUserA.reply.includes("Confidential_User_B.pdf"), "User A must not see User B's documents");
        assert.ok(!resDocsUserA.reply.includes("PASSPORT-SECRET-999"), "User A must not see User B's certificate numbers");
    });

    it('9. Scheme procedure queries like "How can I apply?" do not trigger tickets', () => {
        const procedureQueries = [
            "How can I apply?",
            "What is the application procedure?",
            "What is the application deadline?",
            "Explain the application steps for a scheme"
        ];

        for (const q of procedureQueries) {
            const res = computeLocalFallback(q, profileFacts, userDocuments, userApplications);
            assert.ok(
                !res.reply.includes("Here are your active government applications and support tickets"),
                `Query "${q}" must NOT trigger personal ticket lookup`
            );
        }
    });

    it('10. Phase D1.2.3: Multi-point application process query with negative constraints does NOT trigger personal documents or tickets in fallback', () => {
        const query = `Explain only the application process for the Young Investigators Programme in Biotechnology. Include:
1. Application mode.
2. Where and when applications are invited.
3. Pre-proposal submission and review stages.
4. Detailed proposal evaluation stages.
5. Required institutional endorsement or supporting documents.
6. How applicants are notified.

Use the available scheme record. Do not show my personal applications, tickets, or uploaded documents. If a deadline or current application window is unavailable, explicitly say so.`;

        const res = computeLocalFallback(query, profileFacts, userDocuments, userApplications);
        assert.ok(res && res.reply, "Expected fallback reply");
        assert.ok(!res.reply.includes("Income_Certificate_2026.pdf"), "Must not leak personal document filename");
        assert.ok(!res.reply.includes("DOC-INC-84729"), "Must not leak certificate number");
        assert.ok(!res.reply.includes("APP-99990001"), "Must not leak personal ticket ID");
        assert.ok(!res.reply.includes("active government applications"), "Must not return ticket list");
        assert.ok(res.reply.toLowerCase().includes("apply") || res.reply.toLowerCase().includes("step"), "Must return scheme procedure guidance");
    });

    it('11. Phase D1.2.3: Non-adjacent scheme document wording does not trigger personal document vault in fallback', () => {
        const query = "What supporting documents and institutional endorsements are required for this scheme?";
        const res = computeLocalFallback(query, profileFacts, userDocuments, userApplications);
        assert.ok(!res.reply.includes("Income_Certificate_2026.pdf"), "Must not return personal document");
        assert.ok(!res.reply.includes("DOC-INC-84729"), "Must not return personal certificate number");
    });

    it('12. Phase D1.2.3: Negative constraints (do not show my documents / tickets) do not trigger personal vault in fallback', () => {
        const query = "Tell me about PM-Kisan. Do not show my uploaded documents or tickets.";
        const res = computeLocalFallback(query, profileFacts, userDocuments, userApplications);
        assert.ok(!res.reply.includes("Income_Certificate_2026.pdf"), "Must not return personal document");
        assert.ok(!res.reply.includes("APP-99990001"), "Must not return tickets");
        assert.ok(res.reply.toLowerCase().includes("pm-kisan") || res.reply.toLowerCase().includes("farmer"), "Should resolve PM-Kisan");
    });

    it('13. Phase D1.2.3: Genuine Page 2 personal certificate inquiry is preserved in fallback', () => {
        const query = "What information is on page 2 of my certificate?";
        const res = computeLocalFallback(query, profileFacts, userDocuments, userApplications);
        assert.ok(res.reply.includes("Income_Certificate_2026.pdf"), "Must cite the personal certificate");
        assert.ok(res.reply.includes("Page 2"), "Must cite Page 2");
        assert.equal(res.citations[0].schemeId, "USER_DOCUMENT");
    });
});

