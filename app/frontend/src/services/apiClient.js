/** Same-origin /api/... — proxied by nginx in cluster or Vite dev server locally. */

function apiUrl(path) {
  return path.startsWith("/") ? path : `/${path}`;
}

export async function apiGet(path) {
  const response = await fetch(apiUrl(path));
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export async function apiPost(path, payload) {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

/** Parse buffered NDJSON text into complete lines; returns { events, remainder }. Exported for tests. */
export function parseNdjsonBuffer(buffer) {
  const events = [];
  const lines = buffer.split("\n");
  const remainder = lines.pop() ?? "";
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    events.push(JSON.parse(trimmed));
  }
  return { events, remainder };
}

async function consumeNdjsonReader(reader, onEvent) {
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const { events, remainder } = parseNdjsonBuffer(buffer);
    buffer = remainder;
    for (const evt of events) {
      onEvent(evt);
    }
  }
  buffer += decoder.decode();
  const trimmed = buffer.trim();
  if (trimmed) {
    onEvent(JSON.parse(trimmed));
  }
}

/** POST JSON and consume a newline-delimited JSON response stream. */
export async function apiPostNdjsonStream(path, payload, { onEvent, signal } = {}) {
  try {
    const response = await fetch(apiUrl(path), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/x-ndjson" },
      body: JSON.stringify(payload),
      signal,
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    if (!response.body) {
      throw new Error("Response body is not readable");
    }
    await consumeNdjsonReader(response.body.getReader(), onEvent);
  } catch (err) {
    if (err?.name === "AbortError") {
      return;
    }
    throw err;
  }
}

/** Multipart POST (file uploads). Do not set Content-Type so the browser sets the boundary. */

export async function apiPostFormData(path, formData) {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const text = await response.text();
    let message = text || `Request failed: ${response.status}`;
    try {
      const body = JSON.parse(text);
      if (body?.error) {
        message = body.error;
      }
    } catch {
      /* keep message as raw text */
    }
    throw new Error(message);
  }
  return response.json();
}
