// frontend/src/components/admin/AdminRagInsightsTab.jsx

import { useEffect, useState } from "react";
import { adminApi, ApiError } from "../../api/client";

function AdminRagInsightsTab() {
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    Promise.all([adminApi.getKnowledgeGaps(), adminApi.getSourceAnalytics()])
      .then(([gaps, sources]) => {
        setState({ status: "ready", gaps, sources });
      })
      .catch((err) => {
        setState({
          status: "error",
          error: err instanceof ApiError ? err.message : "Could not load RAG insights.",
        });
      });
  }, []);

  if (state.status === "loading") {
    return (
      <div className="admin-panel">
        <p className="admin-hint">Loading insights…</p>
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

  const { gaps, sources } = state;
  const maxCitations = Math.max(1, ...sources.sources.map((s) => s.citations), 1);

  return (
    <>
      <section className="admin-kpi-grid">
        <div className="admin-kpi-card">
          <span>TOTAL QUESTIONS</span>
          <strong>{gaps.total_questions}</strong>
          <p>Engineer-authored, all time</p>
        </div>

        <div className="admin-kpi-card">
          <span>LOW-CONFIDENCE QUESTIONS</span>
          <strong>{gaps.total_unanswered}</strong>
          <p>Couldn't be confidently answered</p>
        </div>

        <div className="admin-kpi-card">
          <span>UNANSWERED RATE</span>
          <strong>{gaps.unanswered_rate}%</strong>
          <p>Share of all questions</p>
        </div>

        <div className="admin-kpi-card">
          <span>TOTAL CITATIONS</span>
          <strong>{sources.total_citations}</strong>
          <p>Across High/Medium confidence answers</p>
        </div>
      </section>

      <section className="admin-panel">
        <div className="panel-heading">
          <div>
            <span className="section-label">KNOWLEDGE GAPS</span>
            <h2>Questions the system couldn't answer</h2>
          </div>
        </div>

        {gaps.top_gaps.length === 0 ? (
          <p className="admin-hint">No low-confidence questions yet — good sign.</p>
        ) : (
          <>
            <p className="admin-hint">
              Grouped by exact question text — questions repeated here are strong candidates for
              new documentation.
            </p>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>QUESTION</th>
                    <th>TIMES ASKED</th>
                  </tr>
                </thead>
                <tbody>
                  {gaps.top_gaps.map((gap, i) => (
                    <tr key={i}>
                      <td className="gap-question">{gap.question}</td>
                      <td className="question-count">{gap.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section className="admin-panel">
        <div className="panel-heading">
          <div>
            <span className="section-label">SOURCE ANALYTICS</span>
            <h2>Most-cited documents</h2>
          </div>
        </div>

        {sources.sources.length === 0 ? (
          <p className="admin-hint">No citations yet.</p>
        ) : (
          <div className="bar-list">
            {sources.sources.map((s) => (
              <div key={s.document_name} className="bar-row">
                <span className="bar-label" title={s.document_name}>
                  {s.document_name}
                </span>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{ width: `${(s.citations / maxCitations) * 100}%` }}
                  />
                </div>
                <span className="bar-count">
                  {s.citations} ({s.citation_pct}%)
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

export default AdminRagInsightsTab;