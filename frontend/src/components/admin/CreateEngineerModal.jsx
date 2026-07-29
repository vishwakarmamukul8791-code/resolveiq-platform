// frontend/src/components/admin/CreateEngineerModal.jsx

import { useState } from "react";
import { adminApi, ApiError } from "../../api/client";
import "../../styles/modal.css";
import "../../styles/admin-modals.css";

function CreateEngineerModal({ onClose, onCreated }) {
  const [username, setUsername] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = username.trim();
    if (!trimmed) {
      setError("Enter a username.");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      const data = await adminApi.createEngineer(trimmed);
      onCreated(data); // { username, temp_password, message }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create engineer.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-shell" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>Create engineer account</h3>
            <span>They'll set a real password on first login.</span>
          </div>

          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <form className="modal-body" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="new-username">Username</label>
            <input
              id="new-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isSubmitting}
              autoFocus
              autoComplete="off"
            />
          </div>

          {error && <div className="field-error">{error}</div>}

          <button type="submit" className="modal-submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating…" : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default CreateEngineerModal;