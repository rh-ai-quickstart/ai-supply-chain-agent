import { consoleFetch, consoleFetchJSON } from '@openshift-console/dynamic-plugin-sdk';

declare const __SUPPLY_CHAIN_PLUGIN_HTTP_BASE__: string;

/**
 * Base URL for backend HTTP calls.
 * - Default: under `/api/plugins/<plugin-name>/` on the **current page origin** (the OpenShift console).
 *   The console proxies that prefix to the plugin Service; nginx on the pod serves `/api/...` to Flask.
 *   Those requests must use `consoleFetchJSON` so the console adds `X-CSRFToken` (and impersonation headers);
 *   plain `fetch` omits them and POST fails with "CSRF token does not match CSRF cookie".
 * - Optional `SUPPLY_CHAIN_API_BASE_URL` build-time override for a full origin (direct backend / tooling).
 * Replaced at build time via webpack DefinePlugin (see webpack.config.ts).
 */
// eslint-disable-next-line no-undef -- `process.env` is compile-time replaced for the browser bundle
const API_BASE_URL_OVERRIDE = process.env.SUPPLY_CHAIN_API_BASE_URL ?? '';

function resolveRequestUrl(path: string): string {
  const trimmed = path.startsWith('/') ? path.slice(1) : path;
  if (API_BASE_URL_OVERRIDE) {
    const base = API_BASE_URL_OVERRIDE.replace(/\/?$/, '/');
    return `${base}${trimmed}`;
  }
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  return new URL(trimmed, `${origin}${__SUPPLY_CHAIN_PLUGIN_HTTP_BASE__}`).href;
}

function usesConsoleProxy(): boolean {
  return !API_BASE_URL_OVERRIDE;
}

export async function apiGet<T>(path: string): Promise<T> {
  const url = resolveRequestUrl(path);
  if (usesConsoleProxy()) {
    return consoleFetchJSON(url) as Promise<T>;
  }
  const response = await fetch(url, { credentials: 'same-origin' });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  const url = resolveRequestUrl(path);
  if (usesConsoleProxy()) {
    return consoleFetchJSON.post(url, payload) as Promise<T>;
  }
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    credentials: 'same-origin',
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

/** Multipart POST (e.g. file uploads). Uses ``consoleFetch`` in-cluster so CSRF headers are set. */
export async function apiPostFormData<T>(path: string, formData: FormData): Promise<T> {
  const url = resolveRequestUrl(path);
  const parseError = async (response: Response): Promise<Error> => {
    const text = await response.text();
    try {
      const body = JSON.parse(text) as { error?: string };
      if (body?.error) {
        return new Error(body.error);
      }
    } catch {
      /* not JSON */
    }
    return new Error(text || `Request failed: ${response.status}`);
  };

  if (usesConsoleProxy()) {
    const response = await consoleFetch(url, { method: 'POST', body: formData });
    if (!response.ok) {
      throw await parseError(response);
    }
    return response.json() as Promise<T>;
  }
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    credentials: 'same-origin',
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json() as Promise<T>;
}
