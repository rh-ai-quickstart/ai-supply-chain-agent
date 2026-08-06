/**
 * Build identifiers baked in by the frontend Containerfile (`VITE_GIT_COMMIT`
 * / `VITE_BUILD_TIME` build args, see Makefile's `build-frontend` target).
 * Vite inlines `VITE_`-prefixed env vars into `import.meta.env` at build
 * time, so this is `"dev"` outside of a container build (e.g. `pnpm dev`).
 */
export const APP_VERSION = {
  gitCommit: import.meta.env.VITE_GIT_COMMIT || "dev",
  buildTime: import.meta.env.VITE_BUILD_TIME || "",
};

/** Formats an ISO build timestamp for display; falls back to the raw value. */
export function formatBuildTime(buildTime) {
  if (!buildTime) return "";
  const date = new Date(buildTime);
  if (Number.isNaN(date.getTime())) return buildTime;
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
