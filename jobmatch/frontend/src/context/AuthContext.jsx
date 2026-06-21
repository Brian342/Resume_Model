/**
 * context/AuthContext.jsx — Global Auth State
 * ==============================================
 * This is the direct replacement for Streamlit's st.session_state
 * holding logged_in / user_id / user_name / role.
 *
 * HOW IT WORKS:
 *   - On app load, if a token exists in localStorage, we call GET /auth/me
 *     to restore the user's profile (mirrors checking session_state on
 *     every Streamlit rerun, but here it only needs to happen once,
 *     on page load/refresh).
 *   - login() calls POST /auth/login, stores the token, sets user state.
 *   - logout() clears the token and user state — mirrors do_logout().
 *   - Any component can call useAuth() to read { user, login, logout, loading }.
 */

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api, getErrorMessage } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true while we check for an existing session

  // On first load: if there's a saved token, try to restore the session.
  useEffect(() => {
    const token = localStorage.getItem("jobmatch_token");
    if (!token) {
      setLoading(false);
      return;
    }

    api
      .get("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.removeItem("jobmatch_token");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    try {
      const res = await api.post("/auth/login", { email, password });
      localStorage.setItem("jobmatch_token", res.data.access_token);
      setUser(res.data.user);
      return { success: true, user: res.data.user };
    } catch (err) {
      return { success: false, message: getErrorMessage(err) };
    }
  }, []);

  const register = useCallback(async (fullName, email, password, role) => {
    try {
      await api.post("/auth/register", {
        full_name: fullName,
        email,
        password,
        role,
      });
      return { success: true };
    } catch (err) {
      return { success: false, message: getErrorMessage(err) };
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("jobmatch_token");
    setUser(null);
  }, []);

  // Lets a component (e.g. the preferences page) update the cached
  // user object after a successful save, without a full re-fetch.
  const updateUser = useCallback((patch) => {
    setUser((prev) => (prev ? { ...prev, ...patch } : prev));
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, updateUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside an AuthProvider");
  return ctx;
}
