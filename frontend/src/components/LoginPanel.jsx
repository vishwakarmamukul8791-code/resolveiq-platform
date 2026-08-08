// frontend/src/components/LoginPanel.jsx

import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";
import "../styles/login-panel.css";

function LoginPanel() {
  const { login, completePasswordReset, isAuthenticated, mustResetPassword, role } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isResetting, setIsResetting] = useState(false);
  const [resetError, setResetError] = useState(null);

  function redirectByRole(currentRole) {
    navigate(currentRole === "admin" ? "/admin" : "/support", { replace: true });
  }

  // Navigation is a side effect. Running it during render causes React
  // warnings and can produce duplicate redirects in Strict Mode.
  useEffect(() => {
    if (isAuthenticated && !mustResetPassword) {
      navigate(role === "admin" ? "/admin" : "/support", {
        replace: true,
      });
    }
  }, [isAuthenticated, mustResetPassword, navigate, role]);

  async function handleLogin(e) {
    e.preventDefault();
    setError(null);

    if (!username.trim() || !password) {
      setError("Enter your username and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      const data = await login(username.trim(), password, rememberMe);
      if (!data.must_reset_password) {
        redirectByRole(data.role);
      }
      // Otherwise: mustResetPassword is now true in context, so the reset
      // form below renders on the next render — no navigation yet.
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleReset(e) {
    e.preventDefault();
    setResetError(null);

    if (newPassword.length < 8) {
      setResetError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setResetError("Passwords don't match.");
      return;
    }

    setIsResetting(true);
    try {
      // `password` still holds what was typed on the sign-in step above —
      // the backend requires proof of the current password before
      // accepting a new one, so this reuses it instead of asking the
      // person to type their just-used temporary password a second time.
      await completePasswordReset(password, newPassword);
      redirectByRole(role);
    } catch (err) {
      setResetError(err instanceof ApiError ? err.message : "Could not update password.");
    } finally {
      setIsResetting(false);
    }
  }

  if (mustResetPassword) {
    return (
      <section className="login-panel">
        <div className="login-header">
          <span>SECURE ACCESS</span>
          <h2>Set a new password</h2>
          <p>Your temporary password must be changed before continuing.</p>
        </div>

        <form onSubmit={handleReset}>
          <div className="input-group">
            <label htmlFor="new-password">New password</label>
            <input
              id="new-password"
              type="password"
              placeholder="At least 8 characters"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={isResetting}
              autoComplete="new-password"
              autoFocus
            />
          </div>

          <div className="input-group">
            <label htmlFor="confirm-password">Confirm new password</label>
            <input
              id="confirm-password"
              type="password"
              placeholder="Re-enter new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={isResetting}
              autoComplete="new-password"
            />
          </div>

          {resetError && <div className="form-error">{resetError}</div>}

          <button type="submit" disabled={isResetting} style={{ marginTop: 24 }}>
            {isResetting ? "Updating…" : "Update password"}
            <span>→</span>
          </button>
        </form>

        <div className="login-footer">
          This is a one-time step required after your account was created.
        </div>
      </section>
    );
  }

  if (isAuthenticated) {
    return null;
  }

  return (
    <section className="login-panel">
      <div className="login-header">
        <span>SECURE ACCESS</span>
        <h2>Enterprise Sign In</h2>
        <p>Authorized personnel only.</p>
      </div>

      <form onSubmit={handleLogin}>
        <div className="input-group">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            type="text"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={isSubmitting}
            autoComplete="username"
          />
        </div>

        <div className="input-group">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isSubmitting}
            autoComplete="current-password"
          />
        </div>

        <div className="login-options">
          <label>
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              disabled={isSubmitting}
            />
            Remember me
          </label>
          <span>Internal Access</span>
        </div>

        {error && <div className="form-error">{error}</div>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign In"}
          <span>→</span>
        </button>
      </form>

      <div className="login-footer">
        Account access is managed by your administrator.
      </div>

      <div className="login-footer">
        Just evaluating the project? <Link to="/try">Try it without logging in</Link>
      </div>
    </section>
  );
}

export default LoginPanel;
