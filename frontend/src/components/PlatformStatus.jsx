import "../styles/status.css";

function PlatformStatus() {
  return (
    <section className="platform-status">

      <div className="status-heading">
        <span>PLATFORM STATUS</span>
        <small>LIVE</small>
      </div>

      <div className="status-items">

        <div>
          <i></i>
          <span>Vector Database</span>
          <strong>Connected</strong>
        </div>

        <div>
          <i></i>
          <span>Gemini AI</span>
          <strong>Available</strong>
        </div>

        <div>
          <i></i>
          <span>Knowledge Base</span>
          <strong>Indexed</strong>
        </div>

      </div>

    </section>
  );
}

export default PlatformStatus;