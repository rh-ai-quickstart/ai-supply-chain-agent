import { describe, expect, it } from "vitest";
import { safeJsonStringify } from "./safeJsonStringify";

describe("safeJsonStringify", () => {
  it("serializes a simple object", () => {
    expect(safeJsonStringify({ a: 1 })).toBe("{\n  \"a\": 1\n}");
  });

  it("serializes nested objects with indentation", () => {
    expect(safeJsonStringify({ a: { b: 2 } })).toBe('{\n  "a": {\n    "b": 2\n  }\n}');
  });

  it("serializes arrays", () => {
    expect(safeJsonStringify([1, 2, 3])).toBe("[\n  1,\n  2,\n  3\n]");
  });

  it("returns JSON string for primitive number", () => {
    expect(safeJsonStringify(42)).toBe("42");
  });

  it("returns JSON string for primitive string", () => {
    expect(safeJsonStringify("hello")).toBe('"hello"');
  });

  it("returns JSON string for boolean", () => {
    expect(safeJsonStringify(true)).toBe("true");
  });

  it("returns JSON string for null", () => {
    expect(safeJsonStringify(null)).toBe("null");
  });

  it("serializes empty object", () => {
    expect(safeJsonStringify({})).toBe("{}");
  });

  it("serializes empty array", () => {
    expect(safeJsonStringify([])).toBe("[]");
  });

  it("serializes circular reference by falling back to String(value)", () => {
    const obj = { a: 1 };
    obj.self = obj;
    const result = safeJsonStringify(obj);
    expect(typeof result).toBe("string");
  });

  it("returns string representation for Symbols", () => {
    const sym = Symbol("test");
    const result = safeJsonStringify(sym);
    expect(typeof result).toBe("string");
    expect(result).toBe("Symbol(test)");
  });

  it("handles undefined values in object", () => {
    const result = safeJsonStringify({ a: undefined, b: 1 });
    expect(result).toBe('{\n  "b": 1\n}');
  });
});
