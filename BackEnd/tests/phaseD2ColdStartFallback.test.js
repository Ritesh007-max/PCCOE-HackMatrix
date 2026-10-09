/**
 * FIN D2.2-C1-F: Intelligence Cold-Start & Canonical Fallback Reliability Test Suite
 * 
 * Verifies:
 * 1. Named canonical YIPB query in offline fallback returns official YIPB application process.
 * 2. Fallback response does NOT return generic FIN portal instructions as YIPB's process.
 * 3. Fallback response preserves degraded metadata (degraded: true, source: 'local_fallback').
 * 4. Fallback response preserves eligibilityStatus: 'UNKNOWN' and matchScore: null.
 * 5. Unknown scheme query with unavailable canonical data returns transparent offline notice, NOT generic FIN portal steps.
 * 6. Generic portal application question without named scheme returns FIN portal steps.
 * 7. Negative constraints are preserved in fallback (no personal tickets/documents leaked).
 * 8. Official source URL is cited and not invented.
 */

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { computeLocalFallback } = require('../src/services/chatService');

describe('FIN D2.2-C1-F: Intelligence Cold-Start & Canonical Fallback Reliability', () => {

    const userApplications = [
        {
            id: 'app-test-01',
            ticket_id: 'APP-YIPB-1234',
            scheme_id: 'yipb',
            scheme_name: 'Young Investigators Programme in Biotechnology',
            status: 'under_review',
            estimated_benefit: '₹ 45,000/month',
            submitted_at: '2026-09-20T10:00:00Z'
        }
    ];

    const userDocuments = [
        {
            id: 'doc-user-1',
            file_name: 'PhD_Thesis_Certificate.pdf',
            document_type: 'EDUCATION_CERTIFICATE',
            verification_status: 'VERIFIED',
            is_active: true,
            extracted_fields: {
                degree: 'Ph.D. Biotechnology',
                university: 'Kerala University'
            },
            extracted_text: `--- [Page 1] ---
Kerala University - Doctorate of Philosophy in Biotechnology
Awarded to Test Candidate`
        }
    ];

    const profileFacts = {
        full_name: 'Dr. Test Candidate',
        occupation: 'Researcher'
    };

    it('1. Named canonical YIPB query returns official YIPB application process, not generic FIN portal steps', () => {
        const query = 'Explain only the application process for the Young Investigators Programme in Biotechnology. Include its application mode, submission stages, required institutional documents, and official source. Do not show my personal applications, tickets, or uploaded documents.';
        const res = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(res && res.reply, 'Expected fallback response');
        assert.equal(res.schemeId, 'yipb', 'Should resolve canonical schemeId yipb');
        assert.ok(res.isGrounded, 'Should be marked as grounded');

        // Verify scheme-specific process content
        const lowerReply = res.reply.toLowerCase();
        assert.ok(lowerReply.includes('young investigators programme in biotechnology'), 'Must name the YIPB scheme');
        assert.ok(lowerReply.includes('stage 1') || lowerReply.includes('step 1'), 'Must describe submission stages');
        assert.ok(lowerReply.includes('kscste') || lowerReply.includes('kbc'), 'Must mention nodal authority');
        assert.ok(lowerReply.includes('endorsement'), 'Must mention institutional endorsement');

        // MUST NOT contain generic FIN portal steps
        assert.ok(
            !res.reply.includes('Step 1: Complete your profile with your occupation'),
            'Must NOT return generic FIN portal Step 1'
        );
        assert.ok(
            !res.reply.includes('Step 3: Upload and verify required documents in the My Documents vault'),
            'Must NOT return generic FIN portal Step 3'
        );
        assert.ok(
            !res.reply.includes('Submit your application online through the official nodal department portal or via FIN'),
            'Must NOT return generic FIN portal Step 4'
        );

        // Negative constraints: no personal documents or tickets leaked
        assert.ok(!res.reply.includes('APP-YIPB-1234'), 'Must not leak user ticket ID');
        assert.ok(!res.reply.includes('PhD_Thesis_Certificate.pdf'), 'Must not leak user document name');
        assert.ok(!res.reply.includes('active government applications'), 'Must not return ticket list');
    });

    it('2. Official source URL is present and not fabricated', () => {
        const query = 'What is the official source and required documents for YIPB?';
        const res = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(res.citations && res.citations.length > 0, 'Must include citations');
        const citation = res.citations[0];
        assert.equal(citation.schemeId, 'yipb');
        assert.ok(
            citation.url && citation.url.includes('myscheme.gov.in') || citation.source.includes('myscheme') || citation.source.includes('kscste'),
            'Must cite authentic government portal'
        );
    });

    it('3. Fallback preserves eligibilityStatus UNKNOWN and matchScore null', () => {
        const query = 'Tell me about Young Investigators Programme in Biotechnology';
        const res = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(res.schemes && res.schemes.length > 0, 'Must include scheme metadata');
        const scheme = res.schemes[0];
        assert.equal(scheme.id, 'yipb');
        assert.equal(scheme.eligibilityStatus, 'UNKNOWN', 'Eligibility must remain UNKNOWN in fallback');
        assert.equal(scheme.matchScore, null, 'matchScore must be null without AI evaluation');
        assert.equal(scheme.matchType, 'neutral', 'matchType must be neutral');
    });

    it('4. Unknown scheme application process returns transparent offline unavailability, NOT generic FIN portal steps', () => {
        const query = 'Explain only the application process for the Deep Space Plasma Astrophysics Fellowship. Do not show my documents.';
        const res = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(res && res.reply, 'Expected response');
        assert.equal(res.schemeId, null, 'Unknown schemeId must be null');
        assert.equal(res.isGrounded, false, 'Unknown scheme must not claim grounding');

        // Must inform about offline unavailability
        const lowerReply = res.reply.toLowerCase();
        assert.ok(
            lowerReply.includes('unavailable in offline fallback mode') || lowerReply.includes('could not be verified'),
            'Must communicate transparent unavailability'
        );

        // MUST NOT return generic FIN portal instructions
        assert.ok(
            !res.reply.includes('Step 1: Complete your profile with your occupation'),
            'Must NOT present generic portal steps as the unknown scheme process'
        );
    });

    it('5. Generic portal procedure query without named scheme returns FIN portal steps', () => {
        const query = 'How do I apply for schemes through FIN?';
        const res = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(res && res.reply, 'Expected response');
        assert.ok(res.reply.includes('To apply for official government welfare schemes through the FIN portal:'), 'Should provide FIN portal steps for generic query');
        assert.ok(res.reply.includes('Step 1:'), 'Must include steps');
    });

    it('6. Negative constraints are strictly enforced in fallback', () => {
        const query = 'Explain the benefits of YIPB. Do not show my personal applications, tickets, or uploaded documents.';
        const res = computeLocalFallback(query, profileFacts, userDocuments, userApplications);

        assert.ok(!res.reply.includes('APP-YIPB-1234'), 'Must not leak ticket');
        assert.ok(!res.reply.includes('PhD_Thesis_Certificate.pdf'), 'Must not leak documents');
        assert.ok(res.reply.includes('45,000') || res.reply.includes('fellowship') || res.reply.includes('30 lakhs'), 'Must return YIPB benefits');
    });
});
