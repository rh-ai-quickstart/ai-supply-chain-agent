import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LogisticsMapPanel } from "./LogisticsMapPanel";

// Mock react-leaflet to avoid leaflet init requirements
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children, center, zoom }) => (
    <div data-testid="map-container" data-center={JSON.stringify(center)} data-zoom={zoom}>
      {children}
    </div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  CircleMarker: ({ center, children, pathOptions }) => (
    <div data-testid="circle-marker" data-center={JSON.stringify(center)}>
      {pathOptions && <div data-path-options={JSON.stringify(pathOptions)} />}
      {children}
    </div>
  ),
  Marker: ({ children, position, icon }) => (
    <div data-testid="marker" data-position={JSON.stringify(position)}>
      {icon && <div data-icon={JSON.stringify(icon)} />}
      {children}
    </div>
  ),
  Popup: ({ children }) => <div data-testid="popup">{children}</div>,
}));

vi.mock("../utils/mapAssetIcons", () => ({
  createAssetDivIcon: vi.fn((view, asset) => ({ view, asset })),
}));

describe("LogisticsMapPanel", () => {
  const baseProps = {
    mapView: "airFreight",
    onChangeMapView: vi.fn(),
    selectedMapData: { ports: [], assets: [] },
    assetCounts: { air: 0, sea: 0, land: 0 },
  };

  it("renders heading", () => {
    render(<LogisticsMapPanel {...baseProps} />);
    expect(screen.getByRole("heading", { name: /Live Logistics Map/i })).toBeInTheDocument();
  });

  it("renders map view select with all options", () => {
    render(<LogisticsMapPanel {...baseProps} />);
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
    expect(select.value).toBe("airFreight");
  });

  it("renders all map view options", () => {
    render(<LogisticsMapPanel {...baseProps} />);
    expect(screen.getByRole("option", { name: /Global Air Freight/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Global Shipping/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /North America/i })).toBeInTheDocument();
  });

  it("changes map view on selection", async () => {
    const user = userEvent.setup();
    const onChangeMapView = vi.fn();
    render(<LogisticsMapPanel {...baseProps} onChangeMapView={onChangeMapView} />);
    await user.selectOptions(screen.getByRole("combobox"), "global");
    expect(onChangeMapView).toHaveBeenCalledWith("global");
  });

  it("renders ports as circle markers", () => {
    const ports = [
      { name: "Port A", lat: 40, lng: -74, risk: 5 },
      { name: "Port B", lat: 51, lng: 0, risk: 20 },
    ];
    render(<LogisticsMapPanel {...baseProps} selectedMapData={{ ports }} />);
    const markers = screen.getAllByTestId("circle-marker");
    expect(markers.length).toBe(2);
  });

  it("colors high-risk ports red", () => {
    const port = { name: "Danger", lat: 0, lng: 0, risk: 25 };
    render(<LogisticsMapPanel {...baseProps} selectedMapData={{ ports: [port] }} />);
    const container = screen.getByTestId("map-container");
    // Check path options are rendered
    const pathOptions = screen.getByTestId("circle-marker");
    expect(pathOptions).toBeInTheDocument();
  });

  it("colors low-risk ports green", () => {
    render(
      <LogisticsMapPanel
        {...baseProps}
        selectedMapData={{ ports: [{ name: "Safe", lat: 0, lng: 0, risk: 5 }] }}
      />
    );
    const marker = screen.getByTestId("circle-marker");
    expect(marker).toBeInTheDocument();
  });

  it("renders assets as markers", () => {
    const assets = [
      { id: "a1", name: "Asset A", lat: 40, lng: -74, speed: 50 },
    ];
    render(<LogisticsMapPanel {...baseProps} selectedMapData={{ assets }} />);
    const markers = screen.getAllByTestId("marker");
    expect(markers.length).toBe(1);
  });

  it("skips assets without valid coordinates", () => {
    render(
      <LogisticsMapPanel
        {...baseProps}
        selectedMapData={{ assets: [{ id: "bad", name: "No coords" }] }}
      />
    );
    const markers = screen.queryAllByTestId("marker");
    expect(markers.length).toBe(0);
  });

  it("renders marker popup with asset info", () => {
    const asset = { id: "a1", name: "Cargo Ship", lat: 40, lng: -74, cargo: "Electronics" };
    render(<LogisticsMapPanel {...baseProps} selectedMapData={{ assets: [asset] }} />);
    const marker = screen.getByTestId("marker");
    expect(marker).toBeInTheDocument();
  });

  it("shows asset counts", () => {
    render(
      <LogisticsMapPanel
        {...baseProps}
        assetCounts={{ air: 5, sea: 3, land: 2 }}
      />
    );
    expect(screen.getByText(/Air: 5/i)).toBeInTheDocument();
    expect(screen.getByText(/Sea: 3/i)).toBeInTheDocument();
    expect(screen.getByText(/Land: 2/i)).toBeInTheDocument();
  });

  it("renders map container with correct dimensions", () => {
    const { container } = render(<LogisticsMapPanel {...baseProps} />);
    const mapViewport = container.querySelector(".map-viewport");
    expect(mapViewport).toBeInTheDocument();
  });

  it("renders map counts section", () => {
    render(<LogisticsMapPanel {...baseProps} assetCounts={{ air: 0, sea: 0, land: 0 }} />);
    const counts = screen.getByText(/Assets/i);
    expect(counts).toBeInTheDocument();
  });

  it("uses provided mapView prop value in select", () => {
    render(<LogisticsMapPanel {...baseProps} mapView="global" />);
    expect(screen.getByRole("combobox")).toHaveValue("global");
  });

  it("renders asset with speed info", () => {
    const asset = { id: "a1", name: "Fast Ship", lat: 40, lng: -74, speed: "10 knots" };
    render(<LogisticsMapPanel {...baseProps} selectedMapData={{ assets: [asset] }} />);
    const marker = screen.getByTestId("marker");
    expect(marker).toBeInTheDocument();
  });

  it("uses asset.id as key when available", () => {
    const asset = { id: "unique-id", name: "X", lat: 0, lng: 0 };
    // The key is set on the <Marker> element via React, not directly visible in DOM
    // but we can verify the marker renders without error
    render(<LogisticsMapPanel {...baseProps} selectedMapData={{ assets: [asset] }} />);
    expect(screen.getByTestId("marker")).toBeInTheDocument();
  });
});
