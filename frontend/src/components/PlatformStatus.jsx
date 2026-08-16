import { useEffect, useState } from "react";

import { systemApi } from "../api/client";
import "../styles/status.css";

const WARMUP_RETRY_DELAY_MS = 5_000;
const MAX_WARMUP_MS = 6 * 60 * 1_000;

function PlatformStatus() {
  const [apiStatus, setApiStatus] = useState("checking");
  const [rerankerEnabled, setRerankerEnabled] = useState(null);

  useEffect(() => {
    let active = true;
    let retryTimer = null;
    const warmupStartedAt = Date.now();

    async function loadRuntimeStats() {
      try {
        const data = await systemApi.stats();
        if (active) {
          setRerankerEnabled(Boolean(data.reranker_enabled));
        }
      } catch {
        // Non-critical. The retrieval label safely falls back to Hybrid (RRF).
      }
    }

    async function checkBackend() {
      try {
        await systemApi.health();

        if (!active) return;

        setApiStatus("online");
        loadRuntimeStats();
      } catch {
        if (!active) return;

        const stillWithinWarmupWindow =
          Date.now() - warmupStartedAt < MAX_WARMUP_MS;

        if (stillWithinWarmupWindow) {
          // Render Free can be asleep. Keep the page usable and retry instead
          // of immediately presenting a transient cold start as an outage.
          setApiStatus("waking");
          retryTimer = window.setTimeout(
            checkBackend,
            WARMUP_RETRY_DELAY_MS
          );
        } else {
          setApiStatus("offline");
        }
      }
    }

    checkBackend();

    return () => {
      active = false;
      if (retryTimer !== null) {
        window.clearTimeout(retryTimer);
      }
    };
  }, []);

  const statusLabel =
    apiStatus === "online"
      ? "LIVE"
      : apiStatus === "offline"
      ? "OFFLINE"
      : apiStatus === "waking"
      ? "WAKING"
      : "CHECKING";

  const apiLabel =
    apiStatus === "online"
      ? "Online"
      : apiStatus === "offline"
      ? "Unavailable"
      : apiStatus === "waking"
      ? "Preparing backend…"
      : "Checking";

  return (
    <section className="platform-status">
      <div className="status-heading">
        <span>PLATFORM STATUS</span>

        <small
          className={`platform-status-label ${apiStatus}`}
          aria-live="polite"
        >
          {statusLabel}
        </small>
      </div>

      <div className="status-items">
        <div className={`status-item api-status ${apiStatus}`}>
          <i aria-hidden="true" />
          <span>API Service</span>
          <strong>{apiLabel}</strong>
        </div>

        <div className="status-item">
          <i aria-hidden="true" />
          <span>Retrieval Pipeline</span>
          <strong>
            {rerankerEnabled ? "Hybrid + reranked" : "Hybrid (RRF)"}
          </strong>
        </div>

        <div className="status-item">
          <i aria-hidden="true" />
          <span>Answers</span>
          <strong>Source-grounded</strong>
        </div>
      </div>
    </section>
  );
}

export default PlatformStatus;
