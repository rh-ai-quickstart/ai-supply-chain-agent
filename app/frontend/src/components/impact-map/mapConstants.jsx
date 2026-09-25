import L from "leaflet";
import { renderToStaticMarkup } from "react-dom/server";
import { Building2, PlaneTakeoff, Anchor } from "lucide-react";

export const DEFAULT_CENTER = [51.5, -0.5];
export const DEFAULT_ZOOM = 5;

/** Marker / route colors shared by the map and legend. */
export const MAP_COLORS = {
  flight: "#111111",
  facility: "#2ECC71",
  affected: "#FF4757",
  focused: "#FFC312",
  diversion: "#2ECC71",
  diversionSelected: "#F1C40F",
};

/** Default marker color per entity kind. */
export const KIND_COLORS = {
  flight: MAP_COLORS.flight,
  facility: MAP_COLORS.facility,
  vessel: MAP_COLORS.flight,
};

export const DIVERSION_COLOR = MAP_COLORS.diversion;
export const DIVERSION_SELECTED_COLOR = MAP_COLORS.diversionSelected;

const ENTITY_ICONS = {
  flight: PlaneTakeoff,
  facility: Building2,
  vessel: Anchor,
};

const KIND_BY_TYPE = {
  moving_entity: "flight",
  facility: "facility",
  vessel: "vessel",
};

/** Map a GeoJSON feature to a display kind derived from its ``type`` property. */
export function kindForType(type) {
  const kind = KIND_BY_TYPE[String(type || "")];
  return kind || "facility";
}

/** Render a lucide icon to an inline SVG string for use in a Leaflet divIcon. */
export function entityIconHtml(kind, color, size, strokeWidth) {
  const Icon = ENTITY_ICONS[kind] || ENTITY_ICONS.facility;
  return renderToStaticMarkup(
    <span className="impact-entity-glyph" style={{ color }}>
      <Icon size={size} strokeWidth={strokeWidth} aria-hidden="true" />
    </span>,
  );
}

/** ``L.divIcon`` for an entity kind, tinted by the current marker state color. */
export function entityIcon(kind, color, isEmphasized) {
  const size = isEmphasized ? 34 : 26;
  const strokeWidth = isEmphasized ? 2 : 1.75;
  return L.divIcon({
    className: "impact-entity-icon",
    html: entityIconHtml(kind, color, size, strokeWidth),
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

export const MAP_LEGEND_ITEMS = [
  { kind: "flight", label: "Flight (moving entity)" },
  { kind: "facility", label: "Facility (port, warehouse, airport)" },
  { color: MAP_COLORS.affected, label: "Affected by scenario" },
  { color: MAP_COLORS.focused, label: "Focused entity" },
  { color: MAP_COLORS.diversion, label: "Diversion destination" },
  { color: MAP_COLORS.diversionSelected, label: "Selected diversion / route" },
];

/** Parse ``minLon,minLat,maxLon,maxLat`` into Leaflet ``[[lat,lon],[lat,lon]]`` corners. */
export function parseFocusBbox(bbox) {
  if (!bbox || typeof bbox !== "string") return null;
  const parts = bbox.split(",").map((part) => Number(String(part).trim()));
  if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n))) return null;
  const [minLon, minLat, maxLon, maxLat] = parts;
  return [
    [minLat, minLon],
    [maxLat, maxLon],
  ];
}
