import { Link } from "react-router";
import Navbar from "../components/Navbar";
import GuestWorkspace from "../components/GuestWorkspace";
import FullProjectCallout from "../components/FullProjectCallout";
import "../styles/try-page.css";
import "../styles/demo-explorer.css";

function Try() {
  return (
    <>
      <Navbar />
      <div className="try-page-container demo-support-container">
        <GuestWorkspace />

        <p className="demo-support-footer">
          This workspace protects production data. Temporary TXT uploads stay in memory only and
          won&apos;t appear in the Admin Demo. Want to inspect the persisted public-demo environment?{" "}
          <Link to="/demo/admin">Open the read-only Admin Demo</Link>.
        </p>

        <FullProjectCallout />
      </div>
    </>
  );
}

export default Try;
