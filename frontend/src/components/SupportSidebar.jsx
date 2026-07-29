// frontend/src/components/SupportSidebar.jsx

import { useEffect, useState, useCallback } from "react";
import { historyApi, ApiError } from "../api/client";
import { formatRelativeTime } from "../utils/formatTime";
import brandMark from "../assets/resolveiq-mark.png";

function StarIcon({ filled }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path
        d="M12 2.5l2.9 6.1 6.6.8-4.9 4.5 1.3 6.6L12 17.3l-5.9 3.2 1.3-6.6-4.9-4.5 6.6-.8z"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 6h16M9 6V4h6v2m-8 0 1 14h8l1-14" />
    </svg>
  );
}

function HistoryItem({ entry, isActive, onSelect, onTogglePin, onDelete }) {
  return (
    <div className={`history-item ${isActive ? "active" : ""}`}>
      <button type="button" className="history-item-main" onClick={() => onSelect(entry)}>
        <p className="history-item-question">{entry.question}</p>
        <span className="history-item-time">{formatRelativeTime(entry.created_at)}</span>
      </button>

      <div className="history-item-actions">
        <button
          type="button"
          className={`icon-button ${entry.pinned ? "pinned" : ""}`}
          onClick={() => onTogglePin(entry)}
          aria-label={entry.pinned ? "Unpin" : "Pin"}
          title={entry.pinned ? "Unpin" : "Pin"}
        >
          <StarIcon filled={entry.pinned} />
        </button>

        <button
          type="button"
          className="icon-button danger"
          onClick={() => onDelete(entry)}
          aria-label="Delete"
          title="Delete"
        >
          <TrashIcon />
        </button>
      </div>
    </div>
  );
}

function SupportSidebar({
  sidebarOpen,
  setSidebarOpen,
  activeEntryId,
  onNewInvestigation,
  onSelectEntry,
  refreshKey,
}) {
  const [history, setHistory] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [error, setError] = useState(null);

  const loadHistory = useCallback(() => {
    setStatus("loading");
    historyApi
      .list()
      .then((data) => {
        setHistory(data.history ?? []);
        setStatus("ready");
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Could not load history.");
        setStatus("error");
      });
  }, []);

  useEffect(() => {
    loadHistory();
    // refreshKey is bumped by the parent every time a new question is
    // successfully answered, so a fresh entry shows up here without a
    // manual page refresh.
  }, [loadHistory, refreshKey]);

  async function handleTogglePin(entry) {
    try {
      const result = await historyApi.pin(entry.id);
      setHistory((prev) =>
        prev.map((h) => (h.id === entry.id ? { ...h, pinned: result.pinned } : h))
      );
    } catch {
      // Non-critical — leave the list as-is, the star just won't flip.
    }
  }

  async function handleDelete(entry) {
    if (!window.confirm("Delete this investigation from your history?")) return;

    try {
      await historyApi.deleteOne(entry.id);
      setHistory((prev) => prev.filter((h) => h.id !== entry.id));
    } catch {
      // Non-critical — leave the list as-is on failure.
    }
  }

  const pinned = history.filter((h) => h.pinned);
  const recent = history.filter((h) => !h.pinned);

  return (
    <aside className="support-sidebar">
      <div className="sidebar-top">
        {sidebarOpen && (
          <div className="sidebar-brand">
            <img src={brandMark} alt="ResolveIQ" className="sidebar-mark" />

            <div className="sidebar-brand-text">
              <strong>ResolveIQ</strong>
              <span>Support Workspace</span>
            </div>
          </div>
        )}

        <button
          type="button"
          className="sidebar-toggle"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
        >
          {sidebarOpen ? "‹" : "›"}
        </button>
      </div>

      {sidebarOpen && (
        <div className="sidebar-section">
          <span className="sidebar-label">INVESTIGATIONS</span>

          <button
            type="button"
            className={`sidebar-item new-investigation ${!activeEntryId ? "active" : ""}`}
            onClick={onNewInvestigation}
          >
            <span>＋</span>
            <p>New Investigation</p>
          </button>

          {status === "loading" && <p className="sidebar-hint">Loading…</p>}

          {status === "error" && <p className="sidebar-hint error">{error}</p>}

          {status === "ready" && history.length === 0 && (
            <p className="sidebar-hint">No investigations yet — ask something to get started.</p>
          )}

          {status === "ready" && pinned.length > 0 && (
            <>
              <span className="sidebar-sublabel">PINNED</span>
              <div className="history-list">
                {pinned.map((entry) => (
                  <HistoryItem
                    key={entry.id}
                    entry={entry}
                    isActive={entry.id === activeEntryId}
                    onSelect={onSelectEntry}
                    onTogglePin={handleTogglePin}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            </>
          )}

          {status === "ready" && recent.length > 0 && (
            <>
              <span className="sidebar-sublabel">RECENT</span>
              <div className="history-list">
                {recent.map((entry) => (
                  <HistoryItem
                    key={entry.id}
                    entry={entry}
                    isActive={entry.id === activeEntryId}
                    onSelect={onSelectEntry}
                    onTogglePin={handleTogglePin}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </aside>
  );
}

export default SupportSidebar;