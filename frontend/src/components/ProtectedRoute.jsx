// frontend/src/components/ProtectedRoute.jsx

import { Navigate } from "react-router";
import { useAuth } from "../context/AuthContext";

function ProtectedRoute({ children, allowedRoles }) {
  const { isAuthenticated, isLoading, role, mustResetPassword } = useAuth();

  // Avoid a flash-redirect while the mount-time /auth/me restore check
  // (in AuthContext) is still in flight.
  if (isLoading) {
    return <div className="auth-loading">Loading…</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (mustResetPassword) {
    return <Navigate to="/" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    return <Navigate to="/" replace />;
  }

  return children;
}

export default ProtectedRoute;