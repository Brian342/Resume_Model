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
        {}
        ]
    }