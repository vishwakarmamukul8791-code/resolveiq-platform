// frontend/src/components/admin/AdminOverviewTab.jsx

import { useEffect, useState } from "react";
import { adminApi, ApiError } from "../../api/client";

function AdminOverviewTab() {
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    Promise.all([adminApi.getAnalytics(), adminApi.listEngineers()])
      .then(([analytics, engineersData]) => {
        setState({ status: "ready", analytics, engineers: engineersData.engineers ?? [] });
      })
      .catch((err) => {
        setState({
          status: "error",
          error: err instanceof ApiError ? err.message : "Could not load analytics.",
        });
      });
  }, []);

  if (state.status === "loading") {
    return (
      <div className="admin-panel">
        <p className="admin-hint">Loading analytics…</p>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="admin-panel">
        <p className="admin-hint error">{state.error}</p>
      </div>
    );
  }

  const { analytics, engineers } = state;
  const activeEngineers = engineers.filter((e) => e.is_active).length;
  const avgPerEngineer =
    engineers.length > 0 ? (analytics.total_questions / engineers.length).toFixed(1) : "0";

  const {
    High = 0,
    Medium = 0,
    Low = 0,
    High_pct = 0,
    Medium_pct = 0,
    Low_pct = 0,
  } = analytics.confidence_distribution ?? {};

  const maxEngineerQuestions = Math.max(1, ...analytics.per_engineer.map((e) => e.questions), 1);

  return (
    <>
      <section className="admin-kpi-grid">
        <div className="admin-kpi-card">
          <span>ACTIVE ENGINEERS</span>
          <strong>{activeEngineers}</strong>
          <p>of {engineers.length} total accounts</p>
        </div>

        <div className="admin-kpi-card">
          <span>QUESTIONS ASKED</span>
          <strong>{analytics.total_questions}</strong>
          <p>Engineer-authored, all time</p>
        </div>

        <div className="admin-kpi-card">
          <span>HIGH-CONFIDENCE RATE</span>
          <strong>
            {analytics.corpus_coverage_score != null ? `${analytics.corpus_coverage_score}%` : "—"}
          </strong>
          <p>Answered with High confidence</p>
        </div>

        <div className="admin-kpi-card">
          <span>AVG QUESTIONS / ENGINEER</span>
          <strong>{avgPerEngineer}</strong>
          <p>Across all accounts</p>
        </div>
      </section>

      <section className="admin-panel">
        <div className="panel-heading">
          <div>
            <span className="section-label">CONFIDENCE DISTRIBUTION</span>
            <h2>How the RAG system is performing</h2>
          </div>
        </div>

        {analytics.total_questions === 0 ? (
          <p className="admin-hint">No questions have been asked yet.</p>
        ) : (
          <>
            <div className="confidence-bar">
              <div className="segment high" style={{ width: `${High_pct}%` }} />
              <div className="segment medium" style={{ width: `${Medium_pct}%` }} />
              <div className="segment low" style={{ width: `${Low_pct}%` }} />
            </div>

            <div className="confidence-legend">
              <div>
                <i className="dot high" /> High — {High} ({High_pct}%)
              </div>
              <div>
                <i className="dot medium" /> Medium — {Medium} ({Medium_pct}%)
              </div>
              <div>
                <i className="dot low" /> Low — {Low} ({Low_pct}%)
              </div>
            </div>
          </>
        )}
      </section>

      <section className="admin-panel">
        <div className="panel-heading">
          <div>
            <span className="section-label">PER ENGINEER</span>
            <h2>Questions asked</h2>
          </div>
        </div>

        {analytics.per_engineer.length === 0 ? (
          <p className="admin-hint">No activity yet.</p>
        ) : (
          <div className="bar-list">
            {analytics.per_engineer.map((e) => (
              <div key={e.username} className="bar-row">
                <span className="bar-label">{e.username}</span>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{ width: `${(e.questions / maxEngineerQuestions) * 100}%` }}
                  />
                </div>
                <span className="bar-count">{e.questions}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

export default AdminOverviewTab;