const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class DemoApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "DemoApiError";
    this.status = status;
  }
}

export async function getPublicDemoContext() {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/demo/context`, {
      headers: { Accept: "application/json" },
    });
  } catch {
    throw new DemoApiError("Could not reach the ResolveIQ backend.");
  }

  const raw = await response.text();
  let data = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : "Public demo is unavailable.";
    throw new DemoApiError(detail, response.status);
  }

  return data;
}
