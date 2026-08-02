// frontend/src/components/HelpModal.jsx
//
// Real onboarding content for a new support engineer, not a placeholder.
// Reuses the same modal shell as SourceViewerModal.

import { useEffect } from "react";
import "../styles/modal.css";
import "../styles/help-modal.css";

function HelpModal({ onClose }) {
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
            <h3>Using the workspace</h3>
            <span>A quick guide for support engineers</span>
          </div>

          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="modal-body help-body">
          <section>
            <h4>Ask a question</h4>
            <p>
              Describe one incident question or paste one error message in the box below. Press
              Enter to send, or Shift+Enter to start a new line first. Ask independent questions
              separately so each answer gets its own retrieval and confidence decision.
            </p>
          </section>

          <section>
            <h4>Confidence levels</h4>
            <ul>
              <li>
                <strong>High</strong> — retrieval found strong supporting document chunks. Verify
                the cited source before making a production change.
              </li>
              <li>
                <strong>Medium</strong> — a partial match was found. Worth a quick check against
                the source before you act on it.
              </li>
              <li>
                <strong>Low</strong> — nothing relevant enough was found. The system is telling
                you it doesn't know, rather than guessing. Try rephrasing, or check the document
                filter below isn't scoped too narrowly.
              </li>
            </ul>
          </section>

          <section>
            <h4>Scoping to one document</h4>
            <p>
              The document dropdown next to the send button limits your search to a single file.
              If your question isn't actually covered by that document, you'll correctly get a
              Low-confidence result — that's expected behavior, not a bug. Switch back to "All
              documents," or pick the right one, and try again.
            </p>
          </section>

          <section>
            <h4>Sources</h4>
            <p>
              Every answer lists which documents it drew from. Click a source to open the exact
              page it came from and verify it yourself.
            </p>
          </section>

          <section>
            <h4>Sidebar</h4>
            <p>
              "New Investigation" starts a fresh thread. Past questions appear under Recent —
              star one to pin it, or delete the ones you don't need anymore.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

export default HelpModal;
