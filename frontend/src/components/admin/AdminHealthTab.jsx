// frontend/src/components/admin/AdminHealthTab.jsx

import { useEffect, useState, useCallback } from "react";
import { adminApi, ApiError } from "../../api/client";

const COMPONENT_LABELS = {
  faiss_index: "FAISS Index",
  metadata: "Metadata Store",
  registry: "Document Registry",
  gemini_api: "Gemini API Key",
  jwt_secret: "JWT Secret",
};

const OK_VALUES = new Set(["Loaded", "Configured"]);

function AdminHealthTab() {
  const [state, setState] = useState({ status: "loading" });

  const load = useCallback(() => {
    setState({ status: "loading" });
    adminApi
      .getSystemHealth()
      .then((data) => setState({ status: "ready", data }))
      .catch((err) => {
        setState({
          status: "error",
          error: err instanceof ApiError ? err.message : "Could not load system health.",
        });
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (state.status === "loading") {
    return (
      <div className="admin-panel">
        <p className="admin-hint">Checking system health…</p>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="admin-panel">
        <p className="admin-hint error">{state.error}</p>

        <p className="admin-hint">
          If this says "Failed to retrieve system health," it's a known backend bug —{" "}
          <code>admin.py</code> imports <code>get_health</code> from{" "}
          <code>health_service.py</code>, but that module only defines{" "}
          <code>get_health_status</code>. Fixing the import name in the backend is enough — this
          tab needs no frontend changes once that's corrected.
        </p>

        <button type="button" className="row-action retry-button" onClick={load}>
          Retry
        </button>
      </div>
    );
  }

  const { health, stats } = state.data;
  const isHealthy = health.status === "Healthy";

  const components = Object.entries(COMPONENT_LABELS).map(([key, label]) => ({
    key,
    label,
    value: health[key],
    ok: OK_VALUES.has(health[key]),
  }));

  return (
    <>
      <section className={`health-banner ${isHealthy ? "healthy" : "unhealthy"}`}>
        <div className="health-banner-dot" />

        <div>
          <strong>{isHealthy ? "All systems operational" : "Attention needed"}</strong>
          <p>Overall status: {health.status}</p>
        </div>

        <button type="button" className="row-action" onClick={load}>
          Refresh
        </button>
      </section>

      <section className="admin-panel">
        <div className="panel-heading">
          <div>
            <span className="section-label">COMPONENTS</span>
            <h2>Backend dependencies</h2>
          </div>
        </div>

        <div className="health-grid">
          {components.map((c) => (
            <div key={c.key} className="health-item">
              <span className={`status ${c.ok ? "active" : "completed"}`}>
                {c.value ?? "Unknown"}
              </span>
              <p>{c.label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="admin-kpi-grid">
        <div className="admin-kpi-card">
          <span>TOTAL DOCUMENTS</span>
          <strong>{stats.total_documents}</strong>
          <p>Indexed in the registry</p>
        </div>

        <div className="admin-kpi-card">
          <span>TOTAL CHUNKS</span>
          <strong>{stats.total_chunks}</strong>
          <p>Across all documents</p>
        </div>

        <div className="admin-kpi-card">
          <span>TOTAL VECTORS</span>
          <strong>{stats.total_vectors}</strong>
          <p>In the FAISS index</p>
        </div>

        <div className="admin-kpi-card">
          <span>INDEX / METADATA</span>
          <strong className={stats.index_metadata_in_sync ? "sync-ok" : "sync-bad"}>
            {stats.index_metadata_in_sync ? "In sync" : "Out of sync"}
          </strong>
          <p>Vector count vs. metadata count</p>
        </div>
      </section>

      <section className="admin-panel">
        <div className="panel-heading">
          <div>
            <span className="section-label">CONFIGURATION</span>
            <h2>Retrieval settings</h2>
          </div>
        </div>

        <div className="config-list">
          <div>
            <span>Embedding model</span>
            <strong>{stats.embedding_model}</strong>
          </div>
          <div>
            <span>Embedding dimension</span>
            <strong>{stats.embedding_dimension}</strong>
          </div>
          <div>
            <span>Vector database</span>
            <strong>{stats.vector_database}</strong>
          </div>
          <div>
            <span>Top K</span>
            <strong>{stats.top_k}</strong>
          </div>
          <div>
            <span>Chunk size</span>
            <strong>{stats.chunk_size}</strong>
          </div>
          <div>
            <span>Chunk overlap</span>
            <strong>{stats.chunk_overlap}</strong>
          </div>
        </div>
      </section>
    </>
  );
}

export default AdminHealthTab;