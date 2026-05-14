import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }) => <div data-testid="mock-map">{children}</div>,
  TileLayer: () => null,
  CircleMarker: ({ children }) => <div>{children}</div>,
  Popup: ({ children }) => <div>{children}</div>,
  Marker: ({ children }) => <div>{children}</div>,
}));

vi.mock("react-chartjs-2", () => ({
  Line: () => <div data-testid="mock-line-chart" />,
  Bar: () => <div data-testid="mock-bar-chart" />,
}));
