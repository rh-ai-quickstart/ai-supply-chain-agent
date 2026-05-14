import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./services/dashboardService", () => ({
  getDashboardState: vi.fn(() =>
    Promise.resolve({
      kpis: {},
      alerts: { global: [], regional: [], airFreight: [] },
      mapData: {
        airFreight: { assets: [], ports: [] },
        global: { assets: [], ports: [] },
        regional: { assets: [], ports: [] },
      },
      charts: { demand: { labels: [], actual: [], forecast: [] }, revenue: { revenueData: [], colors: [] } },
    })
  ),
  getVectorStores: vi.fn(() => Promise.resolve({ vector_stores: [] })),
  triggerWorldEvent: vi.fn(() => Promise.resolve({})),
  runSimulation: vi.fn(() => Promise.resolve({})),
  sendChatMessage: vi.fn(() => Promise.resolve({ answer: "ok" })),
}));

describe("App", () => {
  beforeEach(() => {
    window.location.hash = "#/";
  });

  it("renders the dashboard shell after state loads", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /live logistics map/i })).toBeInTheDocument();
    });
  });
});
