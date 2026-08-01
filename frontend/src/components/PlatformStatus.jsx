import { useEffect, useState } from "react";

import { systemApi } from "../api/client";
import "../styles/status.css";


function PlatformStatus() {
  const [apiStatus, setApiStatus] = useState("checking");

  useEffect(() => {
    let active = true;

    systemApi
      .health()
      .then(() => {
        if (active) {
          setApiStatus("online");
        }
      })
      .catch(() => {
        if (active) {
          setApiStatus("offline");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const statusLabel =
    apiStatus === "online"
      ? "LIVE"
      : apiStatus === "offline"
      ? "OFFLINE"
      : "CHECKING";

  const apiLabel =
    apiStatus === "online"
      ? "Online"
      : apiStatus === "offline"
      ? "Unavailable"
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
          <strong>Hybrid + reranked</strong>
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