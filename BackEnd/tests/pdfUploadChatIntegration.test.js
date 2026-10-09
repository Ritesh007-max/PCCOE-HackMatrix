const { test, describe, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');
const { validateUploadedFile } = require('../src/middleware/upload');
const documentServices = require('../src/services/documentServices');
const chatService = require('../src/services/chatService');
const { HEADER_NAME, AI_SERVICE_API_KEY } = require('../src/config/intelligenceConfig');

describe('PART 9 — Comprehensive PDF Upload & AI Chat Document Awareness Integration Tests', () => {

    // ─────────────────────────────────────────────────────────────────────────
    // 1. Upload Validation Tests (Part 1 & 2)
    // ─────────────────────────────────────────────────────────────────────────
    describe('PDF Validation & Magic Bytes Verification', () => {
        const createMockReqRes = (file) => {
            const req = { file };
            let statusCode = 200;
            let responseData = null;
            let nextCalled = false;
            let errorPassed = null;

            const res = {
                status(code) {
                    statusCode = code;
                    return this;
                },
                json(data) {
                    responseData = data;
                    return this;
                }
            };

            const next = (err) => {
                nextCalled = true;
                if (err) {
                    errorPassed = err;
                    statusCode = err.status || 500;
                    responseData = { message: err.message };
                }
            };

            return { req, res, next, getResult: () => ({ statusCode, responseData, nextCalled, errorPassed }) };
        };

        test('1. Valid PDF with %PDF- header is accepted', () => {
            const validPdfBuffer = Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF');
            const { req, res, next, getResult } = createMockReqRes({
                originalname: 'income_certificate.pdf',
                mimetype: 'application/pdf',
                buffer: validPdfBuffer,
                size: validPdfBuffer.length
            });

            validateUploadedFile(req, res, next);
            const { statusCode, nextCalled, errorPassed } = getResult();

            assert.strictEqual(nextCalled, true, 'Next middleware should be called');
            assert.strictEqual(errorPassed, null, 'No error should be passed');
            assert.strictEqual(statusCode, 200);
            assert.strictEqual(req.file.mimetype, 'application/pdf');
        });

        test('2. Uppercase .PDF extension with valid signature is accepted', () => {
            const validPdfBuffer = Buffer.from('%PDF-1.7\n%âãÏÓ\n1 0 obj\n<<>>\nendobj\n%%EOF');
            const { req, res, next, getResult } = createMockReqRes({
                originalname: 'CASTE_CERTIFICATE.PDF',
                mimetype: 'application/pdf',
                buffer: validPdfBuffer,
                size: validPdfBuffer.length
            });

            validateUploadedFile(req, res, next);
            const { nextCalled, errorPassed } = getResult();

            assert.strictEqual(nextCalled, true);
            assert.strictEqual(errorPassed, null);
            assert.strictEqual(req.file.mimetype, 'application/pdf');
        });

        test('3. Generic MIME type (application/octet-stream) with valid %PDF- is safely accepted as PDF', () => {
            const validPdfBuffer = Buffer.from('%PDF-1.5\n%Header info\n%%EOF');
            const { req, res, next, getResult } = createMockReqRes({
                originalname: 'salary_slip.pdf',
                mimetype: 'application/octet-stream',
                buffer: validPdfBuffer,
                size: validPdfBuffer.length
            });

            validateUploadedFile(req, res, next);
            const { nextCalled, errorPassed } = getResult();

            assert.strictEqual(nextCalled, true);
            assert.strictEqual(errorPassed, null);
            assert.strictEqual(req.file.mimetype, 'application/pdf', 'MIME type should be normalized to application/pdf');
        });

        test('4. PNG renamed to .pdf (Spoofed extension) is strictly rejected', () => {
            // PNG header signature: \x89PNG\r\n\x1a\n
            const fakePdfBuffer = Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D]);
            const { req, res, next, getResult } = createMockReqRes({
                originalname: 'fake_document.pdf',
                mimetype: 'application/pdf',
                buffer: fakePdfBuffer,
                size: fakePdfBuffer.length
            });

            validateUploadedFile(req, res, next);
            const { statusCode, responseData, errorPassed } = getResult();

            assert.ok(errorPassed, 'Spoofed file must pass an error to next()');
            assert.strictEqual(statusCode, 400, 'Must return HTTP 400');
            assert.match(responseData.message, /invalid pdf file.*renamed with a \.pdf extension/i);
        });

        test('5. Unsupported file extension (.exe, .sh) is rejected', () => {
            const { req, res, next, getResult } = createMockReqRes({
                originalname: 'malicious_script.exe',
                mimetype: 'application/x-msdownload',
                buffer: Buffer.from('MZ\x90\x00'),
                size: 4
            });

            validateUploadedFile(req, res, next);
            const { statusCode, responseData, errorPassed } = getResult();

            assert.ok(errorPassed);
            assert.strictEqual(statusCode, 400);
            assert.match(responseData.message, /unsupported file extension/i);
        });

        test('6. Oversized document (> 10MB) or empty file is rejected', () => {
            // Test empty
            const { req: reqEmpty, res: resEmpty, next: nextEmpty, getResult: getResultEmpty } = createMockReqRes({
                originalname: 'empty.pdf',
                mimetype: 'application/pdf',
                buffer: Buffer.alloc(0),
                size: 0
            });
            validateUploadedFile(reqEmpty, resEmpty, nextEmpty);
            assert.strictEqual(getResultEmpty().statusCode, 400);
            assert.match(getResultEmpty().responseData.message, /empty/i);

            // Test oversized
            const { req: reqBig, res: resBig, next: nextBig, getResult: getResultBig } = createMockReqRes({
                originalname: 'large.pdf',
                mimetype: 'application/pdf',
                buffer: Buffer.alloc(11 * 1024 * 1024), // 11 MB
                size: 11 * 1024 * 1024
            });
            validateUploadedFile(reqBig, resBig, nextBig);
            assert.strictEqual(getResultBig().statusCode, 400);
            assert.match(getResultBig().responseData.message, /exceeds maximum permissible size/i);
        });
    });

    // ─────────────────────────────────────────────────────────────────────────
    // 2. Document Type Aliases Normalization (Fixing Frontend Mismatch)
    // ─────────────────────────────────────────────────────────────────────────
    describe('Document Type Normalization', () => {
        test('Normalizes frontend aliases safely without throwing 400 Unsupported documentType', () => {
            const { normalizeDocumentType } = documentServices;
            assert.strictEqual(normalizeDocumentType('address'), 'address_proof');
            assert.strictEqual(normalizeDocumentType('other'), 'address_proof');
            assert.strictEqual(normalizeDocumentType('general'), 'address_proof');
            assert.strictEqual(normalizeDocumentType('income'), 'income_cert');
            assert.strictEqual(normalizeDocumentType('income_certificate'), 'income_cert');
            assert.strictEqual(normalizeDocumentType('caste'), 'caste_cert');
            assert.strictEqual(normalizeDocumentType('caste_certificate'), 'caste_cert');
            assert.strictEqual(normalizeDocumentType('bank'), 'bank_passbook');
            assert.strictEqual(normalizeDocumentType('id'), 'aadhaar');
            assert.strictEqual(normalizeDocumentType('identity_proof'), 'aadhaar');
            assert.strictEqual(normalizeDocumentType('unknown_custom_type'), 'address_proof');
        });
    });

    // ─────────────────────────────────────────────────────────────────────────
    // 3. AI Chat Document Awareness Queries (Part 5 Requirements)
    // ─────────────────────────────────────────────────────────────────────────
    describe('AI Chat Document Awareness & 7 Required Inquiry Handlers', () => {
        const testUserAId = 'a1111111-1111-4111-8111-111111111111';
        const testUserBId = 'b2222222-2222-4222-8222-222222222222';

        const mockUserADocuments = [
            {
                id: 'doc-inc-001',
                documentType: 'income_certificate',
                fileName: 'Gujarat_Income_Certificate_2026.pdf',
                verificationStatus: 'VERIFIED',
                docNumber: 'INC/2026/GUJ/88271',
                issuer: 'Mamlatdar Office, Ahmedabad East',
                uploadedAt: '2026-09-15T10:00:00Z',
                extractedData: {
                    beneficiary_name: 'Rajesh Patel',
                    annual_income: '180000',
                    document_number: 'INC/2026/GUJ/88271',
                    issuing_authority: 'Mamlatdar Office, Ahmedabad East',
                    state: 'Gujarat',
                    district: 'Ahmedabad'
                },
                extractedText: `--- [Page 1] ---
Government of Gujarat - Revenue Department
INCOME CERTIFICATE
Certificate No: INC/2026/GUJ/88271
This is to certify that Rajesh Patel, resident of Ahmedabad, Gujarat,
has an annual family income of Rs. 1,80,000/- (Rupees One Lakh Eighty Thousand Only).
Issued by: Mamlatdar Office, Ahmedabad East.

--- [Page 2] ---
Statutory Verification Notes:
Revenue inspection verified under section 14 of the Gujarat Public Records Act.
All tax and land holding exemptions apply.

--- [Page 3] ---
Affidavit & Annexure III:
Verified bank account linked with Aadhaar.
Annual family income verified from agricultural and allied trade earnings.`
            },
            {
                id: 'doc-aadhaar-002',
                documentType: 'identity_proof',
                fileName: 'Aadhaar_Card_Verified.pdf',
                verificationStatus: 'VERIFIED',
                docNumber: 'XXXX-XXXX-4829',
                issuer: 'UIDAI',
                uploadedAt: '2026-09-16T11:00:00Z',
                extractedData: {
                    beneficiary_name: 'Rajesh Patel',
                    document_number: 'XXXX-XXXX-4829',
                    issuing_authority: 'UIDAI',
                    date_of_birth: '1990-05-12'
                },
                extractedText: `--- [Page 1] ---
Unique Identification Authority of India (UIDAI)
Name: Rajesh Patel
DOB: 12/05/1990
Gender: Male
Aadhaar No: XXXX-XXXX-4829`
            }
        ];

        let originalListDocuments;
        let mockServer;
        let mockServerPort;

        before(async () => {
            originalListDocuments = documentServices.listDocuments;
            // Stub document listing per authenticated user ID
            documentServices.listDocuments = async (userId) => {
                if (userId === testUserAId) {
                    return mockUserADocuments;
                }
                return [];
            };

            // Fast mock Intelligence server answering dynamically
            mockServer = http.createServer((req, res) => {
                let body = '';
                req.on('data', chunk => { body += chunk; });
                req.on('end', () => {
                    if (req.url === '/v1/chat' && req.method === 'POST') {
                        const payload = JSON.parse(body);
                        const qLower = (payload.query || '').toLowerCase();
                        const docs = payload.documents || [];

                        let answer = "Grounded response";
                        let citations = [];

                        if (qLower.includes('summarize')) {
                            answer = `Here is a grounded summary of your uploaded document(s) on file in Supabase:\n\n### 📄 Document 1: Income Certificate (Gujarat_Income_Certificate_2026.pdf)\n• Verification Status: Ready for AI Chat (VERIFIED)\n• Document Number: INC/2026/GUJ/88271\n• Beneficiary: Rajesh Patel`;
                            citations = [{
                                chunk_id: 'doc-inc-001_summary',
                                scheme_id: 'USER_DOCUMENT',
                                excerpt: '📄 Gujarat_Income_Certificate_2026.pdf (Page 1) - Verified document summary'
                            }];
                        } else if (qLower.includes('annual family income') || (qLower.includes('income') && qLower.includes('according to'))) {
                            if (docs.length > 0 && docs[0].extracted_fields?.annual_income) {
                                answer = `According to your uploaded document **Gujarat_Income_Certificate_2026.pdf** (Certificate No: INC/2026/GUJ/88271), your annual family income is **₹1,80,000**.\n\n• Issuing Authority: Mamlatdar Office, Ahmedabad East\n• Status: Verified and Ready for AI Chat`;
                                citations = [{
                                    chunk_id: 'doc-inc-001_income',
                                    scheme_id: 'USER_DOCUMENT',
                                    excerpt: '📄 Gujarat_Income_Certificate_2026.pdf (Page 1) - Annual Income: ₹1,80,000'
                                }];
                            } else {
                                answer = "None of your uploaded documents establish your annual family income. Please upload an Income Certificate in the 'My Documents' vault.";
                            }
                        } else if (qLower.includes('which documents') || qLower.includes('what documents')) {
                            answer = `You have uploaded 2 document(s) in your vault:\n1. Income Certificate (Gujarat_Income_Certificate_2026.pdf) — Status: Ready for AI Chat\n2. Identity Proof (Aadhaar_Card_Verified.pdf) — Status: Ready for AI Chat`;
                            citations = [{
                                chunk_id: 'doc-inc-001_list',
                                scheme_id: 'USER_DOCUMENT',
                                excerpt: '📄 Gujarat_Income_Certificate_2026.pdf (Page 1) - Income Certificate'
                            }];
                        } else if (qLower.includes('page 3')) {
                            answer = `According to **Page 3** of your uploaded document **Gujarat_Income_Certificate_2026.pdf**, the following information is mentioned:\n\nAffidavit & Annexure III:\nVerified bank account linked with Aadhaar.\nAnnual family income verified from agricultural and allied trade earnings.`;
                            citations = [{
                                chunk_id: 'doc-inc-001_page_3',
                                scheme_id: 'USER_DOCUMENT',
                                excerpt: '📄 Gujarat_Income_Certificate_2026.pdf (Page 3) - Affidavit & Annexure III: Verified bank account linked with Aadhaar.'
                            }];
                        } else if (qLower.includes('page 99')) {
                            answer = "According to your uploaded document Gujarat_Income_Certificate_2026.pdf, Page 99 does not exist in the document (the document contains 3 page(s)). The document does not establish this answer.";
                        } else if (qLower.includes('income certificate')) {
                            answer = "Yes, your uploaded document Gujarat_Income_Certificate_2026.pdf contains your Income Certificate.\n\n• Document Number: INC/2026/GUJ/88271\n• Recorded Annual Income: ₹180000";
                            citations = [{
                                chunk_id: 'doc-inc-001_income_cert',
                                scheme_id: 'USER_DOCUMENT',
                                excerpt: '📄 Gujarat_Income_Certificate_2026.pdf (Page 1) - Verified Income Certificate'
                            }];
                        } else if (qLower.includes('missing')) {
                            answer = "### Application Document Readiness Check\n\nUploaded: Identity Proof, Income Certificate\nMissing: Bank Account Passbook";
                        } else if (qLower.includes('compare')) {
                            answer = "### Document Comparison for PMEGP\n• Aadhaar Card: Satisfied\n• Income Certificate: Satisfied\n• Project Report: Missing";
                            citations = [{
                                chunk_id: 'doc-inc-001_comp',
                                scheme_id: 'USER_DOCUMENT',
                                excerpt: '📄 Gujarat_Income_Certificate_2026.pdf (Page 1) - Satisfies Income Certificate'
                            }];
                        }

                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({
                            request_id: 'req_doc_awareness_test',
                            conversation_id: payload.conversation_id,
                            answer,
                            intent: 'DOCUMENT_INQUIRY',
                            citations,
                            suggested_schemes: []
                        }));
                    } else {
                        res.writeHead(404);
                        res.end();
                    }
                });
            });

            await new Promise((resolve) => {
                mockServer.listen(0, '127.0.0.1', () => {
                    mockServerPort = mockServer.address().port;
                    process.env.AI_SERVER_URL = `http://127.0.0.1:${mockServerPort}`;
                    resolve();
                });
            });
        });

        after(async () => {
            documentServices.listDocuments = originalListDocuments;
            await new Promise((resolve) => mockServer.close(resolve));
        });

        // Query 1: Summarize uploaded PDF
        test('Q1: "Summarize the PDF I uploaded." returns grounded summary with citations', async () => {
            const res = await chatService.chat(testUserAId, 'Summarize the PDF I uploaded.', [], 'conv-01');
            
            assert.ok(res.reply, 'Should return a reply');
            assert.ok(res.reply.includes('Gujarat_Income_Certificate_2026.pdf') || res.reply.includes('Rajesh Patel'), 'Should include document name or beneficiary');
            assert.ok(res.citations && res.citations.length > 0, 'Must include citations');
            assert.strictEqual(res.citations[0].schemeName, 'Uploaded Document');
            assert.ok(res.citations[0].source.includes('Page 1'), 'Citation should reference Page 1');
        });

        // Query 2: Annual family income according to document
        test('Q2: "What is my annual family income according to my document?" extracts exact income with citation', async () => {
            const res = await chatService.chat(testUserAId, 'What is my annual family income according to my document?', [], 'conv-02');
            
            assert.ok(res.reply.includes('1,80,000') || res.reply.includes('180000'), 'Must contain exact extracted income 1,80,000');
            assert.ok(res.reply.includes('Gujarat_Income_Certificate_2026.pdf') || res.reply.includes('Mamlatdar'), 'Must name source document or issuer');
            assert.ok(res.citations && res.citations.length > 0, 'Must attach document citation');
        });

        // Query 3: Which documents have I uploaded
        test('Q3: "Which documents have I uploaded?" lists documents with "Ready for AI Chat" status', async () => {
            const res = await chatService.chat(testUserAId, 'Which documents have I uploaded?', [], 'conv-03');

            assert.ok(res.reply.includes('Gujarat_Income_Certificate_2026.pdf') || res.reply.includes('Income Certificate'), 'Must list income certificate');
            assert.ok(res.reply.includes('Ready for AI Chat') || res.reply.includes('VERIFIED'), 'Must indicate verification status');
        });

        // Query 4: Information mentioned on Page 3
        test('Q4: "What information is mentioned on page 3?" extracts Page 3 text and cites Page 3', async () => {
            const res = await chatService.chat(testUserAId, 'What information is mentioned on page 3?', [], 'conv-04');

            assert.ok(res.reply.includes('Affidavit & Annexure III') || res.reply.includes('Page 3'), 'Must contain Page 3 specific content');
            assert.ok(res.citations && res.citations.length > 0);
            assert.ok(res.citations[0].source.includes('Page 3') || res.citations[0].excerpt.includes('Page 3'), 'Citation must cite Page 3');
        });

        // Query 4b: Non-existent page query (Zero Hallucination verification)
        test('Q4b: Query for Page 99 gracefully states page does not exist without hallucination', async () => {
            const res = await chatService.chat(testUserAId, 'What information is mentioned on page 99?', [], 'conv-05');

            assert.ok(res.reply.includes('does not exist') || res.reply.includes('does not establish'), 'Must state Page 99 does not exist');
            assert.ok(!res.reply.includes('Affidavit & Annexure III'), 'Must NOT fabricate content for non-existent page');
        });

        // Query 5: Does uploaded document contain income certificate
        test('Q5: "Does my uploaded document contain my income certificate?" answers affirmatively with details', async () => {
            const res = await chatService.chat(testUserAId, 'Does my uploaded document contain my income certificate?', [], 'conv-06');

            assert.ok(res.reply.toLowerCase().includes('yes'), 'Must confirm presence of income certificate');
            assert.ok(res.reply.includes('Gujarat_Income_Certificate_2026.pdf') || res.reply.includes('INC/2026/GUJ/88271'), 'Must cite certificate details');
        });

        // Query 6: What information is missing from application
        test('Q6: "What information is missing from my uploaded application?" returns structured readiness checklist', async () => {
            const res = await chatService.chat(testUserAId, 'What information is missing from my uploaded application?', [], 'conv-07');

            assert.ok(res.reply.includes('Readiness Check') || res.reply.includes('Missing'), 'Must provide readiness check');
            assert.ok(res.reply.includes('Identity Proof') || res.reply.includes('Aadhaar'), 'Must recognize uploaded identity proof');
            assert.ok(res.reply.includes('Bank') || res.reply.includes('Passbook'), 'Must identify missing bank passbook');
        });

        // Query 7: Compare uploaded documents with scheme requirements
        test('Q7: "Compare my uploaded documents with the requirements of this scheme." returns comparison table', async () => {
            const res = await chatService.chat(testUserAId, 'Compare my uploaded documents with the requirements of this scheme.', [], 'conv-08');

            assert.ok(res.reply.includes('Satisfied') || res.reply.includes('Missing'), 'Must compare satisfied vs missing requirements');
            assert.ok(res.reply.includes('PMEGP') || res.reply.includes('Aadhaar'), 'Must align with scheme requirements');
        });

        // ─────────────────────────────────────────────────────────────────────
        // 4. Security & Privacy User Isolation (Part 8 Requirements)
        // ─────────────────────────────────────────────────────────────────────
        test('Security: User B cannot retrieve User A uploaded documents or income facts', async () => {
            // User B queries income
            const res = await chatService.chat(testUserBId, 'What is my annual family income according to my document?', [], 'conv-b');

            // Must NOT return User A's 1,80,000 income
            assert.ok(!res.reply.includes('1,80,000'), 'Must never leak User A income to User B');
            assert.ok(res.reply.includes('None of your uploaded documents establish') || res.reply.includes('No verified income'), 'Must return clean missing notice');
        });
    });
});
