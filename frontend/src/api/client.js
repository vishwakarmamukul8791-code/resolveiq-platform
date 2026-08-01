/**
 * Centralized API client for the ResolveIQ frontend.
 *
 * All API requests pass through this module so authentication headers,
 * timeout handling, error parsing, and backend configuration remain
 * consistent across the application.
 *
 * Authentication tokens are stored in localStorage when "Remember me" is
 * enabled and sessionStorage otherwise. Form-encoded and JSON requests are
 * handled according to the corresponding FastAPI endpoint.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "iira_token";

export const tokenStorage = {
  get() {
    try {
      return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  // persist=true  -> localStorage   (survives closing the browser — "Remember me" checked)
  // persist=false -> sessionStorage (cleared when the tab/browser closes)
  // Default stays `true` so any existing call site that doesn't pass a
  // second argument keeps its old behavior.
  set(token, persist = true) {
    try {
      if (persist) {
        localStorage.setItem(TOKEN_KEY, token);
        sessionStorage.removeItem(TOKEN_KEY);
      } else {
        sessionStorage.setItem(TOKEN_KEY, token);
        localStorage.removeItem(TOKEN_KEY);
      }
    } catch {
      /* private browsing / storage disabled — app still works, just won't persist */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      /* no-op */
    }
  },
};

export class ApiError extends Error {
  constructor(message, { status = 0, detail = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status; // 0 = network/timeout, otherwise the HTTP status
    this.detail = detail; // raw `detail` field from FastAPI's error body
  }
}

// AuthContext registers a callback here (e.g. clear state, redirect to /).
// Only fired for requests that were sent WITH a token and got a 401 back —
// never for a failed login attempt itself (that's "wrong password", not
// "session expired", and is handled by the caller reading the ApiError).
let unauthorizedHandler = null;
export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

function buildQueryString(params) {
  if (!params) return "";
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== ""
  );
  if (entries.length === 0) return "";
  const qs = new URLSearchParams();
  entries.forEach(([k, v]) => qs.append(k, v));
  return `?${qs.toString()}`;
}

function extractErrorMessage(data, fallback) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI/Pydantic 422 validation errors: [{ msg, loc, ... }, ...]
    return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  return fallback;
}

/**
 * Core request function. Every exported API method funnels through this,
 * so auth injection, error shape, and timeouts only exist in one place.
 */
async function request(
  path,
  {
    method = "GET",
    params,
    json,
    form,
    multipart,
    headers = {},
    auth = true,
    timeoutMs = 15000,
  } = {}
) {
  const url = `${API_BASE_URL}${path}${buildQueryString(params)}`;
  const finalHeaders = { ...headers };
  let body;

  if (multipart) {
    // FormData: do NOT set Content-Type manually — the browser sets it,
    // including the multipart boundary. Setting it ourselves breaks upload.
    body = multipart;
  } else if (form) {
    body = new URLSearchParams(form);
    finalHeaders["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (json !== undefined) {
    body = JSON.stringify(json);
    finalHeaders["Content-Type"] = "application/json";
  }

  if (auth) {
    const token = tokenStorage.get();
    if (token) finalHeaders["Authorization"] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(url, {
      method,
      headers: finalHeaders,
      body,
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === "AbortError") {
      throw new ApiError(
    "The request took too long. Please try again.",
    { status: 0 }
  );
}
    // Network failure — wrong port, backend not running, CORS block, etc.
    throw new ApiError(
      `Could not reach the server at ${API_BASE_URL}. Is the backend running?`,
      { status: 0 }
    );
  }
  clearTimeout(timeoutId);

  const raw = await response.text();
  let data = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = null; // non-JSON body — shouldn't happen against this backend
    }
  }

  if (!response.ok) {
    if (response.status === 401 && auth) {
      tokenStorage.clear();
      if (unauthorizedHandler) unauthorizedHandler();
    }
    throw new ApiError(
      extractErrorMessage(data, `${method} ${path} failed (${response.status})`),
      { status: response.status, detail: data?.detail ?? null }
    );
  }

  return data;
}

// ── Auth ─────────────────────────────────────────────────────────────────
export const authApi = {
  login(username, password) {
    return request("/auth/login", {
      method: "POST",
      form: { username, password },
      auth: false, // no token exists yet
    });
  },
  logout(sessionId) {
    return request("/auth/logout", {
      method: "POST",
      form: { session_id: sessionId },
    });
  },
  resetPassword(newPassword) {
    return request("/auth/reset-password", {
      method: "POST",
      form: { new_password: newPassword },
    });
  },
  getMe() {
    return request("/auth/me");
  },
};

// ── Core RAG ─────────────────────────────────────────────────────────────
export const askApi = {
  // /ask performs retrieval, reranking, and one bounded
  // Gemini call. The client timeout is intentionally
  // larger than the backend provider timeout so the API
  // can return a structured error to the UI.
  // Pass conversationId (from a previous /ask response) to keep a
  // follow-up question in the same thread instead of starting a new one.
  ask(query, { documentName, sessionId, conversationId, timeoutMs = 60000 } = {}) {
    const headers = {};

    if (sessionId) {
      headers["X-Session-Id"] = sessionId;
    }

    const json = { query };

    if (documentName) {
      json.document_name = documentName;
    }

    if (conversationId) {
      json.conversation_id = conversationId;
    }

    return request("/ask", {
      method: "POST",
      json,
      headers,
      timeoutMs,
    });
  },
};

// ── Documents ────────────────────────────────────────────────────────────
export const documentsApi = {
  list() {
    return request("/documents");
  },
  getDetails(name) {
    return request(`/document/${encodeURIComponent(name)}`);
  },
  upload(file) {
    const formData = new FormData();
    formData.append("file", file);
    return request("/upload", { method: "POST", multipart: formData });
  },
  process(filename) {
    return request("/process-document", {
      method: "POST",
      params: { filename },
    });
  },
  remove(name) {
    return request(`/document/${encodeURIComponent(name)}`, { method: "DELETE" });
  },
};

// ── History (ownership-scoped to the calling user) ──────────────────────
export const historyApi = {
  list() {
    return request("/history");
  },
  // Full message list for one thread — used when a past investigation is
  // selected from the sidebar, so the whole conversation loads.
  getConversation(id) {
    return request(`/history/${encodeURIComponent(id)}`);
  },
  pin(id) {
    return request(`/history/${encodeURIComponent(id)}/pin`, { method: "PATCH" });
  },
  deleteAll() {
    return request("/history", { method: "DELETE" });
  },
  deleteOne(id) {
    return request(`/history/${encodeURIComponent(id)}`, { method: "DELETE" });
  },
};

// ── Admin (all 403 for engineer tokens — backend-enforced via require_admin) ─
export const adminApi = {
  createEngineer(username, fullName) {
    return request("/admin/create-engineer", {
      method: "POST",
      json: { username, full_name: fullName ?? null },
    });
  },
  listEngineers() {
    return request("/admin/engineers");
  },
  setActive(username, isActive) {
    return request("/admin/set-active", {
      method: "POST",
      json: { username, is_active: isActive },
    });
  },
  resetEngineerPassword(username) {
    return request("/admin/reset-engineer-password", {
      method: "POST",
      json: { username },
    });
  },
  getSessions(username) {
    return request("/admin/sessions", { params: { username } });
  },
  getAnalytics() {
    return request("/admin/analytics");
  },
  getKnowledgeGaps() {
    return request("/admin/knowledge-gaps");
  },
  getSourceAnalytics() {
    return request("/admin/source-analytics");
  },
  getSystemHealth() {
    return request("/admin/system-health");
  },
  getEngineerHistory(username) {
    return request(`/admin/history/${encodeURIComponent(username)}`);
  },
};

// ── Debug (RAG internals — admin-only server-side) ──────────────────────
export const debugApi = {
  retrieval(query, { documentName, rewrittenQuery } = {}) {
    return request("/debug/retrieval", {
      params: {
        query,
        document_name: documentName,
        rewritten_query: rewrittenQuery,
      },
    });
  },
};

// ── System (public, used pre-login by PlatformStatus on Landing) ────────
export const systemApi = {
  health() {
    return request("/health", { auth: false });
  },
  stats() {
    return request("/stats", { auth: false });
  },
};