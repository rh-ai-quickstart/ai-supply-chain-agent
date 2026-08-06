import { describe, expect, it } from "vitest";
import { isAbortError, messageFromError } from "./errorMessage";

describe("isAbortError", () => {
  it("recognizes AbortError-shaped values by name", () => {
    expect(isAbortError({ name: "AbortError" })).toBe(true);
    expect(isAbortError(new DOMException("aborted", "AbortError"))).toBe(true);
  });

  it("returns false for other errors and nullish values", () => {
    expect(isAbortError(new Error("boom"))).toBe(false);
    expect(isAbortError(null)).toBe(false);
    expect(isAbortError(undefined)).toBe(false);
  });
});

describe("messageFromError", () => {
  it("returns an empty string for abort errors", () => {
    expect(messageFromError({ name: "AbortError" }, "fallback")).toBe("");
  });

  it("uses the Error message when present", () => {
    expect(messageFromError(new Error("boom"), "fallback")).toBe("boom");
  });

  it("falls back for non-Error values or blank messages", () => {
    expect(messageFromError("string error", "fallback")).toBe("fallback");
    expect(messageFromError(new Error("   "), "fallback")).toBe("fallback");
  });
});
