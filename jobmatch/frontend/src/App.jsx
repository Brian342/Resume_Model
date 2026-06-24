/**
 * App.jsx — Route Configuration
 * =================================
 * Replaces the if/elif page routing inside main() in app.py with real
 * React Router routes.
 *
 * CURRENT STATE: only Login/Register + placeholder dashboards exist so
 * far. As we build each real page (JobBoard, JobDetail, ApplyForm,
 * EmployerDashboard, etc.) we'll swap the placeholders out one at a time.
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";

import Login from "./pages/Login";
import Register from "./pages/Register";

// ── Temporary placeholders — will be replaced as we build each page ──
function SeekerDashboardPlaceholder() {
  const { user } = useAuth();
  return (
    <div className="page-shell">
      <div className="page-header">
        <span className="eyebrow">Overview</span>
        <h1>Welcome back, {user?.full_name?.split(" ")[0]}</h1>
        <p>Your seeker dashboard is coming up next.</p>
      </div>
    </div>
  );
}

function EmployerDashboardPlaceholder() {
  const { user } = useAuth();
  return (
    <div className="page-shell">
      <div className="page-header">
        <span className="eyebrow">Employer dashboard</span>
        <h1>Welcome back, {user?.full_name?.split(" ")[0]}</h1>
        <p>Your job postings will show up here once we build this page.</p>
      </div>
    </div>
  );
}

function HomeRedirect() {
  // Mirrors main()'s role-based landing: seekers go to their dashboard,
  // employers go to theirs.
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "employer" ? "/employer" : "/dashboard"} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Authenticated shell */}
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute requireRole="seeker">
                  <SeekerDashboardPlaceholder />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employer"
              element={
                <ProtectedRoute requireRole="employer">
                  <EmployerDashboardPlaceholder />
                </ProtectedRoute>
              }
            />
          </Route>

          <Route path="/" element={<HomeRedirect />} />
          <Route path="*" element={<HomeRedirect />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
