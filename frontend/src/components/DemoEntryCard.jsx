import { Link } from "react-router";
import "../styles/demo-explorer.css";

function DemoEntryCard() {
  return (
    <section className="demo-entry-card">
      <span className="demo-badge">LIVE PRODUCT DEMO</span>
      <h2>Explore ResolveIQ end to end — no login required.</h2>
      <p>
        Try the live RAG workflow as a support engineer, then switch to a safe
        read-only admin view to inspect system health, RAG insights, document
        visibility, and operational controls.
      </p>
      <p>
        Sensitive actions remain protected: no private data access, credential
        exposure, document mutation, or account changes.
      </p>

      <div className="demo-entry-actions">
        <Link className="demo-primary-button" to="/demo/support">
          Explore Support Engineer
        </Link>
        <Link className="demo-secondary-button" to="/demo/admin">
          Explore Admin Dashboard
        </Link>
      </div>
    </section>
  );
}

export default DemoEntryCard;
