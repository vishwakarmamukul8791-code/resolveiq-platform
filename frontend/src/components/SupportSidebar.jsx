function SupportSidebar({ sidebarOpen, setSidebarOpen }) {

    return (
        <aside className="support-sidebar">

            <div className="sidebar-top">

                {sidebarOpen && (

                    <div className="sidebar-brand">

                        <div className="sidebar-mark">
                            IR
                        </div>

                        <div className="sidebar-brand-text">

                            <strong>
                                Incident AI
                            </strong>

                            <span>
                                Support Workspace
                            </span>

                        </div>

                    </div>

                )}


                <button
                    className="sidebar-toggle"
                    onClick={() => setSidebarOpen(!sidebarOpen)}
                >
                    {sidebarOpen ? "‹" : "›"}
                </button>

            </div>


            {sidebarOpen && (

                <div className="sidebar-section">

                    <span className="sidebar-label">
                        INVESTIGATIONS
                    </span>


                    <div className="sidebar-item active">
                        <span>＋</span>
                        <p>New Investigation</p>
                    </div>


                    <div className="sidebar-item">
                        <span>◷</span>
                        <p>Recent Investigations</p>
                    </div>


                    <div className="sidebar-item">
                        <span>★</span>
                        <p>Pinned Investigations</p>
                    </div>


                    <div className="sidebar-item">
                        <span>⌘</span>
                        <p>History</p>
                    </div>

                </div>

            )}


            {sidebarOpen && (

                <div className="sidebar-footer">

                    <span className="sidebar-label">
                        SYSTEM
                    </span>

                    <div className="sidebar-system">

                        <span className="status-dot"></span>

                        RAG System Ready

                    </div>

                </div>

            )}

        </aside>
    );
}

export default SupportSidebar;