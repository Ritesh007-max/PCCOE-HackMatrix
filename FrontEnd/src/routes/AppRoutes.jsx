import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import DashboardPage from '../pages/DashboardPage';
import DiscoverPage from '../pages/DiscoverPage';
import SchemeDetailsPage from '../pages/SchemeDetailsPage';
import SchemeBenefitsPage from '../pages/SchemeBenefitsPage';
import DocumentsPage from '../pages/DocumentsPage';
import ApplicationsPage from '../pages/ApplicationsPage';
import ProfilePage from '../pages/ProfilePage';
import NotFoundPage from '../pages/NotFoundPage';

import SignupPage from '../pages/SignupPage';
import ProtectedRoute from '../components/common/ProtectedRoute';

export default function AppRoutes() {
  return (
    <Routes>
      {/* Default route redirects to /signup when starting npm run dev */}
      <Route path="/" element={<Navigate to="/signup" replace />} />

      {/* Standalone Authentication Pages */}
      <Route path="/signup" element={<SignupPage initialMode="signup" />} />
      <Route path="/register" element={<SignupPage initialMode="signup" />} />
      <Route path="/login" element={<SignupPage initialMode="signin" />} />
      <Route path="/signin" element={<SignupPage initialMode="signin" />} />

      {/* Main Authenticated Dashboard Pages */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/discover" element={<DiscoverPage />} />
        <Route path="/schemes/:schemeId" element={<SchemeDetailsPage />} />
        <Route path="/scheme/:schemeId" element={<SchemeDetailsPage />} />
        <Route path="/schemes/:schemeId/benefits" element={<SchemeBenefitsPage />} />
        <Route path="/scheme/:schemeId/benefits" element={<SchemeBenefitsPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
