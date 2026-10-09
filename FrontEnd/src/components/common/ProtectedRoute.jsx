import { Navigate, useLocation } from 'react-router-dom';
import { getStoredToken, getStoredRole, isDevelopmentAuthBypassSession } from '../../services/authService';

/**
 * ProtectedRoute
 * Guards routes with token validation and role-based access control.
 * @param {React.ReactNode} children
 * @param {string[]} [allowedRoles] - Optional list of allowed roles ('user' | 'reviewer')
 */
export default function ProtectedRoute({ children, allowedRoles }) {
  const location = useLocation();
  const token = getStoredToken();
  const role = getStoredRole();

  // 1. Unauthenticated -> redirect to login
  if (!token && !isDevelopmentAuthBypassSession()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 2. Role authorization check
  if (allowedRoles && allowedRoles.length > 0) {
    if (!allowedRoles.includes(role)) {
      // If user is a reviewer trying to access citizen-only route -> redirect to reviewer dashboard
      if (role === 'reviewer') {
        return <Navigate to="/reviewer/dashboard" replace />;
      }
      // If user is an ordinary citizen trying to access reviewer route -> redirect to citizen dashboard
      return <Navigate to="/dashboard" replace />;
    }
  }

  return children;
}
