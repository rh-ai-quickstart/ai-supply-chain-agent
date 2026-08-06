import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./services/dashboardService", () => ({
  getVectorStores: vi.fn(() => Promise.resolve({ vector_stores: [] })),
  sendChatMessageStream: vi.fn(),
}));

vi.mock("./services/newsService", () => ({
  getNews: vi.fn(() => Promise.resolve({ items: [], fetched_at: "2026-08-05T12:00:00Z" })),
}));

vi.mock("./services/generalSimulationService", () => ({
  listImpactScenarios: vi.fn(() =>
    Promise.resolve({ success: true, scenarios: ["opensky-uk-closure-001"] }),
  ),
  getImpactEntitiesGeoJson: vi.fn(() =>
    Promise.resolve({ success: true, geojson: { type: "FeatureCollection", features: [] } }),
  ),
  runImpactQuery: vi.fn(),
}));

describe("App", () => {
  beforeEach(() => {
    window.location.hash = "#/simulation";
  });

  it("renders the simulation shell by default", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /impact map/i })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /^simulation$/i })).toHaveClass(
      "dashboard-nav-btn--active",
    );
    expect(screen.queryByRole("button", { name: /^dashboard$/i })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Chat input")).toBeInTheDocument();
  });
});
