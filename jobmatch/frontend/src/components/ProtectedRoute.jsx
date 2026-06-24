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
