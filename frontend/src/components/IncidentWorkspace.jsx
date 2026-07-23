function IncidentWorkspace() {

    return (
        <section className="incident-workspace">


            <div className="incident-chat-box">

                <div className="chat-placeholder">
                    Ask anything
                </div>


                <div className="chat-input-footer">

                    <button className="add-button">
                        +
                    </button>


                    <button className="mic-button">
                        🎙
                    </button>

                </div>

            </div>


            <section className="recent-section">

                <div className="workspace-heading">

                    <div>

                        <span className="section-label">
                            RECENT INVESTIGATIONS
                        </span>

                        <h2>
                            Continue an investigation.
                        </h2>

                    </div>


                    <span className="retrieval-status">
                        ● RAG SYSTEM READY
                    </span>

                </div>


                <div className="investigation-grid">

                    <div className="investigation-card">

                        <span>
                            INC-1024
                        </span>

                        <h3>
                            Database connection timeout
                        </h3>

                        <p>
                            Investigated 2 hours ago
                        </p>

                    </div>


                    <div className="investigation-card">

                        <span>
                            INC-1018
                        </span>

                        <h3>
                            Authentication service failure
                        </h3>

                        <p>
                            Investigated yesterday
                        </p>

                    </div>


                    <div className="investigation-card">

                        <span>
                            INC-1007
                        </span>

                        <h3>
                            API response latency
                        </h3>

                        <p>
                            Investigated 3 days ago
                        </p>

                    </div>

                </div>

            </section>

        </section>
    );
}

export default IncidentWorkspace;