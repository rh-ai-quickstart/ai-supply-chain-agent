import { getLogger } from "../utils/logger.js";
import { consumeChatSseStream } from "../utils/chatStream.js";

const logger = getLogger(import.meta.url);

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
  logger.info("GET %s", path);
  try {
    const response = await fetch(apiUrl(path), { signal });
    if (!response.ok) {
      logger.warn("GET %s failed: %d %s", path, response.status, await response.text());
      throw new Error(await errorMessageFromResponse(response));
    }
    logger.info("GET %s OK: %d", path, response.status);
    return response.json();
  } catch (err) {
    logger.error("GET %s error: %s", path, err.message);
    throw err;
  }
}

export async function apiPost(path, payload, { signal } = {}) {
  logger.info("POST %s: %O", path, payload);
  try {
    const response = await fetch(apiUrl(path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });
    if (!response.ok) {
      logger.warn("POST %s failed: %d %s", path, response.status, await response.text());
      throw new Error(await errorMessageFromResponse(response));
    }
    logger.info("POST %s OK: %d", path, response.status);
    return response.json();
  } catch (err) {
    logger.error("POST %s error: %s", path, err.message);
    throw err;
  }
}

/** POST with ``stream: true`` and SSE event callbacks for chat completions. */
export async function apiPostStream(path, payload, onEvent, { signal } = {}) {
  logger.info("POST_STREAM %s: %O", path, payload);
  try {
    const response = await fetch(apiUrl(path), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ ...payload, stream: true }),
      signal,
    });
    if (!response.ok) {
      logger.warn("POST_STREAM %s failed: %d %s", path, response.status, await response.text());
      throw new Error(await errorMessageFromResponse(response));
    }
    logger.info("POST_STREAM %s OK: %d, starting SSE", path, response.status);
    await consumeChatSseStream(response, (event) => {
      if (event?.type === "error") {
        logger.warn("SSTREAM %s event=error: %O", path, event);
      } else if (event?.type === "done") {
        logger.info("SSTREAM %s done: %O", path, event);
      }
      onEvent?.(event);
    });
  } catch (err) {
    logger.error("POST_STREAM %s error: %s", path, err.message);
    throw err;
  }
}

/** Multipart POST (file uploads). Do not set Content-Type so the browser sets the boundary. */
export async function apiPostFormData(path, formData, { signal } = {}) {
  const files = [];
  for (const [key, value] of formData.entries()) {
    if (value instanceof File) files.push(value.name);
  }
  logger.info("POST_FORM %s: files=%O", path, files);
  try {
    const response = await fetch(apiUrl(path), {
      method: "POST",
      body: formData,
      signal,
    });
    if (!response.ok) {
      logger.warn("POST_FORM %s failed: %d %s", path, response.status, await response.text());
      throw new Error(await errorMessageFromResponse(response));
    }
    logger.info("POST_FORM %s OK: %d", path, response.status);
    return response.json();
  } catch (err) {
    logger.error("POST_FORM %s error: %s", path, err.message);
    throw err;
  }
}
