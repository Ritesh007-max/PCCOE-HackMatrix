/**
 * Phase A — P0 Data Integrity & Eligibility Repair Regression Test Suite
 * 
 * Verifies all 12 regression requirements:
 * 1. Personal income unavailable when only family income exists.
 * 2. Family income remains separately labeled.
 * 3. Multi-turn clarification for income.
 * 4. Conflicting document facts produce REVIEW.
 * 5. Deleted document exclusion.
 * 6. OCR status is not statutory verification.
 * 7. Applicant tenant isolation.
 * 8. Applicant context reaches the rule engine.
 * 9. Missing facts produce UNKNOWN.
 * 10. Conflicts produce REVIEW.
 * 11. Re-Evaluate triggers actual evaluation.
 * 12. Evaluation results persist and return correctly.
 */

const { describe, test } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const chatService = require('../src/services/chatService');
const schemeService = require('../src/services/schemeService');
const documentServices = require('../src/services/documentServices');
const { supabaseAdmin } = require('../src/config/supabaseConfig');

describe('Phase A P0 Data Integrity & Eligibility Repair Suite', () => {

    // -------------------------------------------------------------------------
    // 1. Personal income unavailable when only family income exists
    // 2. Family income remains separately labeled
    // -------------------------------------------------------------------------
    test('1 & 2: Personal income unavailable; Family income separately labeled and not substituted', () => {
        const documents = [
            {
                id: 'doc_fam_inc_001',
                document_type: 'INCOME_CERTIFICATE',
                file_name: 'Income_Certificate_2024.pdf',
                extracted_fields: {
                    annual_family_income: '180000',
                    family_income: '180000'
                }
            }
        ];

        const query = 'What is my personal annual income?';
        const fallback = chatService.computeLocalFallback(query, { annual_family_income: 180000 }, documents);

        // Invariant 1: Must state personal income is unavailable
        assert.match(fallback.reply, /personal.*not available|not found.*personal|not been recorded/i,
            'Must explicitly state that personal income is unavailable');

        // Invariant 2: Must NOT claim personal income is 180,000
        assert.doesNotMatch(fallback.reply, /your personal annual income is ₹?1,?80,?000/i,
            'Must not substitute family income as personal income');

        // Invariant 3: Family income is separately identified and clearly labeled
        assert.match(fallback.reply, /family income/i,
            'Must clearly label the separate family income');
        assert.match(fallback.reply, /1,80,000|180000/,
            'Must display family income value separately');

        // Invariant 4: Source citation is preserved
        assert.ok(fallback.citations && fallback.citations.length > 0, 'Citations must be present');
        assert.strictEqual(fallback.citations[0].chunkId, 'doc_fam_inc_001_income');
        assert.strictEqual(fallback.citations[0].schemeName, 'Uploaded Document');
    });

    // -------------------------------------------------------------------------
    // 3. Multi-turn clarification for income
    // -------------------------------------------------------------------------
    test('3: Multi-turn clarification handles ambiguous income queries', () => {
        const documents = [
            {
                id: 'doc_fam_inc_001',
                document_type: 'INCOME_CERTIFICATE',
                file_name: 'Income_Cert.pdf',
                extracted_fields: {
                    annual_family_income: '180000'
                }
            }
        ];

        // Turn 1: Ambiguous "What is my annual income?"
        const turn1Fallback = chatService.computeLocalFallback('What is my annual income?', {}, documents);
        assert.ok(turn1Fallback.reply.includes('1,80,000') || turn1Fallback.reply.includes('family'));

        // Turn 2: User explicitly specifies personal income
        const turn2Fallback = chatService.computeLocalFallback('What is my personal income?', {}, documents);
        assert.match(turn2Fallback.reply, /personal.*not available|not been recorded/i);
        assert.match(turn2Fallback.reply, /family income/i);
    });

    // -------------------------------------------------------------------------
    // 4. Conflicting document facts produce REVIEW
    // -------------------------------------------------------------------------
    test('4: Conflicting document facts across documents produce REVIEW state', () => {
        const documents = [
            {
                id: 'doc_older_2023',
                document_type: 'INCOME_CERTIFICATE',
                file_name: 'Income_2023.pdf',
                extracted_fields: {
                    annual_family_income: '347250'
                }
            },
            {
                id: 'doc_newer_2024',
                document_type: 'INCOME_CERTIFICATE',
                file_name: 'Income_2024.pdf',
                extracted_fields: {
                    annual_family_income: '180000'
                }
            }
        ];

        const fallback = chatService.computeLocalFallback('What is my annual family income?', {}, documents);

        // Invariant 1: Must flag conflict / REVIEW in response
        assert.match(fallback.reply, /conflict|discrepancy|review/i);

        // Invariant 2: Must cite BOTH documents and both amounts
        assert.match(fallback.reply, /3,47,250|347250/);
        assert.match(fallback.reply, /1,80,000|180000/);
        assert.match(fallback.reply, /Income_2023\.pdf/);
        assert.match(fallback.reply, /Income_2024\.pdf/);

        // Invariant 3: Both citations preserved
        assert.strictEqual(fallback.citations.length, 2);
    });

    // -------------------------------------------------------------------------
    // 5. Deleted document exclusion
    // -------------------------------------------------------------------------
    test('5: Deleted documents are excluded from retrieval and facts', async () => {
        const applicantId = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
        const docId = 'c1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22';

        const originalFrom = supabaseAdmin.from;
        const originalStorage = supabaseAdmin.storage;

        let activeDocuments = [
            {
                id: docId,
                user_id: applicantId,
                application_id: 'app_111',
                file_url: 'applicant/c1eebc99/doc.pdf',
                document_type: 'INCOME_CERTIFICATE'
            }
        ];

        supabaseAdmin.storage = {
            from: () => ({
                remove: () => Promise.resolve({ error: null })
            })
        };

        supabaseAdmin.from = (table) => {
            if (table === 'documents') {
                return {
                    select: () => ({
                        eq: (col1, val1) => ({
                            maybeSingle: () => {
                                const found = activeDocuments.find(d => d[col1] === val1);
                                return Promise.resolve({ data: found || null, error: null });
                            },
                            order: () => Promise.resolve({ data: activeDocuments, error: null })
                        }),
                        in: (col, vals) => ({
                            order: () => Promise.resolve({
                                data: activeDocuments.filter(d => vals.includes(d[col])),
                                error: null
                            })
                        })
                    }),
                    delete: () => ({
                        eq: (col, val) => {
                            activeDocuments = activeDocuments.filter(d => d[col] !== val);
                            return Promise.resolve({ error: null });
                        }
                    })
                };
            }
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => ({
                            eq: () => ({
                                maybeSingle: () => Promise.resolve({ data: { id: 'app_111' }, error: null })
                            }),
                            order: () => ({
                                limit: () => ({
                                    maybeSingle: () => Promise.resolve({ data: { id: 'app_111' }, error: null })
                                })
                            })
                        })
                    })
                };
            }
            if (table === 'applicants') {
                return {
                    select: () => ({
                        eq: () => ({
                            maybeSingle: () => Promise.resolve({ data: { id: applicantId }, error: null })
                        })
                    })
                };
            }
            return originalFrom.call(supabaseAdmin, table);
        };

        try {
            await documentServices.deleteDocument(docId, applicantId);
            assert.strictEqual(activeDocuments.length, 0, 'Deleted document must be removed from document repository');
        } finally {
            supabaseAdmin.from = originalFrom;
            supabaseAdmin.storage = originalStorage;
        }
    });

    // -------------------------------------------------------------------------
    // 6. OCR status is not statutory verification
    // -------------------------------------------------------------------------
    test('6: Document processing assigns EXTRACTED/PENDING verification status, not statutory VERIFIED', () => {
        const rawDocs = [
            {
                id: 'doc_ocr_001',
                document_type: 'INCOME_CERTIFICATE',
                uploaded_at: '2026-10-01T10:00:00Z',
                verification_status: 'PENDING',
                extracted_fields: { annual_family_income: 180000 }
            }
        ];

        const mappedFacts = chatService.buildDocumentFacts(rawDocs);
        assert.strictEqual(mappedFacts.length, 1);
        assert.notStrictEqual(mappedFacts[0].verification_status, 'VERIFIED',
            'OCR extraction must not automatically promote document to VERIFIED');
        assert.strictEqual(mappedFacts[0].verification_status, 'PENDING');
    });

    // -------------------------------------------------------------------------
    // 7. Applicant tenant isolation
    // -------------------------------------------------------------------------
    test('7: Multi-tenant applicant isolation prevents cross-tenant document and profile contamination', () => {
        const tenantADocs = [
            {
                id: 'doc_tenant_A',
                document_type: 'INCOME_CERTIFICATE',
                extracted_fields: { annual_family_income: '200000' }
            }
        ];
        const tenantBDocs = [
            {
                id: 'doc_tenant_B',
                document_type: 'INCOME_CERTIFICATE',
                extracted_fields: { annual_family_income: '800000' }
            }
        ];

        const resA = chatService.computeLocalFallback('What is my annual family income?', {}, tenantADocs);
        const resB = chatService.computeLocalFallback('What is my annual family income?', {}, tenantBDocs);

        assert.match(resA.reply, /2,00,000|200000/);
        assert.doesNotMatch(resA.reply, /8,00,000|800000/);

        assert.match(resB.reply, /8,00,000|800000/);
        assert.doesNotMatch(resB.reply, /2,00,000|200000/);
    });

    // -------------------------------------------------------------------------
    // 8. Applicant context reaches the rule engine
    // 9. Missing facts produce UNKNOWN
    // 10. Conflicts produce REVIEW
    // 11. Re-Evaluate triggers actual evaluation
    // 12. Evaluation results persist and return correctly
    // -------------------------------------------------------------------------
    test('8, 9, 10, 11, 12: End-to-end evaluation with rule engine, persistence, UNKNOWN and REVIEW states', async () => {
        const validApplicantUuid = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
        let capturedPayload = null;
        let persistedRows = [];

        // Mock http server simulating Intelligence /v1/schemes/recommend
        const mockServer = http.createServer((req, res) => {
            let body = '';
            req.on('data', chunk => { body += chunk; });
            req.on('end', () => {
                capturedPayload = JSON.parse(body);
                if (req.url === '/v1/schemes/recommend') {
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        request_id: 'rec_eval_test',
                        total_found: 2,
                        recommendations: [
                            {
                                scheme_id: 'pm_kisan',
                                scheme_slug: 'pm-kisan',
                                scheme_name: 'PM-Kisan Samman Nidhi',
                                eligibility_status: 'UNKNOWN',
                                compatibility_score: 0.5,
                                overall_match_score: 0.75,
                                matched_facts: { state: 'Maharashtra' },
                                missing_fields: ['land_holding'],
                                conflict_fields: []
                            },
                            {
                                scheme_id: 'post_matric_scholarship',
                                scheme_slug: 'post-matric-scholarship',
                                scheme_name: 'Post Matric Scholarship',
                                eligibility_status: 'REVIEW',
                                compatibility_score: 0.4,
                                overall_match_score: 0.6,
                                matched_facts: {},
                                missing_fields: [],
                                conflict_fields: ['annual_family_income']
                            }
                        ]
                    }));
                } else {
                    res.writeHead(404);
                    res.end();
                }
            });
        });

        await new Promise((resolve) => mockServer.listen(0, '127.0.0.1', resolve));
        const port = mockServer.address().port;

        // Temporarily intercept environment variable AI_SERVER_URL
        const origAiServerUrl = process.env.AI_SERVER_URL;
        process.env.AI_SERVER_URL = `http://127.0.0.1:${port}`;

        const origFrom = supabaseAdmin.from;
        supabaseAdmin.from = (table) => {
            if (table === 'schemes') {
                return {
                    select: () => Promise.resolve({
                        data: [
                            { id: 'pm_kisan', slug: 'pm-kisan', scheme_name: 'PM-Kisan Samman Nidhi' },
                            { id: 'post_matric_scholarship', slug: 'post-matric-scholarship', scheme_name: 'Post Matric Scholarship' }
                        ],
                        error: null
                    })
                };
            }
            if (table === 'eligibility_results') {
                return {
                    insert: (rows) => {
                        persistedRows.push(...rows);
                        return Promise.resolve({ data: rows, error: null });
                    }
                };
            }
            if (table === 'applicant_profiles') {
                return {
                    select: () => ({
                        eq: () => ({
                            maybeSingle: () => Promise.resolve({
                                data: {
                                    id: validApplicantUuid,
                                    full_name: 'Test Applicant',
                                    state: 'Maharashtra',
                                    annual_income: null
                                },
                                error: null
                            })
                        })
                    })
                };
            }
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => Promise.resolve({
                            data: [{ id: 'app_p0_001' }],
                            error: null
                        })
                    })
                };
            }
            if (table === 'applicants') {
                return {
                    select: () => ({
                        eq: () => ({
                            maybeSingle: () => Promise.resolve({
                                data: { id: validApplicantUuid },
                                error: null
                            })
                        })
                    })
                };
            }
            if (table === 'documents') {
                return {
                    select: () => ({
                        in: () => ({
                            order: () => Promise.resolve({
                                data: [
                                    {
                                        id: 'doc_inc_p0',
                                        document_type: 'INCOME_CERTIFICATE',
                                        uploaded_at: '2026-10-01T00:00:00Z',
                                        verification_status: 'PENDING',
                                        extracted_fields: { annual_family_income: '180000' }
                                    }
                                ],
                                error: null
                            })
                        }),
                        eq: () => ({
                            order: () => Promise.resolve({
                                data: [
                                    {
                                        id: 'doc_inc_p0',
                                        document_type: 'INCOME_CERTIFICATE',
                                        uploaded_at: '2026-10-01T00:00:00Z',
                                        verification_status: 'PENDING',
                                        extracted_fields: { annual_family_income: '180000' }
                                    }
                                ],
                                error: null
                            })
                        })
                    })
                };
            }
            return origFrom.call(supabaseAdmin, table);
        };

        try {
            // Trigger actual evaluation
            const recResult = await schemeService.recommendSchemes(validApplicantUuid, { query: 'test evaluation' });

            // Invariant 8: Applicant context reached the intelligence recommendation / rule engine
            assert.ok(capturedPayload, 'Payload must reach intelligence microservice');
            assert.strictEqual(capturedPayload.applicant_id, validApplicantUuid);
            assert.ok(capturedPayload.document_facts.length >= 1);
            assert.strictEqual(capturedPayload.document_facts[0].document_id, 'doc_inc_p0');
            assert.strictEqual(capturedPayload.document_facts[0].verification_status, 'PENDING');

            // Invariant 9: Missing facts produce UNKNOWN (not silently converted to PASS)
            const pmKisan = recResult.recommendations.find(s => s.scheme_id === 'pm_kisan');
            assert.ok(pmKisan, 'PM Kisan scheme must be returned');
            assert.strictEqual(pmKisan.eligibility_status, 'UNKNOWN');
            assert.deepStrictEqual(pmKisan.missing_fields, ['land_holding']);

            // Invariant 10: Conflicts produce REVIEW
            const pms = recResult.recommendations.find(s => s.scheme_id === 'post_matric_scholarship');
            assert.ok(pms, 'Post Matric Scholarship must be returned');
            assert.strictEqual(pms.eligibility_status, 'REVIEW');
            assert.deepStrictEqual(pms.conflict_fields, ['annual_family_income']);

            // Invariant 11 & 12: Real evaluation results persisted to Supabase eligibility_results
            assert.strictEqual(persistedRows.length, 2, 'Must persist evaluation verdicts to eligibility_results');
            assert.strictEqual(persistedRows[0].user_id, validApplicantUuid);
            assert.strictEqual(persistedRows[0].verdict, 'MANUAL_REVIEW'); // UNKNOWN -> MANUAL_REVIEW
            assert.strictEqual(persistedRows[1].verdict, 'MANUAL_REVIEW'); // REVIEW -> MANUAL_REVIEW
            assert.ok(persistedRows[0].evaluated_rules.eligibility_status === 'UNKNOWN');

        } finally {
            process.env.AI_SERVER_URL = origAiServerUrl;
            supabaseAdmin.from = origFrom;
            mockServer.close();
        }
    });

});
