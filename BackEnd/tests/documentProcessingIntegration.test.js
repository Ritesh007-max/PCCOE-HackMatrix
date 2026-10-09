const { test, describe } = require('node:test');
const assert = require('node:assert');

const documentServices = require('../src/services/documentServices');

describe('Document Processing Backend ↔ Intelligence Integration Tests', () => {
    test('extractDocument rejects missing documentId or userId with 400', async () => {
        await assert.rejects(
            async () => {
                await documentServices.extractDocument({ documentId: null, userId: 'user_1' });
            },
            { status: 400 }
        );

        await assert.rejects(
            async () => {
                await documentServices.extractDocument({ documentId: 'doc_1', userId: null });
            },
            { status: 400 }
        );
    });

    test('extractDocument is NO LONGER a 501 Not Implemented stub', async () => {
        // Even when document is not found, it must NOT return 501 (which was the old stub)
        const nonExistentDocId = '00000000-0000-0000-0000-000000000001';
        const randomUserId = '00000000-0000-0000-0000-000000000002';

        await assert.rejects(
            async () => {
                await documentServices.extractDocument({ documentId: nonExistentDocId, userId: randomUserId });
            },
            (err) => {
                assert.notStrictEqual(err.status, 501, 'Must NOT return 501 Not Implemented stub');
                assert.strictEqual(err.status, 404, 'Must return 404 Document not found');
                return true;
            }
        );
    });
});
