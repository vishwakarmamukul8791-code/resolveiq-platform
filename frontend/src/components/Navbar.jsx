import "../styles/navbar.css";

function Navbar() {
  return (
    <nav className="main-navbar">

      <div className="brand-section">

        <div className="brand-mark">
          IR
        </div>

        <div>
          <h3>Incident Resolution Assistant</h3>
          <span>Enterprise AI Operations Platform</span>
        </div>

      </div>

      <div className="edition-badge">
        INTERNAL PLATFORM
      </div>

    </nav>
  );
}

export default Navbar;