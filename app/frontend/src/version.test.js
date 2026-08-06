import { describe, expect, it } from "vitest";
import { APP_VERSION, formatBuildTime } from "./version";

describe("APP_VERSION", () => {
  it("falls back to 'dev' when no build-time env vars are baked in", () => {
    // Vitest runs outside the Containerfile build, so VITE_GIT_COMMIT/VITE_BUILD_TIME
    // are unset here, matching a `pnpm dev` / local run.
    expect(APP_VERSION.gitCommit).toBe("dev");
    expect(APP_VERSION.buildTime).toBe("");
  });
});

describe("formatBuildTime", () => {
  it("returns an empty string for a falsy input", () => {
    expect(formatBuildTime("")).toBe("");
    expect(formatBuildTime(undefined)).toBe("");
  });

  it("returns the raw value when it can't be parsed as a date", () => {
    expect(formatBuildTime("not-a-date")).toBe("not-a-date");
  });

  it("formats a valid ISO timestamp into a human-readable string", () => {
    const formatted = formatBuildTime("2026-08-06T09:40:00Z");
    expect(typeof formatted).toBe("string");
    expect(formatted.length).toBeGreaterThan(0);
    expect(formatted).not.toBe("2026-08-06T09:40:00Z");
  });
});
