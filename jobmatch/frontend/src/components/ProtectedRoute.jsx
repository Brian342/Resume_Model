/**
 * components/ProtectedRoute.jsx
 * ==================================
 * Gatekeeper for routes that require login (and optionally a specific role).
 * Mirrors the "if not st.session_state['logged_in']: show login" check
 * at the top of main() in app.py, plus the role-specific page routing
 * (seeker_dashboard vs employer_dashboard).
 *
 * USAGE (once we wire up App.jsx):
 *   <ProtectedRoute><Layout /></ProtectedRoute>                    -> any logged-in user
 *   <ProtectedRoute requireRole="seeker"><JobBoard /></ProtectedRoute>  -> seekers only
 */

import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, requireRole }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="route-loading">
        <div className="spinner" />
        <style>{`
          .route-loading {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
          }
        `}</style>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requireRole && user.role !== requireRole) {
    // e.g. a seeker trying to reach an employer-only page —
    // send them to their own home instead of an error page.
    return <Navigate to={user.role === "employer" ? "/employer" : "/dashboard"} replace />;
  }

  return children;
}
