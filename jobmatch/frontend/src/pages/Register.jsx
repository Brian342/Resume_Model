import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { authStyles } from "./Login";

export default function Register() {
    const { register } = useAuth();
    const navigate = useNavigate();

    const [fullName, setFullName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [role, setRole] = useState("seeker");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [submitting, setSubmitting] = useState(false);

    async function handleSubmit(e) {
        e.preventDefault();
        setError("");
        setSuccess("");

        if (!fullName.trim()) {
            setError("Please enter your full Name.");
            return;
            }
        if (password !== confirm) {
            setError("Passwords do not Match.");
            return;
            }
        if (password.length < 6) {
            setError("Password must be at least 6 Characters");
            return;
            }

        setSubmitting(true);
        const result = await register(fullName, email, password, role);
        setSubmitting(false);

        if (result.success) {
            setSuccess("Account created! Redirecting to login");
            setTimeout(() => navigate("/login"), 1200);
            }else {
                setError(result.message);
            }
        }
    return (
        <div className="auth-screen">
            <div className="auth-card card">
                <div className="auth-brandmark">JM</div>
                <h1>JobMatch</h1>
                <p className="auth-sub">Pioneer Insurance Group Job Match platform</p>

                <form onSubmit={handleSubmit} className="auth-form">
                    {error && <div className="alert alert-error">{error}</div>}
                    {success && <div className="alert alert-success">{success}</div>}

                    <div className="field">
                        <label htmlFor="fullName">Full name</label>
                        <input
                            id="fullName"
                            placeholder="John Doe"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                        />
                        </div>

                        <div className="field">
                            <label htmlFor="email">Email address</label>
                            <input
                                id="email"
                                type="email"
                                placeholder="you@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}

                            />
                            </div>

                            <div className="field">
                            <label htmlFor="password">Password (min 6 characters)</label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                            </div>

                            <div className="field">
                            <label htmlFor="confirm">Confirm Password</label>
                            <input
                                id="confirm"
                                type="password"
                                value={confirm}
                                onChange={(e) => setConfirm(e.target.value)}
                            />
                            </div>

                            <div className="field">
                            <label htmlFor="email">Email address</label>
                            <input
                                id="email"
                                type="email"
                                placeholder="you@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}

                            />
                            </div>



        )

    }
