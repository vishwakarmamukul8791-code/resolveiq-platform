// frontend/src/components/IncidentWorkspace.jsx

import { useState, useRef, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { askApi, documentsApi, ApiError } from "../api/client";
import SourceViewerModal from "./SourceViewerModal";
import "../styles/incident-workspace.css";

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M3.4 20.6 21 12 3.4 3.4 3 10l13 2-13 2z" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" className="spin">
      <circle
        cx="12"
        cy="12"
        r="9"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray="40 20"
      />
    </svg>
  );
}

function ConfidenceBadge({ level }) {
  const cls =
    level === "High"
      ? "confidence-high"
      : level === "Medium"
      ? "confidence-medium"
      : "confidence-low";

  return <span className={`confidence-badge ${cls}`}>{level} confidence</span>;
}

function ExchangeCard({ exchange, onViewSource }) {
  const [showDetails, setShowDetails] = useState(false);

  if (exchange.pending) {
    return (
      <div className="exchange">
        <div className="exchange-question">{exchange.question}</div>
        <div className="exchange-answer pending">
          <span className="thinking-dot" />
          <span className="thinking-dot" />
          <span className="thinking-dot" />
        </div>
      </div>
    );
  }

  const hasSources = exchange.sources && exchange.sources.length > 0;
  const searchedDifferently =
    exchange.rewrittenQuery && exchange.rewrittenQuery !== exchange.question;

  return (
    <div className="exchange">
      <div className="exchange-question">{exchange.question}</div>

      <div className="exchange-answer">
        <div className="answer-meta">
          <ConfidenceBadge level={exchange.confidence} />

          {(hasSources || searchedDifferently || exchange.topScore != null) && (
            <button
              type="button"
              className="details-toggle"
              onClick={() => setShowDetails((s) => !s)}
            >
              {showDetails
                ? "Hide details"
                : hasSources
                ? `${exchange.sources.length} source${exchange.sources.length === 1 ? "" : "s"}`
                : "Retrieval details"}
            </button>
          )}
        </div>

        <p className="answer-text">{exchange.answer}</p>

        {showDetails && (
          <div className="answer-details">
            {searchedDifferently && (
              <p className="detail-line">
                <strong>Searched as:</strong> {exchange.rewrittenQuery}
              </p>
            )}

            {hasSources && (
              <ul className="source-list">
                {exchange.sources.map((src, i) => (
                  <li key={i}>
                    <button
                      type="button"
                      className="source-link"
                      onClick={() => onViewSource(src)}
                    >
                      {src.document_name}
                      {src.page_number != null && ` — p.${src.page_number}`}
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {exchange.topScore != null && (
              <p className="detail-line muted">
                Top relevance score: {exchange.topScore} · {exchange.supportingChunks}{" "}
                supporting chunk{exchange.supportingChunks === 1 ? "" : "s"}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function IncidentWorkspace({ resetToken, loadedEntry, onAsked }) {
  const { sessionId } = useAuth();

  const [documents, setDocuments] = useState([]);
  const [documentFilter, setDocumentFilter] = useState(""); // "" = search all documents

  const [query, setQuery] = useState("");
  const [exchanges, setExchanges] = useState([]);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState(null);
  const [viewingSource, setViewingSource] = useState(null);

  const textareaRef = useRef(null);
  const threadEndRef = useRef(null);

  // Populate the document-scope filter. Not critical to the page working —
  // a failed fetch here just leaves the filter as "All documents".
  useEffect(() => {
    documentsApi
      .list()
      .then((data) => setDocuments(data.documents ?? []))
      .catch(() => {});
  }, []);

  // "New Investigation" in the sidebar bumps resetToken — clear the thread.
  useEffect(() => {
    if (resetToken === undefined) return;
    setExchanges([]);
    setQuery("");
    setError(null);
  }, [resetToken]);

  // Selecting a past investigation from the sidebar loads it as a
  // read-only single-exchange thread. History only ever stores source
  // *names* (see history_service.py), not page numbers — that detail
  // only exists on a fresh /ask response — so it's normalized into the
  // same {document_name, page_number, source_location} shape ExchangeCard
  // expects, with page_number/source_location left null. The source
  // viewer already handles a null page_number by falling back to showing
  // the whole document.
  useEffect(() => {
    if (!loadedEntry) return;
    setExchanges([
      {
        id: loadedEntry.id,
        question: loadedEntry.question,
        pending: false,
        answer: loadedEntry.answer,
        confidence: loadedEntry.confidence,
        sources: (loadedEntry.sources ?? []).map((name) => ({
          document_name: name,
          page_number: null,
          source_location: null,
        })),
        rewrittenQuery: loadedEntry.rewritten_query,
        topScore: null,
        supportingChunks: null,
      },
    ]);
    setError(null);
  }, [loadedEntry]);

  // Auto-grow the textarea with content instead of scrolling inside a
  // fixed-height box (same pattern as ChatGPT's composer).
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [query]);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [exchanges]);

  const hasStarted = exchanges.length > 0;

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || isAsking) return;

    setError(null);
    const pendingId = crypto.randomUUID();

    setExchanges((prev) => [...prev, { id: pendingId, question: trimmed, pending: true }]);
    setQuery("");
    setIsAsking(true);

    try {
      const data = await askApi.ask(trimmed, {
        documentName: documentFilter || undefined,
        sessionId,
      });

      setExchanges((prev) =>
        prev.map((ex) =>
          ex.id === pendingId
            ? {
                ...ex,
                pending: false,
                answer: data.answer,
                confidence: data.confidence,
                sources: data.sources,
                rewrittenQuery: data.rewritten_query,
                topScore: data.top_relevance_score,
                supportingChunks: data.supporting_chunks,
              }
            : ex
        )
      );

      // The backend already persisted this to history — let the sidebar
      // know so its list refetches and shows the new entry immediately.
      onAsked?.();
    } catch (err) {
      // Drop the pending bubble and put the question back in the box so
      // nothing is lost — retry is just hitting send again.
      setExchanges((prev) => prev.filter((ex) => ex.id !== pendingId));
      setQuery(trimmed);
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setIsAsking(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <section className={`incident-workspace ${hasStarted ? "workspace-active" : "workspace-empty"}`}>
      {!hasStarted && (
        <div className="workspace-intro">
          <h1>What incident are you investigating?</h1>
          <p>Ask about an error code, a symptom, or paste details from a ticket.</p>
        </div>
      )}

      {hasStarted && (
        <div className="workspace-thread">
          {exchanges.map((ex) => (
            <ExchangeCard key={ex.id} exchange={ex} onViewSource={setViewingSource} />
          ))}
          <div ref={threadEndRef} />
        </div>
      )}

      <div className="composer-area">
        {error && <div className="composer-error">{error}</div>}

        <form className="incident-chat-box" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            rows={1}
            placeholder="Describe the incident or paste an error message…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isAsking}
            aria-label="Describe the incident"
          />

          <div className="chat-input-footer">
            <select
              className="document-filter"
              value={documentFilter}
              onChange={(e) => setDocumentFilter(e.target.value)}
              disabled={isAsking}
              aria-label="Limit search to a document"
            >
              <option value="">All documents</option>
              {documents.map((doc) => (
                <option key={doc.document_name} value={doc.document_name}>
                  {doc.document_name}
                </option>
              ))}
            </select>

            <button
              type="submit"
              className="send-button"
              disabled={isAsking || !query.trim()}
              aria-label="Ask"
            >
              {isAsking ? <SpinnerIcon /> : <SendIcon />}
            </button>
          </div>
        </form>

        {documents.length > 0 && (
          <p className="composer-hint">
            {documents.length} document{documents.length === 1 ? "" : "s"} indexed
          </p>
        )}
      </div>

      {viewingSource && (
        <SourceViewerModal source={viewingSource} onClose={() => setViewingSource(null)} />
      )}
    </section>
  );
}

export default IncidentWorkspace;