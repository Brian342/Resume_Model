import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {useAuth } from "../contextAuthContext";

export default function Layout() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    function handleLogout() {
        logout();
        navigate("/login");
        }

    const seekerLinks = [
        { to: "/dashboard", label: "My Dashboard" },
        { to: "/jobs", label: "Browse Jobs" },
        { to: "/preferences", label: "Job Preferences" },
        ];

    const employerLinks = [
        { to: "/employer", label: "Dashboard" },
        { to: "/employer/post", label: "Post a job" },
        ];

    const links = user?.role === "employer" ? employerLinks : seekerLinks;

    return (
        <div className="app-shell">
            <aside className="sidebar">

        )
    }