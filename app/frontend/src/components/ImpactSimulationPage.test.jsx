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
  useMap: () => ({ setView: vi.fn(), fitBounds: vi.fn() }),
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
      expect(screen.getByLabelText(/Scenario/i)).toHaveValue("opensky-uk-closure-001");
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
});
