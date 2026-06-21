
/**
 * api/client.js — Central API client
 * ====================================
 * Every request to the FastAPI backend goes through this one axios
 * instance. Two jobs:
 *   1. Prefix every request with the backend's base URL, so components
 *      just call api.get("/jobs") instead of the full URL every time.
 *   2. Automatically attach the JWT (from localStorage) as an
 *      Authorization header on every request — this is what replaces
 *      Streamlit's st.session_state staying alive across reruns.
 *
 * VITE_API_URL should be set in jobmatch/frontend/.env, e.g.:
 *   VITE_API_URL=http://localhost:8000
 */
 import axios from "axios";

 const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

 export const api = axios.create({
    baseURL: BASE_URL,
 });

// Attach the token to every outgoing request, if we have one.
api.interceptors.request.use((config) => {
    const token = localStorage.getItem("jobmatch_token");
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config
});
// If the backend ever returns 401 (expired/invalid token), clear the
// stale token and bounce to login — mirrors do_logout() clearing
// st.session_state when credentials stop being valid.
api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        localStorage.removeItem("jobmatch_token");
        if (window.location.pathname !== "/login") {
           window.location.href = "/login";
        }
      }
      return Promise.reject(error);
    }
);
/**
 * Pulls a readable error message out of a FastAPI error response.
 * FastAPI typically returns { detail: "message" } on HTTPException,
 * or { detail: [{ msg: "...", loc: [...] }] } on Pydantic validation errors.
 */
export function getErrorMessage(error) {
  const detail = error?.response?.data?.detail;

  if (!detail) return error?.message || "Something went wrong. Please try again.";

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg).join(" ");
  }

  return "Something went wrong. Please try again.";
}
