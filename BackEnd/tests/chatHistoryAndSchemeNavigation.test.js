const { test, describe, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const chatHistoryService = require('../src/services/chatHistoryService');
const { chat, computeLocalFallback } = require('../src/services/chatService');
const { getSchemeById } = require('../src/services/schemeService');

describe('FIN AI — Scheme Suggestion & Authenticated Chat History Suite', () => {

    const userA = 'test-user-alpha-1111';
    const userB = 'test-user-beta-2222';

    beforeEach(() => {
        chatHistoryService.clearAllConversations(userA);
        chatHistoryService.clearAllConversations(userB);
    });

    test('1. Scheme suggestion → correct canonical scheme ID and slug', async () => {
        // Query fallback for schemes for students
        const studentResult = computeLocalFallback('schemes for students in Gujarat', {}, [], []);
        assert.ok(studentResult.schemes && studentResult.schemes.length > 0, 'Expected scheme suggestions');

        // Verify each scheme suggestion has exact canonical slug/id
        for (const s of studentResult.schemes) {
            assert.ok(s.id, 'Scheme must have id');
            assert.ok(s.slug, 'Scheme must have canonical slug');
            assert.strictEqual(s.id, s.slug, 'Scheme id must equal canonical slug');
            assert.ok(!s.slug.includes(' '), 'Slug must not contain whitespace');
            assert.ok(!s.slug.startsWith('http'), 'Slug must be identifier, not full URL');
        }

        // Verify specific known student scheme has exact canonical ID
        const vidyalaxmi = studentResult.schemes.find(s => s.id === 'pm-vidyalaxmi');
        assert.ok(vidyalaxmi, 'PM Vidyalaxmi scheme must be present');
        assert.strictEqual(vidyalaxmi.slug, 'pm-vidyalaxmi');
        assert.strictEqual(vidyalaxmi.schemeId, 'pm-vidyalaxmi');

        // Verify PMEGP query returns exact canonical ID 'pmegp'
        const pmegpResult = computeLocalFallback('Tell me about PMEGP subsidies', {}, [], []);
        assert.ok(pmegpResult.schemes && pmegpResult.schemes.length > 0);
        const pmegpScheme = pmegpResult.schemes.find(s => s.id === 'pmegp');
        assert.ok(pmegpScheme, 'PMEGP scheme suggestion must be present');
        assert.strictEqual(pmegpScheme.slug, 'pmegp');
        assert.strictEqual(pmegpScheme.schemeId, 'pmegp');
    });

    test('2. Disambiguates similar-named schemes using canonical ID without text-match conflation', async () => {
        // Test MUDRA Shishu vs MUDRA Kishore
        const shishu = await getSchemeById('mudra-shishu');
        const kishore = await getSchemeById('mudra-kishore');

        assert.ok(shishu && shishu.scheme, 'MUDRA Shishu must resolve');
        assert.ok(kishore && kishore.scheme, 'MUDRA Kishore must resolve');

        assert.strictEqual(shishu.scheme.id, 'mudra-shishu');
        assert.strictEqual(kishore.scheme.id, 'mudra-kishore');
        assert.notStrictEqual(shishu.scheme.id, kishore.scheme.id);
        assert.notStrictEqual(shishu.scheme.name, kishore.scheme.name);
        assert.match(shishu.scheme.name, /Shishu/i);
        assert.match(kishore.scheme.name, /Kishore/i);
    });

    test('3. Empty history state for new authenticated user', async () => {
        const historyA = await chatHistoryService.listConversations(userA);
        assert.ok(Array.isArray(historyA), 'History must be an array');
        assert.strictEqual(historyA.length, 0, 'New user history must be empty');
    });

    test('4. Save and reload chat history for authenticated user', async () => {
        const turn1 = await chatHistoryService.recordChatTurn(
            userA,
            null,
            { text: 'What is PMEGP margin subsidy?' },
            {
                text: 'PMEGP provides up to 35% margin money subsidy.',
                schemes: [{ id: 'pmegp', slug: 'pmegp', title: 'PMEGP' }]
            }
        );

        assert.ok(turn1.conversationId, 'Must return conversationId');
        assert.ok(turn1.title.includes('PMEGP'), 'Title must be derived from first question');

        // List history
        const history = await chatHistoryService.listConversations(userA);
        assert.strictEqual(history.length, 1);
        assert.strictEqual(history[0].id, turn1.conversationId);
        assert.strictEqual(history[0].messageCount, 2);

        // Reopen exact conversation
        const reopened = await chatHistoryService.getConversation(userA, turn1.conversationId);
        assert.ok(reopened, 'Conversation must be retrieved');
        assert.strictEqual(reopened.id, turn1.conversationId);
        assert.strictEqual(reopened.messages.length, 2);
        assert.strictEqual(reopened.messages[0].sender, 'user');
        assert.strictEqual(reopened.messages[1].sender, 'assistant');
        assert.strictEqual(reopened.messages[1].schemes[0].slug, 'pmegp');
    });

    test('5. Strict authenticated history isolation between tenants (User A vs User B)', async () => {
        // User A creates conversation
        const turnA = await chatHistoryService.recordChatTurn(
            userA,
            null,
            'Confidential subsidy query for User A',
            'Answer for User A'
        );

        // User B creates conversation
        const turnB = await chatHistoryService.recordChatTurn(
            userB,
            null,
            'Farmer loan query for User B',
            'Answer for User B'
        );

        // User A should only see User A's conversation
        const historyA = await chatHistoryService.listConversations(userA);
        assert.strictEqual(historyA.length, 1);
        assert.strictEqual(historyA[0].id, turnA.conversationId);
        assert.ok(historyA[0].title.includes('User A'));

        // User B should only see User B's conversation
        const historyB = await chatHistoryService.listConversations(userB);
        assert.strictEqual(historyB.length, 1);
        assert.strictEqual(historyB[0].id, turnB.conversationId);
        assert.ok(historyB[0].title.includes('User B'));

        // User A CANNOT open User B's conversation
        const crossAccessA = await chatHistoryService.getConversation(userA, turnB.conversationId);
        assert.strictEqual(crossAccessA, null, 'User A must not be able to reopen User B conversation');

        // User B CANNOT open User A's conversation
        const crossAccessB = await chatHistoryService.getConversation(userB, turnA.conversationId);
        assert.strictEqual(crossAccessB, null, 'User B must not be able to reopen User A conversation');

        // User B CANNOT delete User A's conversation
        const deleteCross = await chatHistoryService.deleteConversation(userB, turnA.conversationId);
        assert.strictEqual(deleteCross, false, 'User B must not delete User A conversation');
    });

    test('6. Multiple conversations ordering and management', async () => {
        // Create conversation 1
        const conv1 = await chatHistoryService.recordChatTurn(
            userA,
            'conv-multi-1',
            'First conversation question',
            'First answer'
        );

        // Create conversation 2
        const conv2 = await chatHistoryService.recordChatTurn(
            userA,
            'conv-multi-2',
            'Second conversation question',
            'Second answer'
        );

        // Add follow-up to conversation 1 to make it the most recently updated
        await chatHistoryService.recordChatTurn(
            userA,
            'conv-multi-1',
            'Follow-up in first conversation',
            'Follow-up answer'
        );

        const history = await chatHistoryService.listConversations(userA);
        assert.strictEqual(history.length, 2, 'Must contain 2 distinct conversations');

        // Most recently updated conversation must be first
        assert.strictEqual(history[0].id, 'conv-multi-1');
        assert.strictEqual(history[0].messageCount, 4);
        assert.strictEqual(history[1].id, 'conv-multi-2');
        assert.strictEqual(history[1].messageCount, 2);

        // Reopen conversation 2
        const reopened2 = await chatHistoryService.getConversation(userA, 'conv-multi-2');
        assert.strictEqual(reopened2.messages.length, 2);
        assert.strictEqual(reopened2.messages[0].text, 'Second conversation question');

        // Delete conversation 2
        const deleted = await chatHistoryService.deleteConversation(userA, 'conv-multi-2');
        assert.strictEqual(deleted, true);

        const historyAfterDelete = await chatHistoryService.listConversations(userA);
        assert.strictEqual(historyAfterDelete.length, 1);
        assert.strictEqual(historyAfterDelete[0].id, 'conv-multi-1');
    });
});
