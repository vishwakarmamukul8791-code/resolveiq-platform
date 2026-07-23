import "../styles/login-panel.css";

function LoginPanel() {
  return (
    <section className="login-panel">

      <div className="login-header">
        <span>SECURE ACCESS</span>
        <h2>Enterprise Sign In</h2>
        <p>Authorized personnel only.</p>
      </div>

      <form>

        <div className="input-group">
          <label>Username</label>

          <input
            type="text"
            placeholder="Enter your username"
          />
        </div>

        <div className="input-group">
          <label>Password</label>

          <input
            type="password"
            placeholder="Enter your password"
          />
        </div>

        <div className="login-options">

          <label>
            <input type="checkbox" />
            Remember me
          </label>

          <span>Internal Access</span>

        </div>

        <button type="submit">
          Sign In
          <span>→</span>
        </button>

      </form>

      <div className="login-footer">
        Account access is managed by your administrator.
      </div>

    </section>
  );
}

export default LoginPanel;