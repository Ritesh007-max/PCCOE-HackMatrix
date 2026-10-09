const { test, describe, before } = require('node:test');
const assert = require('node:assert/strict');
const request = require('http');

// Helper to make local HTTP requests to backend
const apiRequest = ({ method, path, headers = {}, body = null }) => {
  return new Promise((resolve, reject) => {
    const payload = body ? JSON.stringify(body) : null;
    const req = request.request(
      {
        hostname: '127.0.0.1',
        port: 5000,
        path,
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}),
          ...headers,
        },
      },
      (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          let json = null;
          try {
            json = JSON.parse(data);
          } catch (_) {
            json = data;
          }
          resolve({ status: res.statusCode, headers: res.headers, body: json });
        });
      }
    );
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
};

describe('Reviewer Role & Government Application Review Workflow', () => {
  let reviewerToken = null;
  let citizenToken = null;
  let reviewerUser = null;
  let citizenUser = null;
  let testApplicationId = null;

  before(async () => {
    // 1. Authenticate Reviewer Account
    const reviewerLoginRes = await apiRequest({
      method: 'POST',
      path: '/api/users/login',
      body: {
        email: 'reviewer@fin.gov.in',
        password: 'Reviewer@123',
        loginMode: 'reviewer',
      },
    });

    if (reviewerLoginRes.status === 200 && reviewerLoginRes.body.access_token) {
      reviewerToken = reviewerLoginRes.body.access_token;
      reviewerUser = reviewerLoginRes.body.user;
    }

    // 2. Authenticate Citizen Account
    const citizenLoginRes = await apiRequest({
      method: 'POST',
      path: '/api/users/login',
      body: {
        email: 'testcitizen@example.com',
        password: 'Citizen@123',
        loginMode: 'citizen',
      },
    });

    if (citizenLoginRes.status === 200 && citizenLoginRes.body.access_token) {
      citizenToken = citizenLoginRes.body.access_token;
      citizenUser = citizenLoginRes.body.user;
    }
  });

  test('1. Reviewer login succeeds with server-verified role reviewer', () => {
    assert.ok(reviewerToken, 'Reviewer access token should be present');
    assert.strictEqual(reviewerUser?.role, 'reviewer', 'Persisted role must be reviewer');
  });

  test('2. Citizen attempting Reviewer mode login is rejected with HTTP 403 Forbidden', async () => {
    const res = await apiRequest({
      method: 'POST',
      path: '/api/users/login',
      body: {
        email: 'testcitizen@example.com',
        password: 'Citizen@123',
        loginMode: 'reviewer', // Normal user attempting reviewer login mode
      },
    });

    assert.strictEqual(res.status, 403, 'Must return 403 Forbidden');
    assert.strictEqual(res.body.success, false);
    assert.match(res.body.message, /Access denied/i);
  });

  test('3. Unauthorized citizen calling reviewer-only route receives HTTP 403', async () => {
    if (!citizenToken) return;
    const res = await apiRequest({
      method: 'GET',
      path: '/api/reviewer/dashboard',
      headers: {
        Authorization: `Bearer ${citizenToken}`,
      },
    });

    assert.strictEqual(res.status, 403, 'Citizen token must receive 403 on reviewer endpoint');
    assert.strictEqual(res.body.success, false);
  });

  test('4. Authorized reviewer can access dynamic dashboard metrics', async () => {
    if (!reviewerToken) return;
    const res = await apiRequest({
      method: 'GET',
      path: '/api/reviewer/dashboard',
      headers: {
        Authorization: `Bearer ${reviewerToken}`,
      },
    });

    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.body.success, true);
    assert.ok(typeof res.body.data.pending_reviews === 'number');
    assert.ok(typeof res.body.data.reviewed_today === 'number');
    assert.ok(typeof res.body.data.approved === 'number');
    assert.ok(typeof res.body.data.rejected === 'number');
    assert.ok(typeof res.body.data.action_required === 'number');
  });

  test('5. Authorized reviewer can access application review queue', async () => {
    if (!reviewerToken) return;
    const res = await apiRequest({
      method: 'GET',
      path: '/api/reviewer/applications?status=all',
      headers: {
        Authorization: `Bearer ${reviewerToken}`,
      },
    });

    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.body.success, true);
    assert.ok(Array.isArray(res.body.data));

    if (res.body.data.length > 0) {
      testApplicationId = res.body.data[0].id;
    }
  });

  test('6. Reviewer can inspect application details, applicant facts, and documents', async () => {
    if (!reviewerToken || !testApplicationId) return;
    const res = await apiRequest({
      method: 'GET',
      path: `/api/reviewer/applications/${testApplicationId}`,
      headers: {
        Authorization: `Bearer ${reviewerToken}`,
      },
    });

    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.body.success, true);
    assert.ok(res.body.data.application, 'Application record must be returned');
    assert.ok(res.body.data.applicant, 'Applicant facts must be returned');
    assert.ok(Array.isArray(res.body.data.documents), 'Documents array must be present');
    assert.ok(Array.isArray(res.body.data.reviewHistory), 'Review history timeline must be present');
  });

  test('7. Mandatory remarks are enforced: Rejecting without remark returns HTTP 400', async () => {
    if (!reviewerToken || !testApplicationId) return;
    const res = await apiRequest({
      method: 'POST',
      path: `/api/reviewer/applications/${testApplicationId}/decision`,
      headers: {
        Authorization: `Bearer ${reviewerToken}`,
      },
      body: {
        decision: 'reject',
        remark: '   ', // Empty remark
      },
    });

    assert.strictEqual(res.status, 400, 'Empty remark on reject must fail with 400');
    assert.match(res.body.message, /mandatory/i);
  });

  test('8. Mandatory remarks are enforced: Requesting changes without remark returns HTTP 400', async () => {
    if (!reviewerToken || !testApplicationId) return;
    const res = await apiRequest({
      method: 'POST',
      path: `/api/reviewer/applications/${testApplicationId}/decision`,
      headers: {
        Authorization: `Bearer ${reviewerToken}`,
      },
      body: {
        decision: 'request_changes',
        remark: '', // Empty remark
      },
    });

    assert.strictEqual(res.status, 400, 'Empty remark on request_changes must fail with 400');
    assert.match(res.body.message, /mandatory/i);
  });

  test('9. Reviewer can submit Request Changes with non-empty remark', async () => {
    if (!reviewerToken || !testApplicationId) return;
    const testRemark = 'Please upload a clearer scanned copy of your income certificate (form 16).';
    const res = await apiRequest({
      method: 'POST',
      path: `/api/reviewer/applications/${testApplicationId}/decision`,
      headers: {
        Authorization: `Bearer ${reviewerToken}`,
      },
      body: {
        decision: 'request_changes',
        remark: testRemark,
      },
    });

    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.body.success, true);
    assert.strictEqual(res.body.application.status, 'action_required');
    assert.strictEqual(res.body.review.decision, 'request_changes');
    assert.strictEqual(res.body.review.remark, testRemark);
    assert.strictEqual(res.body.review.reviewerId, reviewerUser.id);
  });

  test('10. Reviewer can submit Approval decision', async () => {
    if (!reviewerToken || !testApplicationId) return;
    const approvalRemark = 'All statutory criteria verified against canonical rules.';
    const res = await apiRequest({
      method: 'POST',
      path: `/api/reviewer/applications/${testApplicationId}/decision`,
      headers: {
        Authorization: `Bearer ${reviewerToken}`,
      },
      body: {
        decision: 'approve',
        remark: approvalRemark,
      },
    });

    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.body.success, true);
    assert.strictEqual(res.body.application.status, 'approved');
    assert.strictEqual(res.body.review.decision, 'approve');
  });

  test('11. Auditable review timeline preserves historical decisions', async () => {
    if (!reviewerToken || !testApplicationId) return;
    const res = await apiRequest({
      method: 'GET',
      path: `/api/reviewer/applications/${testApplicationId}`,
      headers: {
        Authorization: `Bearer ${reviewerToken}`,
      },
    });

    assert.strictEqual(res.status, 200);
    const history = res.body.data.reviewHistory;
    assert.ok(history.length >= 2, 'History must contain past review decisions');
    assert.ok(history.some((h) => h.decision === 'request_changes'), 'Must contain request_changes record');
    assert.ok(history.some((h) => h.decision === 'approve'), 'Must contain approve record');
  });

  test('12. Notification service creates persistent tenant-isolated notification for applicant', async () => {
    const notificationService = require('../src/services/notificationService');
    const dummyApplicantId = '99999999-0000-0000-0000-000000000001';
    const notif = await notificationService.createNotification({
      recipientUserId: dummyApplicantId,
      applicationId: testApplicationId || '11111111-0000-0000-0000-000000000001',
      type: 'approval',
      title: 'Application Approved',
      message: 'Your application has been approved by the nodal review officer.',
    });

    assert.ok(notif.id);
    assert.strictEqual(notif.recipientUserId, dummyApplicantId);

    // Fetch notifications for applicant
    const result = await notificationService.getUserNotifications(dummyApplicantId);
    assert.ok(result.notifications.length >= 1);
    assert.strictEqual(result.notifications[0].title, 'Application Approved');
    assert.strictEqual(result.notifications[0].read, false);

    // Tenant isolation: querying another user returns nothing
    const otherResult = await notificationService.getUserNotifications('88888888-0000-0000-0000-000000000002');
    assert.strictEqual(otherResult.notifications.length, 0);

    // Mark as read
    await notificationService.markAsRead(notif.id, dummyApplicantId);
    const updated = await notificationService.getUserNotifications(dummyApplicantId);
    assert.strictEqual(updated.notifications[0].read, true);
  });
});
