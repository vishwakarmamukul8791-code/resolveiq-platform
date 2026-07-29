// frontend/src/components/SourceViewerModal.jsx
//
// Opened when someone clicks a source under an answer. Fetches the full
// document via GET /document/{name} (already returns every chunk's text
// plus page_number/source_location — no backend change was needed for
// this) and shows the chunk(s) matching the source's page/location, so
// the person can see exactly where in the document the answer came from.

import { useEffect, useState } from "react";
import { documentsApi, ApiError } from "../api/client";
import "../styles/modal.css";
import "../styles/source-viewer.css";

function findRelevantChunks(chunks, pageNumber, sourceLocation) {
  if (pageNumber != null) {
    const matched = chunks.filter((c) => c.page_number === pageNumber);
    if (matched.length > 0) return { chunks: matched, matchType: "page" };
  }
  if (sourceLocation) {
    const matched = chunks.filter((c) => c.source_location === sourceLocation);
    if (matched.length > 0) return { chunks: matched, matchType: "location" };
  }
  return { chunks, matchType: "all" };
}

function SourceViewerModal({ source, onClose }) {
  const [state, setState] = useState({ status: "loading", chunks: [], matchType: null, error: null });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading", chunks: [], matchType: null, error: null });

    documentsApi
      .getDetails(source.document_name)
      .then((data) => {
        if (cancelled) return;
        const { chunks, matchType } = findRelevantChunks(
          data.chunks ?? [],
          source.page_number,
          source.source_location
        );
        setState({ status: "ready", chunks, matchType, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        setState({
          status: "error",
          chunks: [],
          matchType: null,
          error: err instanceof ApiError ? err.message : "Could not load this document.",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [source]);

  useEffect(() => {
    function handleKey(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-shell" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>{source.document_name}</h3>
            <span>
              {source.page_number != null
                ? `Page ${source.page_number}`
                : source.source_location || "Full document"}
            </span>
          </div>

          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="modal-body">
          {state.status === "loading" && <p className="source-modal-note">Loading…</p>}

          {state.status === "error" && (
            <p className="source-modal-note error">{state.error}</p>
          )}

          {state.status === "ready" && (
            <>
              {state.matchType === "all" && (
                <p className="source-modal-note">
                  No page number was recorded for this source — showing the full document.
                </p>
              )}

              {state.chunks.map((chunk) => (
                <p key={chunk.chunk_id} className="source-chunk">
                  {chunk.chunk}
                </p>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default SourceViewerModal;