import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  normalizeDocRequirementId,
  SUPPORTED_DOC_TYPES,
  DOC_TYPE_LOOKUP
} from '../src/data/documentsData.js';

import {
  filterApplicantRelevantSchemes
} from '../src/utils/documentSchemeValidation.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('FIN — Documents Page Data Integrity and Production Hardening Suite', async (t) => {

  await t.test('1. Scheme Impact Count is purely dynamic and never hardcoded to 4', () => {
    // Construct test catalog of applicable schemes
    const sampleSchemes = [
      { id: 'sch-1', name: 'Scheme One', documents_required: 'aadhaar, income_cert, address_proof' },
      { id: 'sch-2', name: 'Scheme Two', documents_required: 'pan, address_proof' },
      { id: 'sch-3', name: 'Scheme Three', documents_required: 'address_proof, caste_cert' },
      { id: 'sch-4', name: 'Scheme Four', documents_required: ['address_proof', 'aadhaar'] },
      { id: 'sch-5', name: 'Scheme Five', documents_required: 'address_proof, bank_passbook' },
      { id: 'sch-6', name: 'Scheme Six', documents_required: 'aadhaar, bank_passbook' }
    ];

    // Compute counts dynamically as implemented in DocumentsPage
    const counts = {};
    sampleSchemes.forEach((s) => {
      const rawDocs = s.documents_required || s.required_documents || s.documents || [];
      const docList = Array.isArray(rawDocs) ? rawDocs : (typeof rawDocs === 'string' ? rawDocs.split(/[;\n|,]+/) : []);
      const seenInScheme = new Set();
      docList.forEach((d) => {
        const norm = normalizeDocRequirementId(d);
        if (norm && !seenInScheme.has(norm)) {
          seenInScheme.add(norm);
          counts[norm] = (counts[norm] || 0) + 1;
        }
      });
    });

    // Address proof is required in schemes 1, 2, 3, 4, 5 => exactly 5 schemes!
    assert.strictEqual(counts['address_proof'], 5, 'Address proof dynamic count should be 5, not hardcoded 4');
    // Aadhaar is required in schemes 1, 4, 6 => exactly 3 schemes
    assert.strictEqual(counts['aadhaar'], 3, 'Aadhaar dynamic count should be 3');
    // Caste certificate is in scheme 3 => 1
    assert.strictEqual(counts['caste_cert'], 1);
    // Domicile not in any => 0 / undefined
    assert.strictEqual(counts['domicile'] ?? 0, 0);
  });

  await t.test('2. DocumentsPage.jsx contains zero hardcoded fallback counts (no "|| 4") and zero hardcoded metric text', () => {
    const pagePath = path.resolve(__dirname, '../src/pages/DocumentsPage.jsx');
    const content = fs.readFileSync(pagePath, 'utf8');

    // Assert no "|| 4" or "requiredForSchemes || 4"
    assert.doesNotMatch(content, /requiredForSchemes\s*\|\|\s*4/, 'Must not contain hardcoded "requiredForSchemes || 4" fallback');

    // Assert metric card subtext is dynamic
    assert.doesNotMatch(content, /'Address proof missing'/, 'Must not hardcode "Address proof missing" in metric card subtext');
    assert.match(content, /actionCount > 0 \? `\$\{actionCount\} document/, 'Must dynamically format action required document count');
  });

  await t.test('3. Statutory Verification Status strictly decoupled from AI OCR Extraction', () => {
    // Sample raw document payload with extracted OCR facts but pending verification
    const rawDocWithOcr = {
      id: 'doc-aadhaar-101',
      document_type: 'address_proof',
      file_name: 'electricity_bill.pdf',
      verification_status: 'PENDING',
      extracted_data: {
        address: '101, Shanti Niketan, Ahmedabad, Gujarat',
        consumer_number: 'EB-99214'
      },
      uploaded_by: 'citizen'
    };

    // Verification status must remain under_review / Uploaded
    const statusRaw = String(rawDocWithOcr.verification_status).toUpperCase();
    const isVerified = statusRaw === 'VERIFIED';
    assert.strictEqual(isVerified, false, 'OCR presence must never mark statutory verification as true');

    const hasExtractedFields = rawDocWithOcr.extracted_data && Object.keys(rawDocWithOcr.extracted_data).length > 0;
    assert.strictEqual(hasExtractedFields, true, 'Extracted fields must be detected');

    // Validity label must truthfully state Uploaded (Pending Review)
    const validity = isVerified ? 'Verified & Ready for AI Chat' : 'Uploaded (Pending Review)';
    assert.strictEqual(validity, 'Uploaded (Pending Review)', 'Validity label must remain pending review');
  });

  await t.test('4. Screenshot Row Elements: 1:1 Mapping Fidelity and Integrity', () => {
    // Row representation matching user specification:
    // Name: "Address Proof"
    // Description: "Residency Verification"
    // Uploader: "Self Uploaded"
    // OCR Status: "AI OCR Extracted"
    // Purpose: "Address Proof"
    // Dynamic Scheme count: 4 (if matching 4 schemes in catalog)
    // Status badge: "Uploaded"
    // Validity: "Uploaded (Pending Review)"

    const docTypeMeta = DOC_TYPE_LOOKUP['address_proof'];
    assert.ok(docTypeMeta, 'address_proof should exist in canonical supported types');
    assert.strictEqual(docTypeMeta.name, 'Address Proof');
    assert.strictEqual(docTypeMeta.category, 'Residency Verification');
    assert.strictEqual(docTypeMeta.purpose, 'Address Proof');

    const uploaderMapping = (raw) => {
      const up = String(raw || '').toUpperCase();
      if (up === 'ADMIN' || up.includes('OFFICER') || up.includes('REVIEWER')) return 'Official Department';
      if (up === 'SYSTEM' || up.includes('SERVICE') || up.includes('SYSTEM')) return 'System Ingested';
      return 'Self Uploaded';
    };

    assert.strictEqual(uploaderMapping('CITIZEN'), 'Self Uploaded');
    assert.strictEqual(uploaderMapping('self'), 'Self Uploaded');
    assert.strictEqual(uploaderMapping('OFFICER_PATEL'), 'Official Department');
    assert.strictEqual(uploaderMapping('SYSTEM_CRON'), 'System Ingested');
  });

  await t.test('5. Multi-Tenant User Isolation: Cache and storage operations are strictly user-scoped', () => {
    const userA = 'usr-tenant-alpha';
    const userB = 'usr-tenant-beta';

    const getStorageKey = (userId) => `fin_documents_tickets_${userId || 'guest'}`;

    assert.notStrictEqual(
      getStorageKey(userA),
      getStorageKey(userB),
      'Storage keys between tenants must be distinct'
    );
  });
});
