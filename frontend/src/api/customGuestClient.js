const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class CustomGuestError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "CustomGuestError";
    this.status = status;
  }
}

export async function askUploadedText({ query, documentName, documentText }) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/guest/custom-text/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        document_name: documentName,
        document_text: documentText,
      }),
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === "AbortError") {
      throw new CustomGuestError("The request took too long. Please try again.");
    }
    throw new CustomGuestError("Could not reach the ResolveIQ backend.");
  }

  clearTimeout(timeoutId);

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
    const detail = data?.detail;
    const message = typeof detail === "string"
      ? detail
      : `Custom TXT question failed (${response.status}).`;
    throw new CustomGuestError(message, response.status);
  }

  return data;
}
