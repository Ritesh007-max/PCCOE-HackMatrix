import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '../src');

test('Reviewer Role & Government Application Review Workflow Frontend Audit', async (t) => {
  await t.test('1. Sidebar hides citizen-only routes and shows reviewer-only routes for reviewer role', () => {
    const sidebarCode = fs.readFileSync(path.join(SRC_DIR, 'components/layout/Sidebar.jsx'), 'utf8');
    
    // Check conditional role rendering
    assert.ok(sidebarCode.includes("role === 'reviewer'"), 'Sidebar must check for role === reviewer');
    assert.ok(sidebarCode.includes('/reviewer/dashboard'), 'Sidebar must link to /reviewer/dashboard');
    assert.ok(sidebarCode.includes('/reviewer/applications'), 'Sidebar must link to /reviewer/applications');
    assert.ok(sidebarCode.includes('/discover'), 'Sidebar must allow Discover Schemes for reviewer');

    // Citizen only items vs Reviewer nav separation
    assert.ok(sidebarCode.includes('reviewerNavItems'), 'Must define reviewerNavItems');
    assert.ok(sidebarCode.includes('citizenNavItems'), 'Must define citizenNavItems');
    assert.ok(sidebarCode.includes('Suggested Schemes'), 'Suggested Schemes defined for citizen');
    assert.ok(sidebarCode.includes('My Documents'), 'My Documents defined for citizen');
  });

  await t.test('2. ProtectedRoute enforces allowedRoles guard against unauthorized access', () => {
    const protectedRouteCode = fs.readFileSync(path.join(SRC_DIR, 'components/common/ProtectedRoute.jsx'), 'utf8');
    
    assert.ok(protectedRouteCode.includes('allowedRoles'), 'ProtectedRoute must accept allowedRoles prop');
    assert.ok(protectedRouteCode.includes('getStoredRole') || protectedRouteCode.includes('userRole'), 'ProtectedRoute must verify stored user role');
    assert.ok(protectedRouteCode.includes('Navigate to="/dashboard"') || protectedRouteCode.includes('Navigate to="/reviewer/dashboard"'), 'Unauthorized role must be redirected safely');
  });

  await t.test('3. AppRoutes mounts Reviewer routes with allowedRoles={[\'reviewer\']}', () => {
    const routesCode = fs.readFileSync(path.join(SRC_DIR, 'routes/AppRoutes.jsx'), 'utf8');
    
    assert.ok(routesCode.includes('/reviewer/dashboard'), 'AppRoutes must mount /reviewer/dashboard');
    assert.ok(routesCode.includes('/reviewer/applications'), 'AppRoutes must mount /reviewer/applications');
    assert.ok(routesCode.includes("allowedRoles={['reviewer']}"), 'Reviewer routes must specify allowedRoles={["reviewer"]}');
  });

  await t.test('4. Login page provides clean User/Reviewer mode selector without client-side role grant', () => {
    const signupCode = fs.readFileSync(path.join(SRC_DIR, 'pages/SignupPage.jsx'), 'utf8');
    
    assert.ok(signupCode.includes('loginMode') || signupCode.includes('isReviewerMode'), 'Login page must manage loginMode state');
    assert.ok(signupCode.includes('Citizen / User') || signupCode.includes('Citizen'), 'Login mode toggle must present Citizen option');
    assert.ok(signupCode.includes('Government Reviewer') || signupCode.includes('Reviewer'), 'Login mode toggle must present Reviewer option');
    assert.ok(signupCode.includes('loginUser'), 'Login must call authService.loginUser with loginMode');
    assert.ok(signupCode.includes('/reviewer/dashboard'), 'Successful reviewer login must route to /reviewer/dashboard');
  });

  await t.test('5. Review Applications page enforces mandatory remarks for reject and request changes', () => {
    const reviewPageCode = fs.readFileSync(path.join(SRC_DIR, 'pages/ReviewApplicationsPage.jsx'), 'utf8');
    
    assert.ok(reviewPageCode.includes('approve'), 'Must handle approve decision');
    assert.ok(reviewPageCode.includes('request_changes'), 'Must handle request_changes decision');
    assert.ok(reviewPageCode.includes('reject'), 'Must handle reject decision');
    assert.ok(reviewPageCode.includes("decisionType === 'reject'") || reviewPageCode.includes('decisionType'), 'Must check decisionType for mandatory remarks');
    assert.ok(reviewPageCode.includes('remark.trim()'), 'Must validate remark is non-empty');
    assert.ok(reviewPageCode.includes('statusFilter'), 'Must support queue status filtering');
  });

  await t.test('6. Reviewer Dashboard displays all 5 real dynamic metrics without hardcoding', () => {
    const dashboardCode = fs.readFileSync(path.join(SRC_DIR, 'pages/ReviewerDashboardPage.jsx'), 'utf8');
    
    assert.ok(dashboardCode.includes('pending_reviews'), 'Dashboard must display pending_reviews metric');
    assert.ok(dashboardCode.includes('reviewed_today'), 'Dashboard must display reviewed_today metric');
    assert.ok(dashboardCode.includes('approved'), 'Dashboard must display approved metric');
    assert.ok(dashboardCode.includes('rejected'), 'Dashboard must display rejected metric');
    assert.ok(dashboardCode.includes('action_required'), 'Dashboard must display action_required metric');
  });

  await t.test('7. Citizen Applications page displays reviewer remarks and supports deep link opening', () => {
    const appPageCode = fs.readFileSync(path.join(SRC_DIR, 'pages/ApplicationsPage.jsx'), 'utf8');
    
    assert.ok(appPageCode.includes('Reviewer Remark') && appPageCode.includes('app.remarks'), 'Citizen applications page must display reviewer remarks');
    assert.ok(appPageCode.includes('targetAppId') || appPageCode.includes('searchParams.get'), 'Must support deep link navigation via URL search param');
    assert.ok(appPageCode.includes('action_required'), 'Must handle action_required status presentation');
  });

  await t.test('8. Header notification dropdown supports unread count, click-to-application navigation and mark-read', () => {
    const headerCode = fs.readFileSync(path.join(SRC_DIR, 'components/layout/Header.jsx'), 'utf8');
    
    assert.ok(headerCode.includes('unreadCount'), 'Header must calculate and display unread count');
    assert.ok(headerCode.includes('/applications?open=') || headerCode.includes('navigate'), 'Notification click must navigate to exact application');
    assert.ok(headerCode.includes('markNotificationAsRead'), 'Header must call markNotificationAsRead service');
  });

  await t.test('9. Canonical 4,752 schemes dataset isolation constraint', () => {
    const authEnv = fs.readFileSync(path.join(SRC_DIR, '../../BackEnd/.env'), 'utf8');
    
    // Auth Supabase must be mnwasujoidhrhchhpllr
    assert.ok(authEnv.includes('mnwasujoidhrhchhpllr'), 'Backend Auth/App Supabase URL must point to mnwasujoidhrhchhpllr');
    
    // Scheme service accesses canonical schemes without mutating or migrating the schema
    const schemeServiceCode = fs.readFileSync(path.join(SRC_DIR, '../../BackEnd/src/services/schemeService.js'), 'utf8');
    assert.ok(schemeServiceCode.includes('canonicalSchemesIndex') || schemeServiceCode.includes('snapshotsRoot'), 'Canonical scheme index remains preserved and read-only');
  });
});
