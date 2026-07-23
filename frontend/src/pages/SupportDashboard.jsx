import { useState } from "react";

import SupportSidebar from "../components/SupportSidebar";
import IncidentWorkspace from "../components/IncidentWorkspace";

import "../styles/support-dashboard.css";

function SupportDashboard() {

    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [profileOpen, setProfileOpen] = useState(false);

    return (
        <div className={`support-dashboard ${!sidebarOpen ? "sidebar-collapsed" : ""}`}>

            <SupportSidebar
                sidebarOpen={sidebarOpen}
                setSidebarOpen={setSidebarOpen}
            />

            <main className="support-main">

                <header className="support-header">

                    <h1>
                        Incident investigation workspace.
                    </h1>


                    <div className="profile-area">

                        <button
                            className="profile-menu-button"
                            onClick={() => setProfileOpen(!profileOpen)}
                        >
                            •••
                        </button>


                        {profileOpen && (

                            <div className="profile-menu">

                                <strong>
                                    Mukul Vishwakarma
                                </strong>

                                <span>
                                    Support Engineer
                                </span>

                                <button>
                                    Help
                                </button>

                                <button className="logout-button">
                                    Logout
                                </button>

                            </div>

                        )}

                    </div>

                </header>


                <IncidentWorkspace />

            </main>

        </div>
    );
}

export default SupportDashboard;