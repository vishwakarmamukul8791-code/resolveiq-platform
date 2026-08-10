// frontend/src/components/GuestWorkspace.jsx
//
// A stripped-down version of IncidentWorkspace for people trying the
// product without logging in (e.g. from a "Try without login" link on
// the landing page). No auth, no history, no document filter — just
// ask a question against the public demo documents the backend has
// allow-listed for guest access (see backend/routes/guest.py).

import { useState, useRef, useEffect } from "react";
import { guestApi, ApiError } from "../api/client";
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

  return (
    <div className="exchange">
      <div className="exchange-question">{exchange.question}</div>

      <div className="exchange-answer">
        <div className="answer-meta">
          <ConfidenceBadge level={exchange.confidence} />

          {hasSources && (
            <button
              type="button"
              className="details-toggle"
              onClick={() => setShowDetails((s) => !s)}
            >
              {showDetails
                ? "Hide details"
                : `${exchange.sources.length} source${exchange.sources.length === 1 ? "" : "s"}`}
            </button>
          )}
        </div>

        <p className="answer-text">{exchange.answer}</p>

        {showDetails && hasSources && (
          <div className="answer-details">
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
          </div>
        )}
      </div>
    </div>
  );
}

const GUEST_QUESTION_LIMIT = 5;

// Picked directly from the actual demo knowledge base (INC-1009 to
// INC-1020) — each one uses specific terms that appear verbatim in a
// chunk (strong BM25 match) while also being a clear, natural question
// (strong semantic match), so both retrievers agree and this reliably
// produces High confidence for a first-time visitor instead of them
// having to guess what's in the demo documents.
const EXAMPLE_QUESTIONS = [
  "Why am I seeing ORA-12154 TNS could not resolve the connect identifier?",
  "How do I fix a Kubernetes pod stuck in CrashLoopBackOff?",
  "We're getting HTTP 502 Bad Gateway errors during peak traffic — what's the cause?",
  "Login is failing with an invalid_grant OAuth error — why?",
];

function GuestWorkspace() {
  const [query, setQuery] = useState("");
  const [exchanges, setExchanges] = useState([]);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState(null);
  const [viewingSource, setViewingSource] = useState(null);

  const textareaRef = useRef(null);
  const threadEndRef = useRef(null);

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
  const askedCount = exchanges.filter((ex) => !ex.pending).length;
  const reachedLimit = askedCount >= GUEST_QUESTION_LIMIT;

  async function askQuestion(text) {
    const trimmed = text.trim();
    if (!trimmed || isAsking || reachedLimit) return;

    setError(null);
    const pendingId = crypto.randomUUID();

    setExchanges((prev) => [...prev, { id: pendingId, question: trimmed, pending: true }]);
    setQuery("");
    setIsAsking(true);

    try {
      const data = await guestApi.ask(trimmed);

      setExchanges((prev) =>
        prev.map((ex) =>
          ex.id === pendingId
            ? {
                ...ex,
                pending: false,
                answer: data.answer,
                confidence: data.confidence,
                sources: data.sources,
              }
            : ex
        )
      );
    } catch (err) {
      setExchanges((prev) => prev.filter((ex) => ex.id !== pendingId));
      setQuery(trimmed);
      setError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong. Try again."
      );
    } finally {
      setIsAsking(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    askQuestion(query);
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
          <h1>Try ResolveIQ — no login needed</h1>
          <p>
            Ask a question against a public demo knowledge base. Limited to
            {" "}{GUEST_QUESTION_LIMIT} questions per visit — log in for full
            access, or run your own instance to try everything.
          </p>

          <div className="guest-suggestions">
            {EXAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                type="button"
                className="guest-suggestion-chip"
                onClick={() => askQuestion(q)}
                disabled={isAsking || reachedLimit}
              >
                {q}
              </button>
            ))}
          </div>
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

        {reachedLimit && (
          <div className="composer-error">
            You've reached the guest question limit for this visit. Log in
            if you have credentials, or run your own instance to keep
            exploring.
          </div>
        )}

        <form className="incident-chat-box" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            rows={1}
            placeholder="Describe the incident or paste an error message…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isAsking || reachedLimit}
            aria-label="Describe the incident"
          />

          <div className="chat-input-footer">
            <span className="composer-hint">
              {askedCount}/{GUEST_QUESTION_LIMIT} guest questions used
            </span>

            <button
              type="submit"
              className="send-button"
              disabled={isAsking || reachedLimit || !query.trim()}
              aria-label="Ask"
            >
              {isAsking ? <SpinnerIcon /> : <SendIcon />}
            </button>
          </div>
        </form>
      </div>

      {viewingSource && (
        <SourceViewerModal source={viewingSource} onClose={() => setViewingSource(null)} />
      )}
    </section>
  );
}

export default GuestWorkspace;
