// frontend/src/context/AuthContext.jsx

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { authApi, tokenStorage, onUnauthorized } from "../api/client";

/**
 * Auth state lives here: token (via client.js's tokenStorage), username,
 * role, session_id, and the forced-password-reset flag.
 *
 * Two things persist across a page refresh beyond just the token:
 * - session_id: /auth/me (used to restore state on reload) does NOT return
 *   it — only /auth/login does. Without persisting it separately, a refresh
 *   would silently drop session-level question tracking (record_question()
 *   on the backend just no-ops on a missing session_id — no error, it just
 *   quietly stops counting). Persisting it avoids that silent gap.
 * - must_reset_password: persisted for immediate rendering, then refreshed
 *   from /auth/me so the server remains authoritative after reload.
 */

const SESSION_META_KEY = "iira_session_meta"; // { sessionId, mustResetPassword }

function readSessionMeta() {
  try {
    const raw = localStorage.getItem(SESSION_META_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeSessionMeta(meta) {
  try {
    localStorage.setItem(SESSION_META_KEY, JSON.stringify(meta));
  } catch {
    /* private browsing / storage disabled — non-fatal */
  }
}

function clearSessionMeta() {
  try {
    localStorage.removeItem(SESSION_META_KEY);
  } catch {
    /* no-op */
  }
}

const AuthContext = createContext(null);

const initialState = {
  isAuthenticated: false,
  isLoading: true, // true until the mount-time token check finishes
  username: null,
  role: null,
  sessionId: null,
  mustResetPassword: false,
};

export function AuthProvider({ children }) {
  const [state, setState] = useState(initialState);

  // Shared by logout() and by the 401 handler below — both mean the same
  // thing: "this browser is no longer authenticated, reset to logged-out."
  const clearAuth = useCallback(() => {
    tokenStorage.clear();
    clearSessionMeta();
    setState({ ...initialState, isLoading: false });
  }, []);

  // Registered directly in the render body, not inside useEffect, so it's
  // live before the mount-time getMe() call below ever fires. If a stored
  // token has expired, client.js's request() will hit the 401 branch,
  // clear the token itself, and call this — which resets React state to
  // match what's already true in storage.
  onUnauthorized(clearAuth);

  // Restore session on page load: if a token is stored, ask the server
  // whether it's still valid via /auth/me. Deliberately NOT decoding the
  // JWT client-side to read username/role — that would only prove the
  // token is well-formed, not that the server still accepts it (expired
  // tokens still decode fine). Calling /auth/me proves both at once.
  useEffect(() => {
    const token = tokenStorage.get();

    if (!token) {
      setState((s) => ({ ...s, isLoading: false }));
      return;
    }

    const meta = readSessionMeta();

    authApi
      .getMe()
      .then(({ username, role, must_reset_password }) => {
        const mustResetPassword = must_reset_password ?? false;

        writeSessionMeta({
          ...meta,
          mustResetPassword,
        });

        setState({
          isAuthenticated: true,
          isLoading: false,
          username,
          role,
          sessionId: meta.sessionId ?? null,
          mustResetPassword,
        });
      })
      .catch(() => {
        // Two different failure shapes land here:
        //   1. The token was genuinely rejected (401) — client.js already
        //      cleared storage and fired onUnauthorized -> clearAuth()
        //      has already run, so isLoading is already false.
        //   2. A network failure (Render cold start, timeout, offline,
        //      CORS) — nothing else runs in that case, so isLoading
        //      would otherwise stay true forever and the app would be
        //      stuck on "Loading…" permanently.
        // Setting isLoading: false unconditionally here handles case 2
        // without disturbing case 1 (already false, so this is a no-op
        // there). The person just lands on the logged-out landing page
        // instead of hanging — they can retry once the backend is warm.
        setState((s) => (s.isLoading ? { ...s, isLoading: false } : s));
      });
  }, []);

  const login = useCallback(async (username, password, rememberMe = true) => {
    const data = await authApi.login(username, password);

    tokenStorage.set(data.access_token, rememberMe);
    writeSessionMeta({
      sessionId: data.session_id,
      mustResetPassword: data.must_reset_password,
    });

    setState({
      isAuthenticated: true,
      isLoading: false,
      username: data.username,
      role: data.role,
      sessionId: data.session_id,
      mustResetPassword: data.must_reset_password,
    });

    return data;
  }, []);

  const completePasswordReset = useCallback(async (currentPassword, newPassword) => {
    await authApi.resetPassword(currentPassword, newPassword);
    const meta = readSessionMeta();
    writeSessionMeta({ ...meta, mustResetPassword: false });
    setState((s) => ({ ...s, mustResetPassword: false }));
  }, []);

  const logout = useCallback(async () => {
    const { sessionId } = state;
    try {
      if (sessionId) await authApi.logout(sessionId);
    } catch {
      // Best-effort: if the network call fails (backend down, token
      // already expired), still log the user out locally. They should
      // never get stuck unable to log out.
    } finally {
      clearAuth();
    }
  }, [state, clearAuth]);

  const value = { ...state, login, logout, completePasswordReset };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
