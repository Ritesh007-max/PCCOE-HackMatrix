import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import DashboardPage from '../pages/DashboardPage';
import DiscoverPage from '../pages/DiscoverPage';
import SchemeDetailsPage from '../pages/SchemeDetailsPage';
import SchemeBenefitsPage from '../pages/SchemeBenefitsPage';
import DocumentsPage from '../pages/DocumentsPage';
import ApplicationsPage from '../pages/ApplicationsPage';
import SuggestedSchemesPage from '../pages/SuggestedSchemesPage';
import ProfilePage from '../pages/ProfilePage';
import ReviewerDashboardPage from '../pages/ReviewerDashboardPage';
import ReviewApplicationsPage from '../pages/ReviewApplicationsPage';
import NotFoundPage from '../pages/NotFoundPage';

import SignupPage from '../pages/SignupPage';
import ProtectedRoute from '../components/common/ProtectedRoute';

export default function AppRoutes() {
  return (
    <Routes>
      {/* Default route redirects to /signup when starting */}
      <Route path="/" element={<Navigate to="/signup" replace />} />

      {/* Standalone Authentication Pages */}
      <Route path="/signup" element={<SignupPage initialMode="signup" />} />
      <Route path="/register" element={<SignupPage initialMode="signup" />} />
      <Route path="/login" element={<SignupPage initialMode="signin" />} />
      <Route path="/signin" element={<SignupPage initialMode="signin" />} />

      {/* Main Authenticated Layout Container */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        {/* Citizen Exclusive Pages */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute allowedRoles={['user']}>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/suggested-schemes"
          element={
            <ProtectedRoute allowedRoles={['user']}>
              <SuggestedSchemesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/documents"
          element={
            <ProtectedRoute allowedRoles={['user']}>
              <DocumentsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/applications"
          element={
            <ProtectedRoute allowedRoles={['user']}>
              <ApplicationsPage />
            </ProtectedRoute>
          }
        />

        {/* Reviewer Exclusive Pages */}
        <Route
          path="/reviewer/dashboard"
          element={
            <ProtectedRoute allowedRoles={['reviewer']}>
              <ReviewerDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reviewer/applications"
          element={
            <ProtectedRoute allowedRoles={['reviewer']}>
              <ReviewApplicationsPage />
            </ProtectedRoute>
          }
        />

        {/* Shared Authenticated Pages (Citizens & Reviewers) */}
        <Route path="/discover" element={<DiscoverPage />} />
        <Route path="/schemes/:schemeId" element={<SchemeDetailsPage />} />
        <Route path="/scheme/:schemeId" element={<SchemeDetailsPage />} />
        <Route path="/schemes/:schemeId/benefits" element={<SchemeBenefitsPage />} />
        <Route path="/scheme/:schemeId/benefits" element={<SchemeBenefitsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
