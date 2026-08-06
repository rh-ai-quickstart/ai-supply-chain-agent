import { consumeChatSseStream } from "../utils/chatStream.js";

/** Same-origin /api/... — proxied by nginx in cluster or Vite dev server locally. */

function apiUrl(path) {
  return path.startsWith("/") ? path : `/${path}`;
}

async function errorMessageFromResponse(response) {
  const fallback = `Request failed: ${response.status}`;
  try {
    const text = await response.text();
    if (!text) return fallback;
    try {
      const body = JSON.parse(text);
      if (body?.error) return String(body.error);
    } catch {
      /* keep raw text */
    }
    return text;
  } catch {
    return fallback;
  }
}

export async function apiGet(path, { signal } = {}) {
  const response = await fetch(apiUrl(path), { signal });
  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }
  return response.json();
}

export async function apiPost(path, payload, { signal } = {}) {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }
  return response.json();
}

/** POST with ``stream: true`` and SSE event callbacks for chat completions. */
export async function apiPostStream(path, payload, onEvent, { signal } = {}) {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ ...payload, stream: true }),
    signal,
  });
  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }
  await consumeChatSseStream(response, onEvent);
}

/** Multipart POST (file uploads). Do not set Content-Type so the browser sets the boundary. */
export async function apiPostFormData(path, formData, { signal } = {}) {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    body: formData,
    signal,
  });
  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }
  return response.json();
}
