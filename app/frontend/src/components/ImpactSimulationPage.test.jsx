import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QUERY_RESPONSE_FIXTURE } from "../test/fixtures/queryResponse";
import { ImpactSimulationPage } from "./ImpactSimulationPage";

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
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

    await userEvent.click(screen.getByRole("button", { name: /Run impact query/i }));

    await waitFor(() => {
      expect(runImpactQuery).toHaveBeenCalledWith({
        question: expect.stringContaining("UK airspace"),
        scenarioId: "opensky-uk-closure-001",
      });
    });

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
      expect(screen.getByRole("button", { name: /Run impact query/i })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: /Run impact query/i }));

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

  it("loads map entities once for the selected scenario bbox", async () => {
    render(<ImpactSimulationPage />);

    await waitFor(() => {
      expect(listImpactScenarios).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(getImpactEntitiesGeoJson).toHaveBeenCalledWith(
        expect.objectContaining({
          bbox: "-15,35,40,62",
          limit: 1000,
        }),
      );
    });
    expect(getImpactEntitiesGeoJson).toHaveBeenCalledTimes(1);
  });

  it("defers heavy map bbox load while chat is in progress", async () => {
    const { rerender } = render(<ImpactSimulationPage chatLoading />);

    await waitFor(() => {
      expect(listImpactScenarios).toHaveBeenCalled();
    });
    expect(getImpactEntitiesGeoJson).not.toHaveBeenCalled();
    expect(
      screen.getByText(/Chat in progress — map refresh and impact query paused/i),
    ).toBeInTheDocument();

    rerender(<ImpactSimulationPage chatLoading={false} />);

    await waitFor(() => {
      expect(getImpactEntitiesGeoJson).toHaveBeenCalledWith(
        expect.objectContaining({
          bbox: "-15,35,40,62",
          limit: 1000,
        }),
      );
    });
  });

  it("surfaces backend error text when the impact query fails", async () => {
    runImpactQuery.mockRejectedValue(new Error("solver unavailable"));
    render(<ImpactSimulationPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Run impact query/i })).toBeEnabled();
    });
    await userEvent.click(screen.getByRole("button", { name: /Run impact query/i }));

    await waitFor(() => {
      expect(screen.getByText("solver unavailable")).toBeInTheDocument();
    });
  });
});
