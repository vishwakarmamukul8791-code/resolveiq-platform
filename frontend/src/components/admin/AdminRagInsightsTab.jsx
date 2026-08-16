// frontend/src/components/admin/AdminRagInsightsTab.jsx

import { useEffect, useState } from "react";
import { adminApi, ApiError } from "../../api/client";

const RETRIEVAL_EVALUATION = [
  { label: "SEMANTIC HIT@1", value: "90.5%", note: "Offline retrieval evaluation" },
  { label: "BM25 HIT@1", value: "85.7%", note: "Offline retrieval evaluation" },
  { label: "HYBRID HIT@1", value: "90.5%", note: "BM25 + vector + RRF" },
  { label: "HYBRID HIT@5", value: "100%", note: "Relevant result within top five" },
];

function AdminRagInsightsTab() {
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    Promise.all([
      adminApi.getKnowledgeGaps(),
      adminApi.getSourceAnalytics(),
      adminApi.getSystemHealth(),
    ])
      .then(([gaps, sources, systemHealth]) => {
        setState({
          status: "ready",
          gaps,
          sources,
          stats: systemHealth.stats,
        });
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

  const { gaps, sources, stats } = state;
  const maxCitations = Math.max(1, ...sources.sources.map((s) => s.citations), 1);

  const pipeline = [
    {
      step: "01",
      title: "Question validation",
      detail: "Reject malformed or multi-question requests before retrieval.",
    },
    {
      step: "02",
      title: "Configurable query rewrite",
      detail: stats.query_rewrite_enabled
        ? "Enabled in this runtime; safe fallback keeps the original query."
        : "Disabled in this runtime; retrieval uses the original query.",
    },
    {
      step: "03",
      title: "BM25 + vector retrieval",
      detail: "Lexical and semantic search retrieve complementary evidence.",
    },
    {
      step: "04",
      title: "Reciprocal Rank Fusion",
      detail: "RRF combines lexical and semantic rankings.",
    },
    {
      step: "05",
      title: "Optional cross-encoder rerank",
      detail: stats.reranker_enabled
        ? "Enabled in this runtime."
        : "Disabled in this runtime; fused ranking is used directly.",
    },
    {
      step: "06",
      title: "Confidence gate",
      detail: "Weak or out-of-domain evidence is stopped before generation.",
    },
    {
      step: "07",
      title: "Grounded Gemini answer",
      detail: "Generation is constrained to accepted retrieved context.",
    },
    {
      step: "08",
      title: "Citations / safe abstention",
      detail: "Return supporting sources or abstain when evidence is insufficient.",
    },
  ];

  return (
    <>
      <div className="panel-heading">
        <div>
          <span className="section-label">LIVE OPERATIONAL ANALYTICS</span>
          <h2>Current authenticated workspace activity</h2>
        </div>
      </div>

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

      <section className="admin-panel rag-evaluation-panel">
        <div className="panel-heading">
          <div>
            <span className="section-label">RETRIEVAL EVALUATION</span>
            <h2>Measured retrieval quality</h2>
          </div>

          <span className="rag-snapshot-badge">DOCUMENTED SNAPSHOT</span>
        </div>

        <p className="admin-hint">
          Offline benchmark snapshot kept separate from the live operational analytics above.
        </p>

        <div className="rag-eval-grid">
          {RETRIEVAL_EVALUATION.map((metric) => (
            <div key={metric.label} className="rag-eval-card">
              <span>{metric.label}</span>
              <strong>{metric.value}</strong>
              <p>{metric.note}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="admin-panel">
        <div className="panel-heading">
          <div>
            <span className="section-label">RAG PIPELINE</span>
            <h2>Retrieval first, generation only after evidence passes</h2>
          </div>
        </div>

        <div className="rag-pipeline-grid">
          {pipeline.map((stage) => (
            <div key={stage.step} className="rag-pipeline-step">
              <span className="rag-pipeline-number">{stage.step}</span>
              <div>
                <strong>{stage.title}</strong>
                <p>{stage.detail}</p>
              </div>
            </div>
          ))}
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
