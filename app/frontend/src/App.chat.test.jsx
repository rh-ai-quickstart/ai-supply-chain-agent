import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { sendChatMessage } from "./services/dashboardService";

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
      charts: {
        demand: { labels: [], actual: [], forecast: [] },
        revenue: { revenueData: [], colors: [] },
      },
    }),
  ),
  getVectorStores: vi.fn(() => Promise.resolve({ vector_stores: [] })),
  triggerWorldEvent: vi.fn(() => Promise.resolve({})),
  runSimulation: vi.fn(() => Promise.resolve({})),
  sendChatMessage: vi.fn(),
}));

describe("App chat", () => {
  beforeEach(() => {
    window.location.hash = "#/";
    vi.mocked(sendChatMessage).mockReset();
  });

  it("shows the assistant reply in the chat modal after POST /api/v1/chat succeeds", async () => {
    vi.mocked(sendChatMessage).mockResolvedValue({
      answer: "Fuel prices vary by region.",
      completion: { model: "meta-llama/Llama-3.2-1B-Instruct", usage: { total_tokens: 10 } },
    });

    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /live logistics map/i })).toBeInTheDocument();
    });

    const input = screen.getByLabelText("Chat input");
    await user.type(input, "What are fuel prices?");
    await user.click(screen.getByRole("button", { name: "➤" }));

    await waitFor(() => {
      expect(screen.getByText(/Fuel prices vary by region/)).toBeInTheDocument();
    });
  });
});
