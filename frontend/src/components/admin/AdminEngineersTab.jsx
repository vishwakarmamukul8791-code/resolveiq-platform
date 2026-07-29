// frontend/src/components/admin/AdminEngineersTab.jsx

import { useEffect, useMemo, useState, useCallback } from "react";
import * as XLSX from "xlsx";
import { adminApi, ApiError } from "../../api/client";
import { formatRelativeTime, formatDuration } from "../../utils/formatTime";
import CreateEngineerModal from "./CreateEngineerModal";
import TempPasswordModal from "./TempPasswordModal";
import "../../styles/admin-modals.css";

function AdminEngineersTab() {
  const [engineers, setEngineers] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);

  const [search, setSearch] = useState("");
  const [pendingUsername, setPendingUsername] = useState(null);
  const [actionError, setActionError] = useState(null);

  const [showCreate, setShowCreate] = useState(false);
  const [tempPasswordInfo, setTempPasswordInfo] = useState(null);

  const loadEngineers = useCallback(() => {
    setStatus("loading");
    adminApi
      .listEngineers()
      .then((data) => {
        setEngineers(data.engineers ?? []);
        setStatus("ready");
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Could not load engineers.");
        setStatus("error");
      });
  }, []);

  useEffect(() => {
    loadEngineers();
  }, [loadEngineers]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return engineers;
    return engineers.filter((e) => e.username.toLowerCase().includes(q));
  }, [engineers, search]);

  async function handleToggleActive(engineer) {
    setActionError(null);
    setPendingUsername(engineer.username);
    try {
      const result = await adminApi.setActive(engineer.username, !engineer.is_active);
      setEngineers((prev) =>
        prev.map((e) =>
          e.username === engineer.username ? { ...e, is_active: result.is_active } : e
        )
      );
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Could not update account status.");
    } finally {
      setPendingUsername(null);
    }
  }

  async function handleResetPassword(engineer) {
    if (
      !window.confirm(
        `Reset ${engineer.username}'s password? They'll need to set a new one at next login.`
      )
    ) {
      return;
    }

    setActionError(null);
    setPendingUsername(engineer.username);
    try {
      const result = await adminApi.resetEngineerPassword(engineer.username);
      setEngineers((prev) =>
        prev.map((e) =>
          e.username === engineer.username ? { ...e, must_reset_password: true } : e
        )
      );
      setTempPasswordInfo(result);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Could not reset password.");
    } finally {
      setPendingUsername(null);
    }
  }

  function handleCreated(result) {
    setShowCreate(false);
    setTempPasswordInfo(result);
    loadEngineers();
  }

  function handleExport() {
    const rows = engineers.map((e) => ({
      Username: e.username,
      Status: e.is_active ? "Active" : "Inactive",
      "Must Reset Password": e.must_reset_password ? "Yes" : "No",
      "Total Sessions": e.total_sessions,
      "Total Questions": e.total_questions,
      "High Confidence": e.high_confidence,
      "Medium Confidence": e.medium_confidence,
      "Low Confidence": e.low_confidence,
      "Total Minutes": e.total_minutes,
      "Last Login": e.last_login ?? "Never",
      "Created At": e.created_at,
    }));

    const worksheet = XLSX.utils.json_to_sheet(rows);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Engineers");
    XLSX.writeFile(workbook, `resolveiq-engineers-${new Date().toISOString().slice(0, 10)}.xlsx`);
  }

  if (status === "loading") {
    return (
      <div className="admin-panel">
        <p className="admin-hint">Loading engineers…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="admin-panel">
        <p className="admin-hint error">{error}</p>
      </div>
    );
  }

  return (
    <section className="admin-panel employee-panel">
      <div className="panel-heading">
        <div>
          <span className="section-label">ENGINEERS</span>
          <h2>Support engineer accounts</h2>
        </div>

        <div className="panel-actions">
          <button type="button" className="export-button secondary" onClick={() => setShowCreate(true)}>
            + Add Engineer
          </button>

          <button
            type="button"
            className="export-button"
            onClick={handleExport}
            disabled={engineers.length === 0}
          >
            ↓ Export Excel
          </button>
        </div>
      </div>

      {actionError && <p className="admin-hint error">{actionError}</p>}

      <div className="table-toolbar">
        <input
          type="text"
          placeholder="Search by username..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <span>
          Showing {filtered.length} of {engineers.length} engineers
        </span>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ENGINEER</th>
              <th>STATUS</th>
              <th>SESSIONS</th>
              <th>QUESTIONS</th>
              <th>HIGH-CONF RATE</th>
              <th>TOTAL TIME</th>
              <th>LAST LOGIN</th>
              <th>ACTIONS</th>
            </tr>
          </thead>

          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="empty-row">
                  {engineers.length === 0 ? "No engineer accounts yet." : "No matches."}
                </td>
              </tr>
            )}

            {filtered.map((e) => {
              const highRate =
                e.total_questions > 0
                  ? `${Math.round((e.high_confidence / e.total_questions) * 100)}%`
                  : "—";
              const isPending = pendingUsername === e.username;

              return (
                <tr key={e.username}>
                  <td>
                    <div className="employee-name">
                      <div className="employee-avatar">{e.username.charAt(0).toUpperCase()}</div>
                      <div>
                        <strong>{e.username}</strong>
                        {e.must_reset_password && (
                          <span className="must-reset-tag">Must reset password</span>
                        )}
                      </div>
                    </div>
                  </td>

                  <td>
                    <span className={`status ${e.is_active ? "active" : "completed"}`}>
                      {e.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>

                  <td>{e.total_sessions}</td>
                  <td className="question-count">{e.total_questions}</td>
                  <td>{highRate}</td>
                  <td>{formatDuration(e.total_minutes)}</td>
                  <td>{e.last_login ? formatRelativeTime(e.last_login) : "Never"}</td>

                  <td>
                    <div className="row-actions">
                      <button
                        type="button"
                        className="row-action"
                        onClick={() => handleToggleActive(e)}
                        disabled={isPending}
                      >
                        {e.is_active ? "Disable" : "Enable"}
                      </button>

                      <button
                        type="button"
                        className="row-action"
                        onClick={() => handleResetPassword(e)}
                        disabled={isPending}
                      >
                        Reset password
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateEngineerModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}

      {tempPasswordInfo && (
        <TempPasswordModal
          username={tempPasswordInfo.username}
          tempPassword={tempPasswordInfo.temp_password}
          message={tempPasswordInfo.message}
          onClose={() => setTempPasswordInfo(null)}
        />
      )}
    </section>
  );
}

export default AdminEngineersTab;