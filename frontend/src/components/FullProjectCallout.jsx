import "../styles/demo-explorer.css";

const REPOSITORY_URL = "https://github.com/vishwakarmamukul8791-code/resolveiq-platform";
const LOCAL_SETUP_URL = `${REPOSITORY_URL}#local-setup--windows-powershell`;

function FullProjectCallout() {
  return (
    <section className="full-project-callout">
      <div className="full-project-callout-copy">
        <span className="demo-eyebrow">EXPLORE BEYOND THE PUBLIC DEMO</span>
        <h2>Run the complete ResolveIQ workflow locally.</h2>
        <p>
          This public environment is intentionally read-only and limited to public sample data.
          Clone the project locally to test authentication, admin operations, document upload and
          processing, engineer management, and the complete application workflow with your own data.
        </p>
      </div>

      <div className="full-project-callout-actions">
        <a href={REPOSITORY_URL} target="_blank" rel="noopener noreferrer" className="demo-secondary-button">
          View GitHub Repository
        </a>
        <a href={LOCAL_SETUP_URL} target="_blank" rel="noopener noreferrer" className="demo-primary-button">
          Run Full Project Locally
        </a>
      </div>
    </section>
  );
}

export default FullProjectCallout;
