import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ImpactMapPanel } from "./ImpactMapPanel";
import { diversionKey } from "../utils/impactEntityUtils";

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  CircleMarker: ({ children, pathOptions }) => (
    <div
      data-testid="marker"
      data-color={pathOptions?.color}
      data-radius={pathOptions?.radius}
    >
      {children}
    </div>
  ),
  Popup: ({ children }) => <div data-testid="popup">{children}</div>,
  Polyline: ({ pathOptions }) => (
    <div data-testid="diversion-route" data-color={pathOptions?.color} />
  ),
  useMap: () => ({ setView: vi.fn(), fitBounds: vi.fn(), getZoom: () => 5 }),
}));

const aircraftFeature = {
  type: "Feature",
  id: "opensky-407290",
  geometry: { type: "Point", coordinates: [-0.1, 51.5] },
  properties: {
    id: "opensky-407290",
    type: "moving_entity",
    status: "airborne",
    attributes: { call_sign: "BAW123" },
  },
};

const reroute = {
  entity_id: "opensky-407290",
  target_id: "EIDW",
  target_label: "Dublin (EIDW)",
  latitude: 53.4213,
  longitude: -6.2701,
  rationale: "Divert while disruption is active.",
};

describe("ImpactMapPanel", () => {
  it("shows loading and error states", () => {
    const { rerender } = render(<ImpactMapPanel loading />);
    expect(screen.getByText("Loading entities…")).toBeInTheDocument();

    rerender(<ImpactMapPanel error="Map unavailable" />);
    expect(screen.getByText("Map unavailable")).toBeInTheDocument();
  });

  it("shows empty-state copy when there are no features", () => {
    render(<ImpactMapPanel features={[]} />);
    expect(screen.getByText(/No map entities yet/i)).toBeInTheDocument();
  });

  it("shows entity count in the header when not loading", () => {
    render(<ImpactMapPanel title="Live Flights" features={[aircraftFeature]} />);
    expect(screen.getByRole("heading", { name: "Live Flights" })).toBeInTheDocument();
    expect(screen.getAllByText(/Entities: 1/).length).toBeGreaterThanOrEqual(1);
  });

  it("shows warning text when provided", () => {
    render(<ImpactMapPanel features={[aircraftFeature]} warning="Overlay missed" />);
    expect(screen.getByRole("status")).toHaveTextContent("Overlay missed");
  });

  it("highlights aircraft when a cargo affected id remaps to it", () => {
    render(
      <ImpactMapPanel
        features={[aircraftFeature]}
        highlightedIds={["cargo-opensky-407290-1"]}
      />,
    );
    const marker = screen.getByTestId("marker");
    // Highlighted markers use the red accent color.
    expect(marker).toHaveAttribute("data-color", "#FF4757");
  });

  it("renders a diversion polyline when a reroute is selected", () => {
    const key = diversionKey(reroute);
    render(
      <ImpactMapPanel
        features={[aircraftFeature]}
        reroutes={[reroute]}
        selectedDiversionKey={key}
      />,
    );
    expect(screen.getByTestId("diversion-route")).toBeInTheDocument();
    expect(screen.getByText("Dublin (EIDW)")).toBeInTheDocument();
  });

  it("reports entity counts in the footer", () => {
    render(
      <ImpactMapPanel
        features={[aircraftFeature]}
        highlightedIds={["opensky-407290"]}
        reroutes={[reroute]}
      />,
    );
    const footer = document.querySelector(".map-counts");
    expect(footer).toHaveTextContent(/Entities: 1/);
    expect(footer).toHaveTextContent(/Highlighted: 1/);
    expect(footer).toHaveTextContent(/Diversions: 1/);
  });

  it("renders a color legend with labels for each marker state", () => {
    render(<ImpactMapPanel features={[aircraftFeature]} />);
    const legend = screen.getByRole("list", { name: /map legend/i });
    expect(legend).toBeInTheDocument();
    expect(screen.getByText(/Entity \(flight, facility, or vessel\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Affected by scenario/i)).toBeInTheDocument();
    expect(screen.getByText(/Focused entity/i)).toBeInTheDocument();
    expect(screen.getByText(/Diversion destination/i)).toBeInTheDocument();
    expect(screen.getByText(/Selected diversion \/ route/i)).toBeInTheDocument();
  });
});
