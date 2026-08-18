import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore(s => s.token);
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

/** Restricts a route to a set of roles; anyone else is bounced to the dashboard. */
export function RoleRoute({ roles, children }: { roles: string[]; children: React.ReactNode }) {
  const user = useAuthStore(s => s.user);
  if (user && !roles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}
