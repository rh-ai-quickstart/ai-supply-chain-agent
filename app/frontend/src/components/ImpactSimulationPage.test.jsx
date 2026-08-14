import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QUERY_RESPONSE_FIXTURE } from "../test/fixtures/queryResponse";
import { ImpactSimulationPage } from "./ImpactSimulationPage";

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  Marker: ({ children }) => <div>{children}</div>,
  CircleMarker: ({ children }) => <div>{children}</div>,
  Popup: ({ children }) => <div>{children}</div>,
  Polyline: () => <div data-testid="diversion-route" />,
  useMap: () => ({ setView: vi.fn(), fitBounds: vi.fn(), getZoom: () => 5 }),
}));

vi.mock("./ChatMarkdownBody.jsx", () => ({
  ChatMarkdownBody: ({ content }) => <div data-testid="markdown">{content}</div>,
}));

const listImpactScenarios = vi.fn();
const getImpactEntitiesGeoJson = vi.fn();
const runImpactQuery = vi.fn();

vi.mock("../services/generalSimulationService", () => ({
  listImpactScenarios: (...args) => listImpactScenarios(...args),
  getImpactEntitiesGeoJson: (...args) => getImpactEntitiesGeoJson(...args),
  runImpactQuery: (...args) => runImpactQuery(...args),
}));

async function expandResultsSection(labelPattern) {
  const trigger = screen
    .getAllByRole("button")
    .find(
      (button) =>
        button.classList.contains("collapsible-section__trigger") &&
        new RegExp(labelPattern, "i").test(button.textContent || ""),
    );
  if (!trigger) {
    throw new Error(`Collapsible section not found: ${labelPattern}`);
  }
  await userEvent.click(trigger);
}

describe("ImpactSimulationPage", () => {
  beforeEach(() => {
    listImpactScenarios.mockResolvedValue({
      success: true,
      scenarios: ["opensky-uk-closure-001"],
    });
    getImpactEntitiesGeoJson.mockResolvedValue({
      success: true,
      geojson: {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            id: "opensky-407290",
            geometry: { type: "Point", coordinates: [-0.1, 51.5] },
            properties: { id: "opensky-407290", type: "moving_entity", status: "airborne" },
          },
        ],
      },
    });
    runImpactQuery.mockResolvedValue({
      success: true,
      ...QUERY_RESPONSE_FIXTURE,
    });
  });

  it("loads scenarios and runs an impact query", async () => {
    render(<ImpactSimulationPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "UK Airspace Closure" })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    });

    await userEvent.click(screen.getByRole("button", { name: "UK Airspace Closure" }));

    await waitFor(() => {
      expect(runImpactQuery).toHaveBeenCalledWith({
        question: expect.stringContaining("UK airspace"),
        scenarioId: "opensky-uk-closure-001",
      });
    });

    await expandResultsSection("Answer");
    await waitFor(() => {
      expect(screen.getByTestId("markdown")).toHaveTextContent(
        "Three aircraft are affected by the UK airspace closure.",
      );
    });
    expect(screen.getByText("0.650")).toBeInTheDocument();
  });

  it("shows a diversion route on the map when a recommended diversion is clicked", async () => {
    render(<ImpactSimulationPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "UK Airspace Closure" })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "UK Airspace Closure" }));

    await expandResultsSection("Recommended diversions");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /opensky-407290.*Dublin/i })).toBeInTheDocument();
    });

    expect(screen.queryByTestId("diversion-route")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /opensky-407290.*Dublin/i }));

    expect(screen.getByTestId("diversion-route")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /opensky-407290.*Dublin/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("prefers initialScenarioId when present in the loaded list", async () => {
    listImpactScenarios.mockResolvedValue({
      success: true,
      scenarios: ["supply-chain-port-strike-la", "opensky-uk-closure-001"],
    });

    render(<ImpactSimulationPage initialScenarioId="opensky-uk-closure-001" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "UK Airspace Closure" })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    });
    expect(screen.getByRole("button", { name: "UK Airspace Closure" })).toHaveClass("btn--active");
  });

  it("notifies parent when the active scenario changes", async () => {
    listImpactScenarios.mockResolvedValue({
      success: true,
      scenarios: ["opensky-uk-closure-001", "supply-chain-port-strike-la"],
    });
    const onScenarioChange = vi.fn();
    render(<ImpactSimulationPage onScenarioChange={onScenarioChange} />);

    await waitFor(() => {
      expect(onScenarioChange).toHaveBeenCalledWith("opensky-uk-closure-001");
    });

    await userEvent.click(screen.getByRole("button", { name: "Port Strike LA" }));
    await waitFor(() => {
      expect(onScenarioChange).toHaveBeenCalledWith("supply-chain-port-strike-la");
    });
  });

  it("loads map entities once with the global demo bbox", async () => {
    render(<ImpactSimulationPage />);

    await waitFor(() => {
      expect(listImpactScenarios).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(getImpactEntitiesGeoJson).toHaveBeenCalledWith(
        expect.objectContaining({
          bbox: "-130,20,50,62",
          limit: 3000,
        }),
      );
    });
    expect(getImpactEntitiesGeoJson).toHaveBeenCalledTimes(1);
  });

  it("defers heavy map load while chat is in progress", async () => {
    const { rerender } = render(<ImpactSimulationPage chatLoading />);

    await waitFor(() => {
      expect(listImpactScenarios).toHaveBeenCalled();
    });
    expect(getImpactEntitiesGeoJson).not.toHaveBeenCalled();
    expect(
      screen.getByText(/Chat in progress — map refresh and Scenario paused/i),
    ).toBeInTheDocument();

    rerender(<ImpactSimulationPage chatLoading={false} />);

    await waitFor(() => {
      expect(getImpactEntitiesGeoJson).toHaveBeenCalledWith(
        expect.objectContaining({
          bbox: "-130,20,50,62",
          limit: 3000,
        }),
      );
    });
  });

  it("surfaces backend error text when the impact query fails", async () => {
    runImpactQuery.mockRejectedValue(new Error("solver unavailable"));
    render(<ImpactSimulationPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "UK Airspace Closure" })).toBeEnabled();
    });
    await userEvent.click(screen.getByRole("button", { name: "UK Airspace Closure" }));

    await waitFor(() => {
      expect(screen.getByText("solver unavailable")).toBeInTheDocument();
    });
  });

  it("runs the impact query and highlights the button when a scenario is selected", async () => {
    listImpactScenarios.mockResolvedValue({
      success: true,
      scenarios: ["opensky-uk-closure-001", "supply-chain-port-strike-la"],
    });
    render(<ImpactSimulationPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Port Strike LA" })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "Port Strike LA" }));

    await waitFor(() => {
      expect(runImpactQuery).toHaveBeenCalledWith({
        scenarioId: "supply-chain-port-strike-la",
        question: expect.stringContaining("Port of Los Angeles"),
      });
    });
    expect(screen.getByRole("button", { name: "Port Strike LA" })).toHaveClass("btn--active");
    expect(screen.getByRole("button", { name: "UK Airspace Closure" })).not.toHaveClass(
      "btn--active",
    );
  });

  it("runs the impact query from a suggested prompt chip", async () => {
    render(<ImpactSimulationPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Show affected aircraft/i }),
      ).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: /Show affected aircraft/i }));

    await waitFor(() => {
      expect(runImpactQuery).toHaveBeenCalledWith({
        scenarioId: "opensky-uk-closure-001",
        question: "Show affected aircraft and recommend diversions.",
      });
    });
  });

  it("sends a suggested prompt through the chat agent and saves it as a chat message", async () => {
    const onSendPrompt = vi.fn();
    render(<ImpactSimulationPage onSendPrompt={onSendPrompt} />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Show affected aircraft/i }),
      ).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: /Show affected aircraft/i }));

    expect(onSendPrompt).toHaveBeenCalledWith(
      "Show affected aircraft and recommend diversions.",
    );
    expect(runImpactQuery).not.toHaveBeenCalled();
  });

  it("opens create scenario from the query panel button", async () => {
    const onOpenCreateScenario = vi.fn();
    render(<ImpactSimulationPage onOpenCreateScenario={onOpenCreateScenario} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Create scenario/i })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: /Create scenario/i }));

    expect(onOpenCreateScenario).toHaveBeenCalledTimes(1);
  });
});
