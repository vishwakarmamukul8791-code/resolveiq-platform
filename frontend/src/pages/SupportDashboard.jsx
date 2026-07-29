import { useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
// import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import SupportSidebar from "../components/SupportSidebar";
import IncidentWorkspace from "../components/IncidentWorkspace";
import HelpModal from "../components/HelpModal";
import AccountMenu from "../components/AccountMenu";

import "../styles/support-dashboard.css";

function QuestionIcon() {
    return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="9" />
            <path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.9.4-1.5 1-1.5 2.2" />
            <circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none" />
        </svg>
    );
}

function SupportDashboard() {

    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [helpOpen, setHelpOpen] = useState(false);

    // These three pieces of state are the whole bridge between the sidebar
    // and the workspace — they're siblings, so this has to live in the
    // shared parent rather than in either child directly.
    const [resetToken, setResetToken] = useState(0);
    const [loadedEntry, setLoadedEntry] = useState(null);
    const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

    const { role } = useAuth();

    const handleNewInvestigation = useCallback(() => {
        setLoadedEntry(null);
        setResetToken((t) => t + 1);
    }, []);

    const handleSelectEntry = useCallback((entry) => {
        setLoadedEntry(entry);
    }, []);

    const handleAsked = useCallback(() => {
        setHistoryRefreshKey((k) => k + 1);
    }, []);

    return (
        <div className={`support-dashboard ${!sidebarOpen ? "sidebar-collapsed" : ""}`}>

            <SupportSidebar
                sidebarOpen={sidebarOpen}
                setSidebarOpen={setSidebarOpen}
                activeEntryId={loadedEntry?.id ?? null}
                onNewInvestigation={handleNewInvestigation}
                onSelectEntry={handleSelectEntry}
                refreshKey={historyRefreshKey}
            />

            <main className="support-main">

                <header className="support-header">

                    <h1>
                        Incident investigation workspace.
                    </h1>


                    <div className="header-actions">

                        {role === "admin" && (
                            <Link to="/admin" className="admin-nav-link">
                                Admin Dashboard
                            </Link>
                        )}

                        <button
                            type="button"
                            className="help-button"
                            onClick={() => setHelpOpen(true)}
                            aria-label="Help"
                            title="Help"
                        >
                            <QuestionIcon />
                        </button>

                        <AccountMenu />

                    </div>

                </header>


                <IncidentWorkspace
                    resetToken={resetToken}
                    loadedEntry={loadedEntry}
                    onAsked={handleAsked}
                />

            </main>

            {helpOpen && <HelpModal onClose={() => setHelpOpen(false)} />}

        </div>
    );
}

export default SupportDashboard;