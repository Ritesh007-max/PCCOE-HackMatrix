import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getStoredToken } from '../../services/authService';

/**
 * ProtectedRoute
 * Guards private citizen dashboard routes.
 * If citizen is unauthenticated or session expired, redirects to /login.
 */
export default function ProtectedRoute({ children }) {
  const location = useLocation();
  const token = getStoredToken();

  if (!token) {
    // Preserve requested path for redirect after login if needed
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}
