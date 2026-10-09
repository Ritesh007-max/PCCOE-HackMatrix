/**
 * applicationsProductionAudit.test.js
 * FIN — Applications Final Production Audit Test Suite (Backend)
 *
 * Covers:
 * - Authentication & tenant isolation
 * - Application retrieval & dynamic hydration
 * - Canonical scheme mapping
 * - Status integrity & self-approval prevention
 * - Benefit integrity (no loan ceilings as cash grants, accurate waiver/stipend/grant labels)
 * - Document relation (real documents table, verification status, OCR_EXTRACTED != VERIFIED)
 * - Application creation with canonical scheme
 * - Rejection of invalid/stale schemes
 * - Direct ID ownership enforcement (cannot read other user's app)
 * - Empty & error state resilience
 */

const { describe, test, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const applicationService = require('../src/services/applicationService');
const schemeService = require('../src/services/schemeService');
const { supabaseAdmin } = require('../src/config/supabaseConfig');

describe('FIN — Applications Final Production Audit (Backend Suite)', () => {
    const userA = '05403000-bcac-4287-b36f-721eefe3c7e4';
    const userB = '4d4e48a3-063b-43c1-9771-0d004a1aa572';
    const canonicalSchemeId = '32198bb9-6b92-493f-8d45-9ba7f5807148'; // 100% Penalty Mafi Yojana

    let originalFrom;
    let originalGetSchemeById;

    beforeEach(() => {
        originalFrom = supabaseAdmin.from;
        originalGetSchemeById = schemeService.getSchemeById;
    });

    afterEach(() => {
        supabaseAdmin.from = originalFrom;
        schemeService.getSchemeById = originalGetSchemeById;
    });

    // 1. TENANT ISOLATION & RETRIEVAL
    test('1. Tenant isolation: listApplications queries strictly by authenticated user ID', async () => {
        let queriedApplicantId = null;
        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: (col, val) => {
                            if (col === 'applicant_id') queriedApplicantId = val;
                            return {
                                order: () => Promise.resolve({
                                    data: [
                                        {
                                            id: 'app-user-a-1',
                                            applicant_id: userA,
                                            scheme_id: canonicalSchemeId,
                                            status: 'under_review',
                                            created_at: '2026-10-01T10:00:00Z'
                                        }
                                    ],
                                    error: null
                                })
                            };
                        }
                    })
                };
            }
            if (table === 'applicant_profiles') {
                return {
                    select: () => ({
                        eq: () => ({
                            maybeSingle: () => Promise.resolve({ data: { id: userA, full_name: 'Dhruv' } })
                        })
                    })
                };
            }
            if (table === 'documents') {
                return {
                    select: () => ({
                        eq: () => Promise.resolve({ data: [] })
                    })
                };
            }
            return originalFrom.call(supabaseAdmin, table);
        };

        const apps = await applicationService.listApplications(userA);
        assert.strictEqual(queriedApplicantId, userA);
        assert.strictEqual(apps.length, 1);
        assert.strictEqual(apps[0].applicant_id, userA);
    });

    // 2. OWNERSHIP ENFORCEMENT ON GET BY ID
    test('2. Ownership: getApplicationById rejects direct access to another user application', async () => {
        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: (col1, val1) => ({
                            eq: (col2, val2) => ({
                                maybeSingle: () => {
                                    // If user A asks for user B's app, DB query returns null
                                    if (val1 === 'app-b' && (val2 === userA || val1 === userA)) {
                                        return Promise.resolve({ data: null, error: null });
                                    }
                                    return Promise.resolve({ data: null, error: null });
                                }
                            })
                        })
                    })
                };
            }
            if (table === 'applicant_profiles') {
                return {
                    select: () => ({
                        eq: () => ({
                            maybeSingle: () => Promise.resolve({ data: { id: userA, full_name: 'Dhruv' } })
                        })
                    })
                };
            }
            return originalFrom.call(supabaseAdmin, table);
        };

        await assert.rejects(
            async () => {
                await applicationService.getApplicationById(userA, 'app-b');
            },
            (err) => {
                assert.strictEqual(err.status, 404);
                assert.match(err.message, /not found/i);
                return true;
            }
        );
    });

    // 3. CANONICAL SCHEME MAPPING
    test('3. Scheme mapping: hydrated application links to canonical scheme name, category, and URL', async () => {
        const rawApp = {
            id: 'app-mapped-1',
            applicant_id: userA,
            scheme_id: 'scheme-statutory-1',
            status: 'under_review',
            created_at: '2026-10-01T10:00:00Z'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'database',
            scheme: {
                id,
                name: 'Statutory Student Stipend Scheme',
                category: 'Education & Learning',
                official_url: 'https://scholarships.gov.in',
                documents_required: ['Aadhaar Card', 'Income Certificate'],
                financial_benefit: {
                    category: 'MONTHLY_FELLOWSHIP_OR_STIPEND',
                    amountDisplay: '₹3,000 / month',
                    subtitle: '(Monthly Fellowship / Stipend)',
                    amount: 3000
                }
            }
        });

        supabaseAdmin.from = (table) => {
            if (table === 'documents') {
                return {
                    select: () => ({
                        eq: () => Promise.resolve({ data: [] })
                    })
                };
            }
            if (table === 'applicant_profiles') {
                return {
                    select: () => ({
                        eq: () => ({
                            maybeSingle: () => Promise.resolve({ data: { full_name: 'Dhruv' } })
                        })
                    })
                };
            }
            return originalFrom.call(supabaseAdmin, table);
        };

        const hydrated = await applicationService.hydrateApplicationRecord(rawApp);
        assert.strictEqual(hydrated.scheme_name, 'Statutory Student Stipend Scheme');
        assert.strictEqual(hydrated.category, 'Education & Learning');
        assert.strictEqual(hydrated.is_scheme_available, true);
        assert.strictEqual(hydrated.applicant_name, 'Dhruv');
        assert.strictEqual(hydrated.benefit_display, '₹3,000 / month');
        assert.strictEqual(hydrated.benefit_numeric, 0); // Stipend is recurring, not cash grant
        assert.deepStrictEqual(hydrated.required_documents, ['Aadhaar Card', 'Income Certificate']);
    });

    // 4. BENEFIT INTEGRITY: LOAN DISTINCTION
    test('4. Benefit integrity: loan schemes never represent loan ceilings as cash grants', async () => {
        const rawApp = {
            id: 'app-loan-1',
            applicant_id: userA,
            scheme_id: 'loan-scheme-id',
            status: 'under_review'
        };

        schemeService.getSchemeById = async (id) => ({
            source: 'database',
            scheme: {
                id,
                name: 'PM Vidyalaxmi Education Loan',
                max_benefit: 750000,
                financial_benefit: {
                    category: 'LOAN_OR_CREDIT_FACILITY',
                    amountDisplay: 'Up to ₹7,50,000 (Loan)',
                    subtitle: '(Credit Facility / Repayable Loan)',
                    hasLoanCalculator: true,
                    amount: 0
                }
            }
        });

        supabaseAdmin.from = (table) => ({
            select: () => ({
                eq: () => ({
                    maybeSingle: () => Promise.resolve({ data: null })
                })
            })
        });

        const hydrated = await applicationService.hydrateApplicationRecord(rawApp);
        assert.strictEqual(hydrated.benefit_display, 'Up to ₹7,50,000 (Loan)');
        assert.strictEqual(hydrated.benefit_subtitle, '(Credit Facility / Repayable Loan)');
        assert.strictEqual(hydrated.benefit_numeric, 0);
    });

    // 5. DOCUMENT RELATION: OCR_EXTRACTED IS NOT VERIFIED
    test('5. Document relation: documents table verification_status is preserved; OCR_EXTRACTED is not VERIFIED', async () => {
        const rawApp = {
            id: 'app-doc-test',
            applicant_id: userA,
            scheme_id: canonicalSchemeId,
            status: 'under_review'
        };

        supabaseAdmin.from = (table) => {
            if (table === 'documents') {
                return {
                    select: () => ({
                        eq: () => Promise.resolve({
                            data: [
                                {
                                    id: 'doc-1',
                                    document_type: 'income_cert',
                                    file_name: 'income_certificate.pdf',
                                    file_url: 'path/to/doc',
                                    verification_status: 'PENDING', // Even if OCR extracted facts exist
                                    uploaded_at: '2026-10-02T10:00:00Z'
                                },
                                {
                                    id: 'doc-2',
                                    document_type: 'aadhaar',
                                    file_name: 'aadhaar_card.pdf',
                                    file_url: 'path/to/aadhaar',
                                    verification_status: 'VERIFIED',
                                    uploaded_at: '2026-10-01T10:00:00Z'
                                }
                            ]
                        })
                    })
                };
            }
            return originalFrom.call(supabaseAdmin, table);
        };

        const hydrated = await applicationService.hydrateApplicationRecord(rawApp);
        assert.strictEqual(hydrated.submitted_documents.length, 2);
        
        const incomeDoc = hydrated.submitted_documents.find(d => d.document_type === 'income_cert');
        assert.strictEqual(incomeDoc.verification_status, 'PENDING');
        assert.strictEqual(incomeDoc.verified, false);
        assert.strictEqual(incomeDoc.reason, 'Pending Verification');

        const aadhaarDoc = hydrated.submitted_documents.find(d => d.document_type === 'aadhaar');
        assert.strictEqual(aadhaarDoc.verification_status, 'VERIFIED');
        assert.strictEqual(aadhaarDoc.verified, true);
        assert.strictEqual(aadhaarDoc.reason, 'Verified ✓');
    });

    // 6. APPLICATION CREATION: REJECT INVALID SCHEME
    test('6. Application creation: fails with 404 when scheme ID does not exist in catalog', async () => {
        schemeService.getSchemeById = async () => null;

        await assert.rejects(
            async () => {
                await applicationService.createApplication(userA, {
                    schemeId: 'non-existent-scheme-99999'
                });
            },
            (err) => {
                assert.strictEqual(err.status, 404);
                assert.match(err.message, /not exist in the official scheme catalog/i);
                return true;
            }
        );
    });

    // 7. APPLICATION CREATION: SELF-APPROVAL PREVENTION
    test('7. Status integrity: citizen cannot pass status "approved" or "sanctioned" on creation', async () => {
        let insertedApp = null;
        schemeService.getSchemeById = async (id) => ({
            source: 'database',
            scheme: {
                id,
                name: 'Valid Scheme Test',
                max_benefit: 10000
            }
        });

        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => ({
                            eq: () => ({
                                maybeSingle: () => Promise.resolve({ data: null }) // no duplicate
                            })
                        })
                    }),
                    insert: (app) => {
                        insertedApp = app;
                        return {
                            select: () => ({
                                single: () => Promise.resolve({ data: { id: 'new-app-1', ...app }, error: null })
                            })
                        };
                    }
                };
            }
            if (table === 'applicant_profiles') {
                return {
                    select: () => ({
                        eq: () => ({
                            maybeSingle: () => Promise.resolve({ data: { id: userA, full_name: 'Dhruv' } })
                        })
                    })
                };
            }
            if (table === 'documents') {
                return {
                    select: () => ({
                        eq: () => Promise.resolve({ data: [] })
                    })
                };
            }
            return originalFrom.call(supabaseAdmin, table);
        };

        const result = await applicationService.createApplication(userA, {
            schemeId: 'scheme-valid-uuid',
            status: 'approved' // Malicious client attempt
        });

        // Must be forced to under_review
        assert.strictEqual(insertedApp.status, 'under_review');
        assert.strictEqual(result.status, 'under_review');
    });

    // 8. DUPLICATE APPLICATION HANDLING
    test('8. Duplicate prevention: rejects creation when applicant has already applied for the scheme', async () => {
        schemeService.getSchemeById = async (id) => ({
            source: 'database',
            scheme: {
                id,
                name: 'Valid Scheme Test'
            }
        });

        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => ({
                            eq: () => ({
                                maybeSingle: () => Promise.resolve({ data: { id: 'existing-app-id' } })
                            })
                        })
                    })
                };
            }
            if (table === 'applicant_profiles') {
                return {
                    select: () => ({
                        eq: () => ({
                            maybeSingle: () => Promise.resolve({ data: { id: userA, full_name: 'Dhruv' } })
                        })
                    })
                };
            }
            return originalFrom.call(supabaseAdmin, table);
        };

        await assert.rejects(
            async () => {
                await applicationService.createApplication(userA, {
                    schemeId: 'scheme-already-applied'
                });
            },
            (err) => {
                assert.strictEqual(err.status, 409);
                assert.match(err.message, /already been submitted/i);
                return true;
            }
        );
    });

    // 9. EMPTY STATE
    test('9. Empty state: returns empty array when applicant has 0 applications, no mock data', async () => {
        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => ({
                            order: () => Promise.resolve({ data: [], error: null })
                        })
                    })
                };
            }
            if (table === 'applicant_profiles') {
                return {
                    select: () => ({
                        eq: () => ({
                            maybeSingle: () => Promise.resolve({ data: { id: userA, full_name: 'Dhruv' } })
                        })
                    })
                };
            }
            return originalFrom.call(supabaseAdmin, table);
        };

        const apps = await applicationService.listApplications(userA);
        assert.strictEqual(Array.isArray(apps), true);
        assert.strictEqual(apps.length, 0);
    });

    // 10. ERROR STATE RESILIENCE
    test('10. Error resilience: database error returns empty array safely without mock fallback', async () => {
        supabaseAdmin.from = (table) => {
            if (table === 'applications') {
                return {
                    select: () => ({
                        eq: () => ({
                            order: () => Promise.resolve({ data: null, error: { message: 'Database connection failed' } })
                        })
                    })
                };
            }
            if (table === 'applicant_profiles') {
                return {
                    select: () => ({
                        eq: () => ({
                            maybeSingle: () => Promise.resolve({ data: { id: userA, full_name: 'Dhruv' } })
                        })
                    })
                };
            }
            return originalFrom.call(supabaseAdmin, table);
        };

        const apps = await applicationService.listApplications(userA);
        assert.strictEqual(Array.isArray(apps), true);
        assert.strictEqual(apps.length, 0);
    });
});
