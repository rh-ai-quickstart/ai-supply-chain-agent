/** Best-effort JSON for debug panels; never throws into the React tree. */
export function safeJsonStringify(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
