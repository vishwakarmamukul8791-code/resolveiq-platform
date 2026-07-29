import { Link } from "react-router-dom";
import ThemeToggle from "./ThemeToggle";
import brandMark from "../assets/resolveiq-mark.png";
import "../styles/navbar.css";

function Navbar() {
  return (
    <nav className="main-navbar">

      <Link to="/" className="brand-section">
        <img src={brandMark} alt="ResolveIQ" className="brand-mark-icon" />

        <div>
          <h3>ResolveIQ</h3>
          <span>Enterprise AI Incident Intelligence Platform</span>
        </div>
      </Link>

      <div className="navbar-right">
        <div className="edition-badge">
          INTERNAL PLATFORM
        </div>

        <ThemeToggle />
      </div>

    </nav>
  );
}

export default Navbar;