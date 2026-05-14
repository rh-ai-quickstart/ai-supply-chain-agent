import { beforeEach, describe, expect, it, vi } from "vitest";
import { createAssetDivIcon, PLANE_ICON_PATH } from "./mapAssetIcons";

const { divIcon } = vi.hoisted(() => {
  const fn = vi.fn((opts) => ({ ...opts, _kind: "divIcon" }));
  return { divIcon: fn };
});

vi.mock("leaflet", () => ({
  default: { divIcon },
}));

describe("createAssetDivIcon", () => {
  beforeEach(() => {
    divIcon.mockClear();
  });

  it("uses plane path for air freight", () => {
    createAssetDivIcon("airFreight", { name: "x", lat: 0, lng: 0 }, { fill: "#fff", stroke: "#000" });
    const arg = divIcon.mock.calls[0][0];
    expect(arg.html).toContain(PLANE_ICON_PATH);
    expect(arg.html).toContain("map-asset-svg");
  });

  it("uses plane icon for live assets on non-air map", () => {
    createAssetDivIcon("global", { is_live: true, lat: 0, lng: 0 }, { fill: "#fff", stroke: "#000" });
    expect(divIcon.mock.calls[0][0].html).toContain(PLANE_ICON_PATH);
  });

  it("uses truck markup for regional non-live assets", () => {
    createAssetDivIcon("regional", { name: "truck", lat: 1, lng: 2, is_live: false }, {
      fill: "#abc",
      stroke: "#111",
    });
    const html = divIcon.mock.calls[0][0].html;
    expect(html).toContain("map-truck-icon");
    expect(html).toContain("rotate(0deg)");
  });

  it("passes rotation from asset.track", () => {
    createAssetDivIcon("global", { lat: 0, lng: 0, track: 45 }, { fill: "#fff", stroke: "#000" });
    expect(divIcon.mock.calls[0][0].html).toContain("rotate(45deg)");
  });
});
