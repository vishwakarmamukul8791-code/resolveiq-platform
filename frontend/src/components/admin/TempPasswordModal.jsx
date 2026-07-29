// frontend/src/components/admin/TempPasswordModal.jsx
//
// Shown once after creating an engineer or resetting a password — the
// backend never stores or returns the plaintext password again after
// this response, so this is the only chance to see/copy it.

import { useState } from "react";
import "../../styles/modal.css";
import "../../styles/admin-modals.css";

function TempPasswordModal({ username, tempPassword, message, onClose }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(tempPassword);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API unavailable in this context — the password is
      // still visible on screen to copy by hand.
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-shell" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>Temporary password</h3>
            <span>{username}</span>
          </div>

          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="modal-body">
          <p className="temp-password-warning">{message}</p>

          <div className="temp-password-box">
            <code>{tempPassword}</code>
            <button type="button" onClick={handleCopy}>
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TempPasswordModal;