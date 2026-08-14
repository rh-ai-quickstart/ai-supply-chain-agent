import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { sendChatMessageStream } from "./services/chatService";

vi.mock("./services/chatService", () => ({
  getVectorStores: vi.fn(() =>
    Promise.resolve({
      vector_stores: [
        { id: "vs-air", name: "air_risk_uk_nats_gps_closure-abc12345" },
        { id: "vs-port", name: "land_risk_port_strike_la-def67890" },
        { id: "vs-suez", name: "suez_blockage_analysis-ghi11223" },
      ],
    }),
  ),
  sendChatMessageStream: vi.fn(),
}));

vi.mock("./services/newsService", () => ({
  getNews: vi.fn(() =>
    Promise.resolve({
      items: [
        {
          title: "Port strike disrupts shipping",
          link: "https://example.com/1",
          source: "BBC",
        },
      ],
      fetched_at: "2026-08-05T12:00:00Z",
    }),
  ),
}));

vi.mock("./services/generalSimulationService", () => ({
  listImpactScenarios: vi.fn(() =>
    Promise.resolve({
      success: true,
      scenarios: [
        "opensky-uk-closure-001",
        "supply-chain-port-strike-la",
        "supply-chain-suez-blockage",
      ],
    }),
  ),
  getImpactEntitiesGeoJson: vi.fn(() =>
    Promise.resolve({ success: true, geojson: { type: "FeatureCollection", features: [] } }),
  ),
  runImpactQuery: vi.fn(),
}));

describe("App chat", () => {
  beforeEach(() => {
    window.location.hash = "#/simulation";
    vi.mocked(sendChatMessageStream).mockReset();
  });

  it("shows the assistant reply in the chat modal after POST /api/v1/chat succeeds", async () => {
    vi.mocked(sendChatMessageStream).mockImplementation(async (_input, _history, _vs, _vllm, onEvent) => {
      onEvent({ type: "delta", content: "Fuel prices vary by region." });
      onEvent({
        type: "done",
        answer: "Fuel prices vary by region.",
        completion: { model: "meta-llama/Llama-3.2-3B-Instruct", usage: { total_tokens: 10 } },
      });
    });

    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByLabelText("Chat input")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(
        "Knowledge base: air_risk_uk_nats_gps_closure-abc12345",
      );
    });

    const input = screen.getByLabelText("Chat input");
    await user.type(input, "What are fuel prices?");
    await user.click(screen.getByRole("button", { name: "Send chat message" }));

    await waitFor(() => {
      expect(screen.getByText(/Fuel prices vary by region/)).toBeInTheDocument();
    });
    expect(sendChatMessageStream).toHaveBeenCalledWith(
      "What are fuel prices?",
      expect.any(Array),
      "vs-air",
      true,
      expect.any(Function),
      expect.objectContaining({
        signal: expect.any(AbortSignal),
        scenarioId: expect.any(String),
      }),
    );
  });

  it("keeps separate chats per scenario and selects matching vector stores", async () => {
    vi.mocked(sendChatMessageStream).mockImplementation(async (input, _history, _vs, _vllm, onEvent) => {
      onEvent({ type: "delta", content: `Reply to ${input}` });
      onEvent({
        type: "done",
        answer: `Reply to ${input}`,
        completion: { model: "test", usage: { total_tokens: 1 } },
      });
    });

    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Port Strike LA" })).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Chat input"), "UK question");
    await user.click(screen.getByRole("button", { name: "Send chat message" }));

    await waitFor(() => {
      expect(screen.getByText(/Reply to UK question/)).toBeInTheDocument();
    });
    expect(sendChatMessageStream).toHaveBeenLastCalledWith(
      "UK question",
      expect.any(Array),
      "vs-air",
      true,
      expect.any(Function),
      expect.objectContaining({
        signal: expect.any(AbortSignal),
        scenarioId: expect.any(String),
      }),
    );

    await user.click(screen.getByRole("button", { name: "Port Strike LA" }));
    await waitFor(() => {
      expect(screen.queryByText(/Reply to UK question/)).not.toBeInTheDocument();
    });
    const chatBar = screen.getByLabelText("Chat input").closest(".chat-bar-container");
    await waitFor(() => {
      expect(within(chatBar).getByLabelText("Knowledge base status")).toHaveTextContent(
        "Knowledge base: land_risk_port_strike_la-def67890",
      );
    });

    await user.type(screen.getByLabelText("Chat input"), "Port question");
    await user.click(screen.getByRole("button", { name: "Send chat message" }));

    await waitFor(() => {
      expect(screen.getByText(/Reply to Port question/)).toBeInTheDocument();
    });
    expect(sendChatMessageStream).toHaveBeenLastCalledWith(
      "Port question",
      expect.any(Array),
      "vs-port",
      true,
      expect.any(Function),
      expect.objectContaining({
        signal: expect.any(AbortSignal),
        scenarioId: expect.any(String),
      }),
    );

    await user.click(screen.getByRole("button", { name: "UK Airspace Closure" }));
    await waitFor(() => {
      expect(screen.getByText(/Reply to UK question/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Reply to Port question/)).not.toBeInTheDocument();
  });
});
