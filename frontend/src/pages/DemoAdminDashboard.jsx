import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import FullProjectCallout from "../components/FullProjectCallout";
import { DemoApiError, getPublicDemoContext } from "../api/demoClient";
import "../styles/demo-explorer.css";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "engineers", label: "Engineers" },
  { id: "documents", label: "Documents" },
  { id: "rag", label: "RAG Insights" },
  { id: "health", label: "System Health" },
];

function StateBadge({ children, tone = "safe" }) {
  return <span className={`demo-state-badge ${tone}`}>{children}</span>;
}

function MetricCard({ label, value, note }) {
  return (
    <div className="demo-metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </div>
  );
}

function OverviewTab({ data }) {
  return (
    <div className="demo-panel-stack">
      <section className="demo-panel">
        <div className="demo-section-heading">
          <div>
            <span className="demo-eyebrow">ADMIN OVERVIEW</span>
            <h2>Explore the operations layer safely.</h2>
          </div>
          <StateBadge>READ ONLY</StateBadge>
        </div>

        <div className="demo-metric-grid">
          <MetricCard label="Public demo documents" value={data.document_count} note="Explicit allow-list only" />
          <MetricCard label="Authenticated admin access" value="Required" note="JWT + role enforcement unchanged" />
          <MetricCard label="Destructive demo actions" value="Disabled" note="No upload, delete, reset, or user mutation" />
          <MetricCard label="Private data exposure" value="None" note="Only public demo documents can reach guest RAG" />
        </div>
      </section>
    </div>
  );
}

function EngineersTab() {
  const actions = [
    ["Create engineer", "Creates a support-engineer account and one-time temporary password."],
    ["Enable / disable", "Controls whether an engineer can authenticate without deleting their record."],
    ["Reset password", "Rotates an engineer password and forces the secure reset flow."],
    ["Session analytics", "Tracks sessions, question volume, confidence mix, and investigation activity."],
  ];

  return (
    <section className="demo-panel">
      <div className="demo-section-heading">
        <div>
          <span className="demo-eyebrow">ENGINEER MANAGEMENT</span>
          <h2>Administrative controls are visible; real identities are not.</h2>
          <p className="demo-muted-copy">
            Public viewers never receive admin credentials, engineer identities, session transcripts,
            temporary passwords, or mutation access.
          </p>
        </div>
        <StateBadge>IDENTITIES HIDDEN</StateBadge>
      </div>

      <div className="demo-action-table">
        {actions.map(([name, description]) => (
          <div className="demo-action-row" key={name}>
            <div>
              <strong>{name}</strong>
              <p>{description}</p>
            </div>
            <button type="button" disabled title="Disabled in public demo">
              Disabled in public demo
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

function DocumentsTab({ data }) {
  return (
    <section className="demo-panel">
      <div className="demo-section-heading">
        <div>
          <span className="demo-eyebrow">DOCUMENT LIFECYCLE</span>
          <h2>Only the explicit public-demo corpus is shown.</h2>
          <p className="demo-muted-copy">
            The real admin can upload, process, inspect, and delete documents. Public demo viewers can
            inspect only the names of files intentionally allow-listed for guest retrieval.
          </p>
        </div>
        <button type="button" className="demo-disabled-action" disabled>
          Upload disabled
        </button>
      </div>

      <div className="demo-document-table">
        <div className="demo-document-row header">
          <span>Document</span><span>Type</span><span>Visibility</span><span>Status</span><span>Actions</span>
        </div>
        {data.documents.map((doc) => (
          <div className="demo-document-row" key={doc.name}>
            <strong>{doc.name}</strong>
            <span>{doc.type}</span>
            <span>{doc.visibility}</span>
            <StateBadge>{doc.status}</StateBadge>
            <button type="button" disabled title="Delete is protected by the real admin role">
              Delete disabled
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

function RagInsightsTab({ data }) {
  const metrics = data.evaluation_snapshot;
  const percent = (value) => `${(value * 100).toFixed(1)}%`;

  return (
    <div className="demo-panel-stack">
      <section className="demo-panel">
        <div className="demo-section-heading">
          <div>
            <span className="demo-eyebrow">RETRIEVAL EVALUATION</span>
            <h2>Measured retrieval quality, not a chatbot-only demo.</h2>
            <p className="demo-muted-copy">{metrics.label}</p>
          </div>
        </div>

        <div className="demo-metric-grid">
          <MetricCard label="Semantic Hit@1" value={percent(metrics.semantic_hit_at_1)} />
          <MetricCard label="BM25 Hit@1" value={percent(metrics.bm25_hit_at_1)} />
          <MetricCard label="Hybrid Hit@1" value={percent(metrics.hybrid_hit_at_1)} />
          <MetricCard label="Hybrid Hit@5" value={percent(metrics.hybrid_hit_at_5)} />
        </div>
      </section>

      <section className="demo-panel">
        <span className="demo-eyebrow">RAG PIPELINE</span>
        <div className="demo-pipeline">
          {[
            "Question validation",
            "Configurable query rewrite",
            "BM25 + semantic retrieval",
            "Reciprocal Rank Fusion",
            "Optional rerank",
            "Confidence gate",
            "Grounded Gemini answer",
            "Citations / safe abstention",
          ].map((step, index, items) => (
            <div className="demo-pipeline-step" key={step}>
              <span>{index + 1}</span>
              <strong>{step}</strong>
              {index < items.length - 1 && <i>→</i>}
            </div>
          ))}
        </div>

        <div className="demo-insight-note">
          Knowledge-gap queries, source analytics, and engineer-level usage exist in the authenticated
          admin dashboard. Their raw production records are intentionally not copied into this public view.
        </div>
      </section>
    </div>
  );
}

function SystemHealthTab({ data }) {
  const healthEntries = Object.entries(data.health || {});
  const configEntries = Object.entries(data.retrieval_config || {});

  return (
    <div className="demo-panel-stack">
      <section className="demo-panel">
        <div className="demo-section-heading">
          <div>
            <span className="demo-eyebrow">SANITIZED LIVE HEALTH</span>
            <h2>Operational state without secrets or internal identifiers.</h2>
          </div>
          <StateBadge>{data.health?.status || "Unavailable"}</StateBadge>
        </div>
        <div className="demo-key-value-grid">
          {healthEntries.map(([key, value]) => (
            <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{String(value)}</strong></div>
          ))}
        </div>
      </section>

      <section className="demo-panel">
        <span className="demo-eyebrow">SAFE RETRIEVAL CONFIG</span>
        <div className="demo-key-value-grid">
          {configEntries.length ? configEntries.map(([key, value]) => {
            const label = key === "query_rewrite_enabled"
              ? "Configurable query rewrite"
              : key.replaceAll("_", " ");
            const displayValue = key === "query_rewrite_enabled"
              ? (value ? "Enabled" : "Disabled")
              : String(value);

            return (
              <div key={key}>
                <span>{label}</span>
                <strong>{displayValue}</strong>
              </div>
            );
          }) : <p className="demo-muted-copy">Retrieval configuration is temporarily unavailable.</p>}
        </div>
        <p className="demo-security-note">
          API keys, JWT secrets, database URLs, service-role keys, storage credentials, private file paths,
          and authenticated user/session data are never returned by this endpoint.
        </p>
      </section>
    </div>
  );
}

function DemoAdminDashboard() {
  const [activeTab, setActiveTab] = useState("overview");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    getPublicDemoContext()
      .then((payload) => active && setData(payload))
      .catch((err) => {
        if (!active) return;
        setError(err instanceof DemoApiError ? err.message : "Unable to load the public admin demo.");
      });
    return () => { active = false; };
  }, []);

  const activeLabel = useMemo(
    () => TABS.find((tab) => tab.id === activeTab)?.label || "Overview",
    [activeTab]
  );

  return (
    <div className="demo-admin-page">
      <header className="demo-admin-header">
        <div>
          <span className="demo-eyebrow">ADMINISTRATION · PUBLIC PREVIEW</span>
          <h1>ResolveIQ system overview.</h1>
          <p>
            Same product responsibilities, deliberately reduced authority. This page never calls the
            authenticated admin mutation endpoints.
          </p>
        </div>
        <div className="demo-admin-header-actions">
          <Link to="/demo/support">Open Support Workspace</Link>
          <Link to="/">Back to landing</Link>
        </div>
      </header>
<nav className="demo-admin-tabs" aria-label="Admin demo sections">
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

      <main className="demo-admin-content" aria-label={activeLabel}>
        {error && <div className="demo-error-card">{error}</div>}
        {!error && !data && <div className="demo-loading-card">Loading sanitized demo data…</div>}
        {data && activeTab === "overview" && <OverviewTab data={data} />}
        {data && activeTab === "engineers" && <EngineersTab />}
        {data && activeTab === "documents" && <DocumentsTab data={data} />}
        {data && activeTab === "rag" && <RagInsightsTab data={data} />}
        {data && activeTab === "health" && <SystemHealthTab data={data} />}
      </main>

      <div className="demo-admin-full-project">
        <FullProjectCallout />
      </div>
    </div>
  );
}

export default DemoAdminDashboard;
