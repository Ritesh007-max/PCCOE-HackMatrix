import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@clerk/react';
import { getStoredToken, isDevelopmentAuthBypassSession } from '../../services/authService';

/**
 * ProtectedRoute
 * Guards private citizen dashboard routes.
 * If citizen is unauthenticated or session expired, redirects to /login.
 */
export default function ProtectedRoute({ children }) {
  const location = useLocation();
  const token = getStoredToken();
  const { isSignedIn, isLoaded } = useAuth();

  if (!isLoaded) {
    return null;
  }

  if (!isSignedIn && !token && !isDevelopmentAuthBypassSession()) {
    // Preserve requested path for redirect after login if needed
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}
