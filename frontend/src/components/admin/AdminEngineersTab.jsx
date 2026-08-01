import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  adminApi,
  ApiError,
} from "../../api/client";

import {
  formatDuration,
  formatRelativeTime,
} from "../../utils/formatTime";

import CreateEngineerModal from "./CreateEngineerModal";
import TempPasswordModal from "./TempPasswordModal";

import "../../styles/admin-modals.css";


function escapeCsvCell(value) {
  const text = String(value ?? "");

  // Prevent spreadsheet formula injection.
  const safeText = /^[\s]*[=+\-@]/.test(text)
    ? `'${text}`
    : text;

  return `"${safeText.replace(/"/g, '""')}"`;
}


function AdminEngineersTab() {
  const [engineers, setEngineers] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);

  const [search, setSearch] = useState("");
  const [pendingUsername, setPendingUsername] =
    useState(null);
  const [actionError, setActionError] =
    useState(null);

  const [showCreate, setShowCreate] =
    useState(false);
  const [tempPasswordInfo, setTempPasswordInfo] =
    useState(null);

  const loadEngineers = useCallback(async () => {
    try {
      const data = await adminApi.listEngineers();

      setEngineers(data.engineers ?? []);
      setError(null);
      setStatus("ready");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not load engineers."
      );

      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void loadEngineers();
  }, [loadEngineers]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return engineers;
    }

    return engineers.filter((engineer) =>
      engineer.username
        .toLowerCase()
        .includes(query)
    );
  }, [engineers, search]);

  async function handleToggleActive(engineer) {
    setActionError(null);
    setPendingUsername(engineer.username);

    try {
      const result = await adminApi.setActive(
        engineer.username,
        !engineer.is_active
      );

      setEngineers((currentEngineers) =>
        currentEngineers.map((current) =>
          current.username === engineer.username
            ? {
                ...current,
                is_active: result.is_active,
              }
            : current
        )
      );
    } catch (err) {
      setActionError(
        err instanceof ApiError
          ? err.message
          : "Could not update account status."
      );
    } finally {
      setPendingUsername(null);
    }
  }

  async function handleResetPassword(engineer) {
    const confirmed = window.confirm(
      `Reset ${engineer.username}'s password? ` +
        "They'll need to set a new one at next login."
    );

    if (!confirmed) {
      return;
    }

    setActionError(null);
    setPendingUsername(engineer.username);

    try {
      const result =
        await adminApi.resetEngineerPassword(
          engineer.username
        );

      setEngineers((currentEngineers) =>
        currentEngineers.map((current) =>
          current.username === engineer.username
            ? {
                ...current,
                must_reset_password: true,
              }
            : current
        )
      );

      setTempPasswordInfo(result);
    } catch (err) {
      setActionError(
        err instanceof ApiError
          ? err.message
          : "Could not reset password."
      );
    } finally {
      setPendingUsername(null);
    }
  }

  function handleCreated(result) {
    setShowCreate(false);
    setTempPasswordInfo(result);

    void loadEngineers();
  }

  function handleExport() {
    const headers = [
      "Username",
      "Status",
      "Must Reset Password",
      "Total Sessions",
      "Total Questions",
      "High Confidence",
      "Medium Confidence",
      "Low Confidence",
      "Total Minutes",
      "Last Login",
      "Created At",
    ];

    const rows = engineers.map((engineer) => [
      engineer.username,
      engineer.is_active ? "Active" : "Inactive",
      engineer.must_reset_password ? "Yes" : "No",
      engineer.total_sessions,
      engineer.total_questions,
      engineer.high_confidence,
      engineer.medium_confidence,
      engineer.low_confidence,
      engineer.total_minutes,
      engineer.last_login ?? "Never",
      engineer.created_at,
    ]);

    const csv = [headers, ...rows]
      .map((row) =>
        row.map(escapeCsvCell).join(",")
      )
      .join("\r\n");

    const blob = new Blob(
      ["\uFEFF", csv],
      {
        type: "text/csv;charset=utf-8",
      }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download =
      `resolveiq-engineers-` +
      `${new Date()
        .toISOString()
        .slice(0, 10)}.csv`;

    document.body.appendChild(link);
    link.click();
    link.remove();

    setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 0);
  }

  if (status === "loading") {
    return (
      <div className="admin-panel">
        <p className="admin-hint">
          Loading engineers…
        </p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="admin-panel">
        <p className="admin-hint error">
          {error}
        </p>

        <button
          type="button"
          className="row-action retry-button"
          onClick={() => {
            setStatus("loading");
            void loadEngineers();
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <section className="admin-panel employee-panel">
      <div className="panel-heading">
        <div>
          <span className="section-label">
            ENGINEERS
          </span>

          <h2>Support engineer accounts</h2>
        </div>

        <div className="panel-actions">
          <button
            type="button"
            className="export-button secondary"
            onClick={() => setShowCreate(true)}
          >
            + Add Engineer
          </button>

          <button
            type="button"
            className="export-button"
            onClick={handleExport}
            disabled={engineers.length === 0}
          >
            ↓ Export CSV
          </button>
        </div>
      </div>

      {actionError && (
        <p className="admin-hint error">
          {actionError}
        </p>
      )}

      <div className="table-toolbar">
        <input
          type="search"
          aria-label="Search engineers"
          placeholder="Search by username..."
          value={search}
          onChange={(event) =>
            setSearch(event.target.value)
          }
        />

        <span>
          Showing {filtered.length} of{" "}
          {engineers.length} engineers
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
                <td
                  colSpan={8}
                  className="empty-row"
                >
                  {engineers.length === 0
                    ? "No engineer accounts yet."
                    : "No matches."}
                </td>
              </tr>
            )}

            {filtered.map((engineer) => {
              const highRate =
                engineer.total_questions > 0
                  ? `${Math.round(
                      (
                        engineer.high_confidence /
                        engineer.total_questions
                      ) * 100
                    )}%`
                  : "—";

              const isPending =
                pendingUsername ===
                engineer.username;

              return (
                <tr key={engineer.username}>
                  <td>
                    <div className="employee-name">
                      <div className="employee-avatar">
                        {engineer.username
                          .charAt(0)
                          .toUpperCase()}
                      </div>

                      <div>
                        <strong>
                          {engineer.username}
                        </strong>

                        {engineer.must_reset_password && (
                          <span className="must-reset-tag">
                            Must reset password
                          </span>
                        )}
                      </div>
                    </div>
                  </td>

                  <td>
                    <span
                      className={
                        `status ${
                          engineer.is_active
                            ? "active"
                            : "completed"
                        }`
                      }
                    >
                      {engineer.is_active
                        ? "Active"
                        : "Inactive"}
                    </span>
                  </td>

                  <td>
                    {engineer.total_sessions}
                  </td>

                  <td className="question-count">
                    {engineer.total_questions}
                  </td>

                  <td>{highRate}</td>

                  <td>
                    {formatDuration(
                      engineer.total_minutes
                    )}
                  </td>

                  <td>
                    {engineer.last_login
                      ? formatRelativeTime(
                          engineer.last_login
                        )
                      : "Never"}
                  </td>

                  <td>
                    <div className="row-actions">
                      <button
                        type="button"
                        className="row-action"
                        onClick={() =>
                          handleToggleActive(
                            engineer
                          )
                        }
                        disabled={isPending}
                      >
                        {engineer.is_active
                          ? "Disable"
                          : "Enable"}
                      </button>

                      <button
                        type="button"
                        className="row-action"
                        onClick={() =>
                          handleResetPassword(
                            engineer
                          )
                        }
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
        <CreateEngineerModal
          onClose={() =>
            setShowCreate(false)
          }
          onCreated={handleCreated}
        />
      )}

      {tempPasswordInfo && (
        <TempPasswordModal
          username={
            tempPasswordInfo.username
          }
          tempPassword={
            tempPasswordInfo.temp_password
          }
          message={
            tempPasswordInfo.message
          }
          onClose={() =>
            setTempPasswordInfo(null)
          }
        />
      )}
    </section>
  );
}

export default AdminEngineersTab;