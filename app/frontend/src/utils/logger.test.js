import { afterEach, describe, expect, it, vi } from "vitest";
import { getLogger } from "./logger.js";

describe("logger", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("formats messages with module name from import meta url", () => {
    const infoSpy = vi.spyOn(console, "info").mockImplementation(() => {});
    const logger = getLogger("file:///app/src/services/apiClient.js");
    logger.info("GET %s status=%d", "/api/v1/news", 200);
    expect(infoSpy).toHaveBeenCalledOnce();
    const line = infoSpy.mock.calls[0][0];
    expect(line).toContain("app-frontend:apiClient:info:");
    expect(line).toContain("GET /api/v1/news status=200");
  });

  it("routes error level to console.error", () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const logger = getLogger("file:///app/src/hooks/useChatSession.js");
    logger.error("stream failed");
    expect(errorSpy).toHaveBeenCalledOnce();
    expect(errorSpy.mock.calls[0][0]).toContain("useChatSession:error:");
    expect(errorSpy.mock.calls[0][0]).toContain("stream failed");
  });

  it("uses unknown module when url parsing fails", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const logger = getLogger("not-a-valid-url");
    logger.warn("retrying");
    expect(warnSpy.mock.calls[0][0]).toContain("unknown:warn:");
  });
});
