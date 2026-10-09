const assert = require('assert');

const API_BASE = 'http://127.0.0.1:5000';
const FRONTEND_BASE = 'http://127.0.0.1:5173';

async function req(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const res = await fetch(url, { ...options, headers: headers });
  const text = await res.text();
  let body;
  try { body = JSON.parse(text); } catch { body = text; }
  return { status: res.status, headers: res.headers, body };
}

async function runEndToEndVerification() {
  console.log('=== FIN REVIEWER ROLE & APPLICATION WORKFLOW VERIFICATION ===\n');

  // 1. Verify Frontend Dev Server is accessible
  console.log('1. Checking Frontend Dev Server...');
  const feRes = await fetch(FRONTEND_BASE);
  assert.strictEqual(feRes.status, 200, 'Frontend dev server must be accessible');
  const feHtml = await feRes.text();
  assert.ok(feHtml.includes('<title>') || feHtml.includes('FIN'), 'Frontend index HTML returned');
  console.log('   ✓ Frontend is running at http://localhost:5173\n');

  // 2. Normal User Login
  console.log('2. Testing Citizen / User Login...');
  const citizenLogin = await req('/api/users/login', {
    method: 'POST',
    body: JSON.stringify({
      email: 'testcitizen@example.com',
      password: 'Citizen@123',
      loginMode: 'citizen'
    })
  });
  assert.strictEqual(citizenLogin.status, 200);
  assert.strictEqual(citizenLogin.body.user.role, 'user');
  const citizenToken = citizenLogin.body.access_token;
  const citizenId = citizenLogin.body.user.id;
  console.log(`   ✓ Citizen authenticated (ID: ${citizenId}, Role: ${citizenLogin.body.user.role})\n`);

  // 3. Normal User attempting Reviewer Mode Login (Must be Rejected 403)
  console.log('3. Testing Citizen Attempting Reviewer Mode Login (Role Escalation Prevention)...');
  const spoofAttempt = await req('/api/users/login', {
    method: 'POST',
    body: JSON.stringify({
      email: 'testcitizen@example.com',
      password: 'Citizen@123',
      loginMode: 'reviewer'
    })
  });
  assert.strictEqual(spoofAttempt.status, 403, 'Citizen in reviewer mode must receive 403 Forbidden');
  assert.match(spoofAttempt.body.message, /reviewer/i);
  console.log('   ✓ Citizen spoofing reviewer mode correctly rejected with HTTP 403 Forbidden\n');

  // 4. Unauthorized Citizen calling Reviewer APIs (Must be Blocked 403)
  console.log('4. Testing Citizen calling Reviewer APIs directly...');
  const unauthorizedQueue = await req('/api/reviewer/applications', {
    headers: { Authorization: `Bearer ${citizenToken}` }
  });
  assert.strictEqual(unauthorizedQueue.status, 403);
  console.log('   ✓ Backend middleware blocks citizen from /api/reviewer with HTTP 403 Forbidden\n');

  // 5. Reviewer Login
  console.log('5. Testing Official Reviewer Login...');
  const reviewerLogin = await req('/api/users/login', {
    method: 'POST',
    body: JSON.stringify({
      email: 'reviewer@fin.gov.in',
      password: 'Reviewer@123',
      loginMode: 'reviewer'
    })
  });
  assert.strictEqual(reviewerLogin.status, 200);
  assert.strictEqual(reviewerLogin.body.user.role, 'reviewer');
  const reviewerToken = reviewerLogin.body.access_token;
  const reviewerId = reviewerLogin.body.user.id;
  console.log(`   ✓ Reviewer authenticated (ID: ${reviewerId}, Role: ${reviewerLogin.body.user.role})\n`);

  // 6. Reviewer Dashboard Metrics (Live Backend Data)
  console.log('6. Testing Reviewer Dashboard Metrics...');
  const dashboardRes = await req('/api/reviewer/dashboard', {
    headers: { Authorization: `Bearer ${reviewerToken}` }
  });
  assert.strictEqual(dashboardRes.status, 200);
  const stats = dashboardRes.body.data;
  assert.ok(typeof stats.pending_reviews === 'number');
  assert.ok(typeof stats.reviewed_today === 'number');
  assert.ok(typeof stats.approved === 'number');
  assert.ok(typeof stats.rejected === 'number');
  assert.ok(typeof stats.action_required === 'number');
  console.log(`   ✓ Live metrics: Pending: ${stats.pending_reviews}, Approved: ${stats.approved}, Rejected: ${stats.rejected}, Action Required: ${stats.action_required}\n`);

  // 7. Review Applications Queue
  console.log('7. Testing Review Applications Queue...');
  const queueRes = await req('/api/reviewer/applications?status=all', {
    headers: { Authorization: `Bearer ${reviewerToken}` }
  });
  assert.strictEqual(queueRes.status, 200);
  const apps = queueRes.body.data;
  assert.ok(Array.isArray(apps) && apps.length > 0);
  const testApp = apps[0];
  console.log(`   ✓ Queue returned ${apps.length} applications. Target application: ${testApp.id} (${testApp.scheme_name || 'Scheme'})\n`);

  // 8. Application Details Inspection
  console.log(`8. Inspecting Application Details for ${testApp.id}...`);
  const detailsRes = await req(`/api/reviewer/applications/${testApp.id}`, {
    headers: { Authorization: `Bearer ${reviewerToken}` }
  });
  assert.strictEqual(detailsRes.status, 200);
  const details = detailsRes.body.data;
  assert.ok(details.applicant, 'Applicant profile present');
  assert.ok(Array.isArray(details.documents), 'Documents list present');
  console.log(`   ✓ Applicant: ${details.applicant.fullName || 'Citizen'}, Documents attached: ${details.documents.length}\n`);

  // 9. Mandatory Remark Validation for 'reject'
  console.log('9. Testing Mandatory Remark Validation on Reject...');
  const rejectNoRemark = await req(`/api/reviewer/applications/${testApp.id}/decision`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${reviewerToken}` },
    body: JSON.stringify({ decision: 'reject', remark: '' })
  });
  assert.strictEqual(rejectNoRemark.status, 400);
  assert.match(rejectNoRemark.body.message, /mandatory/i);
  console.log('   ✓ Reject with empty remark blocked with HTTP 400 Bad Request\n');

  // 10. Mandatory Remark Validation for 'request_changes'
  console.log('10. Testing Mandatory Remark Validation on Request Changes...');
  const changeNoRemark = await req(`/api/reviewer/applications/${testApp.id}/decision`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${reviewerToken}` },
    body: JSON.stringify({ decision: 'request_changes', remark: '   ' })
  });
  assert.strictEqual(changeNoRemark.status, 400);
  assert.match(changeNoRemark.body.message, /mandatory/i);
  console.log('   ✓ Request Changes with empty remark blocked with HTTP 400 Bad Request\n');

  // 11. Submitting Request Changes Decision with Mandatory Remark
  console.log('11. Submitting Request Changes Decision with Mandatory Remark...');
  const changeRemarkText = 'Please upload a clearer scanned copy of your income certificate (form 16).';
  const changeRes = await req(`/api/reviewer/applications/${testApp.id}/decision`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${reviewerToken}` },
    body: JSON.stringify({ decision: 'request_changes', remark: changeRemarkText })
  });
  assert.strictEqual(changeRes.status, 200);
  assert.strictEqual(changeRes.body.application.status, 'action_required');
  assert.strictEqual(changeRes.body.review.decision, 'request_changes');
  assert.strictEqual(changeRes.body.review.remark, changeRemarkText);
  // Ensure remark is clean and not contaminated with ACTION_REQUIRED: prefix
  assert.ok(!changeRes.body.application.remarks?.startsWith('ACTION_REQUIRED:'));
  console.log(`   ✓ Status updated to ${changeRes.body.application.status} with clean remark preserved\n`);

  // 12. Submitting Reject Decision with Mandatory Remark
  console.log('12. Submitting Reject Decision with Mandatory Remark...');
  const rejectRemarkText = 'Application does not meet the statutory eligibility requirements under Section 4.';
  const rejectRes = await req(`/api/reviewer/applications/${testApp.id}/decision`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${reviewerToken}` },
    body: JSON.stringify({ decision: 'reject', remark: rejectRemarkText })
  });
  assert.strictEqual(rejectRes.status, 200);
  assert.strictEqual(rejectRes.body.application.status, 'rejected');
  assert.strictEqual(rejectRes.body.review.decision, 'reject');
  assert.strictEqual(rejectRes.body.review.remark, rejectRemarkText);
  console.log(`   ✓ Reject decision succeeded: status updated to ${rejectRes.body.application.status} with mandatory remark\n`);

  // 13. Submitting Approval Decision
  console.log('13. Submitting Approval Decision...');
  const approvalRemark = 'All statutory documents and eligibility requirements validated.';
  const approveRes = await req(`/api/reviewer/applications/${testApp.id}/decision`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${reviewerToken}` },
    body: JSON.stringify({ decision: 'approve', remark: approvalRemark })
  });
  assert.strictEqual(approveRes.status, 200);
  assert.strictEqual(approveRes.body.application.status, 'approved');
  console.log(`   ✓ Status updated to ${approveRes.body.application.status}\n`);

  // 14. Auditable History Timeline Preserved
  console.log('14. Verifying Auditable Review Timeline...');
  const historyRes = await req(`/api/reviewer/applications/${testApp.id}`, {
    headers: { Authorization: `Bearer ${reviewerToken}` }
  });
  const history = historyRes.body.data.reviewHistory;
  assert.ok(history.length >= 3, 'History must contain all three review decisions (request_changes, reject, approve)');
  assert.ok(history.some(h => h.decision === 'reject'), 'Timeline must preserve reject decision');
  assert.ok(history.some(h => h.decision === 'request_changes'), 'Timeline must preserve request_changes decision');
  assert.ok(history.some(h => h.decision === 'approve'), 'Timeline must preserve approve decision');
  console.log(`   ✓ Preserved ${history.length} auditable historical review records with all 3 decision types\n`);

  // 14. Notifications Created for Applicant & Tenant Isolation Verified
  console.log('14. Verifying Persistent Tenant-Isolated Notifications for Applicant...');
  const notificationService = require('../src/services/notificationService');
  
  // Verify notification was created for applicant
  const notifResult = await notificationService.getUserNotifications(details.applicant.id);
  const applicantNotifs = notifResult.notifications || [];
  assert.ok(Array.isArray(applicantNotifs) && applicantNotifs.length > 0, 'Notification must be stored for applicant');
  const latestNotif = applicantNotifs[0];
  console.log(`   ✓ Applicant notification created: "${latestNotif.title}" — "${latestNotif.message}"`);
  console.log(`   ✓ Associated Application ID: ${latestNotif.applicationId}, Link: ${latestNotif.link}`);

  // Verify Tenant Isolation: citizen does not receive other users' notifications
  if (details.applicant.id !== citizenId) {
    const unauthNotifs = await req('/api/notifications', {
      headers: { Authorization: `Bearer ${citizenToken}` }
    });
    assert.strictEqual(unauthNotifs.status, 200);
    const otherNotifs = unauthNotifs.body.data || [];
    assert.ok(
      !otherNotifs.some(n => n.id === latestNotif.id),
      'Tenant isolation: Other citizens must never receive applicant notifications'
    );
    console.log('   ✓ Verified strict tenant isolation: Other users cannot see applicant notifications');
  }

  // 15. Notification Read/Unread State for Citizen
  console.log('\n15. Testing Notification Delivery & Read/Unread State...');
  const testCitizenNotif = await notificationService.createNotification({
    recipientUserId: citizenId,
    applicationId: testApp.id,
    type: 'decision',
    title: 'Application Decision Recorded',
    message: 'Your application has been processed by the nodal review officer.'
  });

  const citizenNotifsRes = await req('/api/notifications', {
    headers: { Authorization: `Bearer ${citizenToken}` }
  });
  assert.strictEqual(citizenNotifsRes.status, 200);
  const citizenList = citizenNotifsRes.body.data || [];
  assert.ok(citizenList.some(n => n.id === testCitizenNotif.id));
  console.log(`   ✓ Notification delivered to citizen (Unread Count: ${citizenNotifsRes.body.unreadCount})`);

  const markRead = await req(`/api/notifications/${testCitizenNotif.id}/read`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${citizenToken}` }
  });
  assert.strictEqual(markRead.status, 200);
  assert.strictEqual(markRead.body.data.read, true);
  console.log('   ✓ Notification successfully marked as read');

  console.log('===============================================================');
  console.log('ALL WORKFLOW VERIFICATIONS PASSED WITH 100% SUCCESS!');
  console.log('===============================================================\n');
}

runEndToEndVerification().catch((err) => {
  console.error('VERIFICATION ERROR:', err);
  process.exit(1);
});
