import { useState } from "react";
import { Link } from "react-router";

import AdminOverviewTab from "../components/admin/AdminOverviewTab";
import AdminEngineersTab from "../components/admin/AdminEngineersTab";
import AdminDocumentsTab from "../components/admin/AdminDocumentsTab";
import AdminRagInsightsTab from "../components/admin/AdminRagInsightsTab";
import AdminHealthTab from "../components/admin/AdminHealthTab";
import AccountMenu from "../components/AccountMenu";
import "../styles/admin-dashboard.css";

const TABS = [
    { id: "overview", label: "Overview" },
    { id: "engineers", label: "Engineers" },
    { id: "documents", label: "Documents" },
    { id: "rag", label: "RAG Insights" },
    { id: "health", label: "System Health" },
];

function AdminDashboard() {

    const [activeTab, setActiveTab] = useState("overview");

    return (
        <div className="admin-dashboard">

            <header className="admin-header">

                <div>
                    <span className="admin-eyebrow">
                        ADMINISTRATION
                    </span>

                    <h1>
                        System overview.
                    </h1>

                    <p>
                        Monitor ResolveIQ adoption and support productivity.
                    </p>
                </div>


                <div className="admin-header-actions">

                    <Link to="/support" className="admin-nav-link">
                        Support Workspace
                    </Link>

                    <AccountMenu />

                </div>

            </header>


            <nav className="admin-tabs">
                {TABS.map((tab) => (
                    <button
                        key={tab.id}
                        type="button"
                        className={activeTab === tab.id ? "selected" : ""}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        {tab.label}
                    </button>
                ))}
            </nav>


            <main className="admin-content">

                {activeTab === "overview" && <AdminOverviewTab />}
                {activeTab === "engineers" && <AdminEngineersTab />}
                {activeTab === "documents" && <AdminDocumentsTab />}
                {activeTab === "rag" && <AdminRagInsightsTab />}
                {activeTab === "health" && <AdminHealthTab />}

            </main>

        </div>
    );
}

export default AdminDashboard;