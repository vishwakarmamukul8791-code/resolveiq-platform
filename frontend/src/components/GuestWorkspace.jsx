// Public support-engineer demo.
// - Demo KB mode uses the real allow-listed guest hybrid RAG endpoint.
// - Own TXT mode is a bounded, non-persistent sandbox for one visitor file.

import { useEffect, useRef, useState } from "react";
import { guestApi, ApiError } from "../api/client";
import { askUploadedText, CustomGuestError } from "../api/customGuestClient";
import SourceViewerModal from "./SourceViewerModal";
import "../styles/incident-workspace.css";
import "../styles/demo-explorer.css";
import "../styles/custom-text-demo.css";

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

function cleanAnswerText(value = "") {
  return value
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/â€”/g, "—");
}

function ConfidenceBadge({ level, customContext = false }) {
  if (customContext && level === "Grounded") {
    return <span className="confidence-badge confidence-high">Grounded in uploaded TXT</span>;
  }

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
          <ConfidenceBadge
            level={exchange.confidence}
            customContext={exchange.customContext}
          />

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

        <p className="answer-text">{cleanAnswerText(exchange.answer)}</p>

        {showDetails && hasSources && (
          <div className="answer-details">
            <ul className="source-list">
              {exchange.sources.map((src, i) => (
                <li key={`${src.document_name}-${src.chunk_index ?? i}`}>
                  {exchange.customContext ? (
                    <span className="custom-source-label">
                      {src.document_name}
                      {src.chunk_index != null && ` — retrieved chunk ${src.chunk_index}`}
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="source-link"
                      onClick={() => onViewSource(src)}
                    >
                      {src.document_name}
                      {src.page_number != null && ` — p.${src.page_number}`}
                    </button>
                  )}
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
const MAX_TXT_BYTES = 20_000;

const EXAMPLE_QUESTIONS = [
  "Why am I seeing ORA-12154 TNS could not resolve the connect identifier?",
  "How do I fix a Kubernetes pod stuck in CrashLoopBackOff?",
  "We're getting HTTP 502 Bad Gateway errors during peak traffic — what's the cause?",
  "Login is failing with an invalid_grant OAuth error — why?",
];

function GuestWorkspace() {
  const [mode, setMode] = useState("demo");
  const [query, setQuery] = useState("");
  const [exchanges, setExchanges] = useState([]);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState(null);
  const [viewingSource, setViewingSource] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [usedCount, setUsedCount] = useState(0);

  const textareaRef = useRef(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [query]);

  const hasStarted = exchanges.length > 0;
  const askedCount = usedCount;
  const reachedLimit = usedCount >= GUEST_QUESTION_LIMIT;
  const uploadReady = mode === "upload" && uploadedFile?.text;

  function switchMode(nextMode) {
    if (nextMode === mode) return;
    setMode(nextMode);
    setQuery("");
    setExchanges([]);
    setError(null);
    setViewingSource(null);
  }

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    setError(null);
    setExchanges([]);

    if (!file) {
      setUploadedFile(null);
      return;
    }

    if (!file.name.toLowerCase().endsWith(".txt")) {
      setUploadedFile(null);
      setError("Upload a .txt file for the public sandbox.");
      event.target.value = "";
      return;
    }

    if (file.size > MAX_TXT_BYTES) {
      setUploadedFile(null);
      setError("TXT sandbox files are limited to 20 KB.");
      event.target.value = "";
      return;
    }

    const text = await file.text();
    if (text.trim().length < 40) {
      setUploadedFile(null);
      setError("Upload a TXT document with at least 40 characters.");
      event.target.value = "";
      return;
    }

    setUploadedFile({
      name: file.name,
      size: file.size,
      text,
    });
  }

  async function askQuestion(text) {
    const trimmed = text.trim();
    if (!trimmed || isAsking || reachedLimit) return;
    if (mode === "upload" && !uploadReady) {
      setError("Upload a TXT document first.");
      return;
    }

    setError(null);
    const pendingId = crypto.randomUUID();

    setExchanges((prev) => [
      ...prev,
      {
        id: pendingId,
        question: trimmed,
        pending: true,
        customContext: mode === "upload",
      },
    ]);
    setQuery("");
    setIsAsking(true);
    // Count API attempts across both demo-KB and temporary-TXT modes so
    // switching sources cannot reset the visible five-question budget.
    setUsedCount((count) => Math.min(GUEST_QUESTION_LIMIT, count + 1));

    try {
      const data = mode === "upload"
        ? await askUploadedText({
            query: trimmed,
            documentName: uploadedFile.name,
            documentText: uploadedFile.text,
          })
        : await guestApi.ask(trimmed);

      setExchanges((prev) =>
        prev.map((ex) =>
          ex.id === pendingId
            ? {
                ...ex,
                pending: false,
                answer: data.answer,
                confidence: data.confidence,
                sources: data.sources,
                customContext: mode === "upload",
              }
            : ex
        )
      );
    } catch (err) {
      setExchanges((prev) => prev.filter((ex) => ex.id !== pendingId));
      setQuery(trimmed);
      if ((err instanceof ApiError || err instanceof CustomGuestError) && err.status === 429) {
        setUsedCount(GUEST_QUESTION_LIMIT);
      }
      setError(
        err instanceof ApiError || err instanceof CustomGuestError
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
          <h1>Explore the Support Engineer workflow</h1>
          <p>
            Use the public demo knowledge base, or upload one small TXT runbook and ask questions
            against your own temporary context.
          </p>

          <div className="custom-mode-switch" role="tablist" aria-label="Support demo source">
            <button
              type="button"
              className={mode === "demo" ? "active" : ""}
              onClick={() => switchMode("demo")}
            >
              Demo knowledge base
            </button>
            <button
              type="button"
              className={mode === "upload" ? "active" : ""}
              onClick={() => switchMode("upload")}
            >
              Upload your TXT
            </button>
          </div>

          {mode === "demo" ? (
            <>
              <div className="guest-suggestions-label">Recommended questions</div>
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
            </>
          ) : (
            <div className="custom-upload-card">
              <div>
                <strong>Temporary TXT sandbox</strong>
                <p>
                  Public sandbox: TXT only · max 20 KB · processed in memory only. The full authenticated
                  ResolveIQ workflow supports PDF, CSV, and TXT. Sandbox uploads are not added to
                  storage, registry, or the vector index.
                </p>
              </div>

              <label className="custom-upload-button">
                {uploadedFile ? "Replace TXT" : "Choose TXT file"}
                <input
                  type="file"
                  accept=".txt,text/plain"
                  onChange={handleFileChange}
                  disabled={isAsking}
                />
              </label>

              {uploadedFile && (
                <div className="custom-upload-selected">
                  <span>Ready</span>
                  <strong>{uploadedFile.name}</strong>
                  <small>{Math.max(1, Math.round(uploadedFile.size / 1024))} KB · temporary</small>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {hasStarted && (
        <div className="workspace-thread">
          <div className="custom-active-context">
            {mode === "upload"
              ? `Temporary TXT: ${uploadedFile?.name || "uploaded document"}`
              : "Public demo knowledge base"}
          </div>
          {exchanges.map((ex) => (
            <ExchangeCard key={ex.id} exchange={ex} onViewSource={setViewingSource} />
          ))}
        </div>
      )}

      <div className="composer-area">
        {error && <div className="composer-error">{error}</div>}

        {reachedLimit && (
          <div className="composer-error">
            You've reached the 5-question demo limit for this visit.
          </div>
        )}

        <form className="incident-chat-box" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            rows={1}
            placeholder={
              mode === "upload"
                ? uploadedFile
                  ? "Ask a question about your uploaded TXT…"
                  : "Upload a TXT document first…"
                : "Describe the incident or paste an error message…"
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isAsking || reachedLimit || (mode === "upload" && !uploadReady)}
            aria-label="Describe the incident"
          />

          <div className="chat-input-footer">
            <span className="composer-hint">
              {askedCount} / {GUEST_QUESTION_LIMIT} demo questions used
            </span>

            <button
              type="submit"
              className="send-button"
              disabled={
                isAsking ||
                reachedLimit ||
                !query.trim() ||
                (mode === "upload" && !uploadReady)
              }
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
