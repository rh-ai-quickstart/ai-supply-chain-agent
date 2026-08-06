/** Best-effort JSON for debug panels; never throws into the React tree. */
export function safeJsonStringify(value) {
  try {
    const json = JSON.stringify(value, null, 2);
    // JSON.stringify returns undefined for Symbols / bare undefined (does not throw).
    return json === undefined ? String(value) : json;
  } catch {
    return String(value);
  }
}
