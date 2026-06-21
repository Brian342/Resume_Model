/**
 * pages/Login.jsx — mirrors show_login_page() in app.py
 * ==========================================================
 * Note: this exports `authStyles` too, since Register.jsx (next file)
 * shares the exact same visual shell (auth-screen, auth-card, etc.)
 * and will import that constant rather than duplicating the CSS.
 */

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!email || !password) {
      setError("Please fill in all fields.");
      return;
    }

    setSubmitting(true);
    const result = await login(email, password);
    setSubmitting(false);

    if (result.success) {
      // login() returns the user object directly, so we can route
      // straight to the correct home instead of a generic redirect.
      navigate(result.user.role === "employer" ? "/employer" : "/dashboard");
    } else {
      setError(result.message);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-card card">
        <div className="auth-brandmark">JM</div>
        <h1>JobMatch</h1>
        <p className="auth-sub">Pioneer Insurance Group Job Match Platform</p>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="alert alert-error">{error}</div>}

          <div className="field">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          <button className="btn btn-primary auth-submit" type="submit" disabled={submitting}>
            {submitting ? <span className="spinner spinner-light" /> : "Log in"}
          </button>
        </form>

        <div className="auth-divider" />

        <p className="auth-footer-text">
          Don't have an account? <Link to="/register">Create one</Link>
        </p>
      </div>

      <style>{authStyles}</style>
    </div>
  );
}

export const authStyles = `
  .auth-screen {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(160deg, var(--navy-900) 0%, var(--navy-700) 55%, var(--navy-500) 100%);
    padding: 24px;
  }
  .auth-card {
    width: 100%;
    max-width: 420px;
    padding: 40px 36px;
    text-align: center;
  }
  .auth-brandmark {
    width: 48px;
    height: 48px;
    margin: 0 auto 18px;
    border-radius: 12px;
    background: var(--amber-500);
    color: var(--navy-900);
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .auth-card h1 {
    font-size: 26px;
  }
  .auth-sub {
    color: var(--slate-600);
    font-size: 13.5px;
    margin: 6px 0 28px;
  }
  .auth-form {
    text-align: left;
  }
  .auth-submit {
    width: 100%;
    margin-top: 6px;
    padding: 12px;
  }
  .auth-divider {
    height: 1px;
    background: var(--slate-200);
    margin: 26px 0 18px;
  }
  .auth-footer-text {
    font-size: 14px;
    color: var(--slate-600);
  }
  .auth-footer-text a {
    color: var(--navy-700);
    font-weight: 600;
  }
  .auth-footer-text a:hover {
    color: var(--amber-500);
  }
  .role-pills {
    display: flex;
    gap: 10px;
    margin-bottom: 18px;
  }
  .role-pill {
    flex: 1;
    padding: 12px;
    border-radius: var(--radius-sm);
    border: 1.5px solid var(--slate-200);
    background: white;
    cursor: pointer;
    text-align: center;
    font-size: 14px;
    font-weight: 600;
    color: var(--slate-600);
    transition: all 0.15s ease;
  }
  .role-pill-active {
    border-color: var(--navy-700);
    background: var(--navy-700);
    color: white;
  }
  .spinner-light {
    border-color: rgba(255,255,255,0.3);
    border-top-color: white;
  }
`;
