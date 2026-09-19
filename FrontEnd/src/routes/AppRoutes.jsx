import React from 'react';
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

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        {/* Default route redirects to /dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/discover" element={<DiscoverPage />} />
        <Route path="/schemes/:schemeId" element={<SchemeDetailsPage />} />
        <Route path="/schemes/:schemeId/benefits" element={<SchemeBenefitsPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
