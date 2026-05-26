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
