// frontend/src/components/AccountMenu.jsx
//
// Shared account avatar + dropdown (name, role, logout) used on both
// SupportDashboard and AdminDashboard — was duplicated in both before.

import { useState } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "../context/AuthContext";
import "../styles/account-menu.css";

const ROLE_LABELS = {
    admin: "Administrator",
    engineer: "Support Engineer",
};

function getInitials(name) {
    if (!name) return "?";
    return name.trim().charAt(0).toUpperCase();
}

function AccountMenu() {
    const [open, setOpen] = useState(false);
    const { username, role, logout } = useAuth();
    const navigate = useNavigate();

    async function handleLogout() {
        await logout();
        navigate("/", { replace: true });
    }

    return (
        <div className="profile-area">
            <button
                className="profile-menu-button"
                onClick={() => setOpen(!open)}
                aria-label="Account menu"
            >
                <span className="profile-avatar">{getInitials(username)}</span>
            </button>

            {open && (
                <div className="profile-menu">
                    <strong>{username}</strong>
                    <span>{ROLE_LABELS[role] ?? role}</span>
                    <button className="logout-button" onClick={handleLogout}>
                        Logout
                    </button>
                </div>
            )}
        </div>
    );
}

export default AccountMenu;